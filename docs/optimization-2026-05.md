# NexTags 效能 / 架構優化調查報告（2026-05）

## 背景與範圍

NexTags 在 2026-05 進行一次完整的效能與架構稽核。起點是一批未 commit 的進行中變更（約 +930 行，導入 Redis audio catalog、Navidrome hook、port 收斂等），目的是先確認該批變更是否安全可上線，再就整個 codebase 提出與處理進一步的優化項目。

調查覆蓋：FastAPI 後端（router/services/dependencies）、React/Vite 前端、Docker 部署設定、共用元件（task_manager、Redis 快取、SQLite）。本報告是該次優化的完整紀錄。

---

## 調查發現分類

### A 區：未 commit 變更的風險（上線阻擋項）

| # | 風險 | 嚴重度 |
|---|---|---|
| A1 | `upsert_audio_record` 改成重操作（讀標籤 + 多次 `os.stat` 遠端）卻在 async handler 內同步呼叫 → 阻塞 event loop | 高（必修） |
| A2 | 需確認 startup 真的有 `task_manager.start_worker()`，否則 `/cache/rebuild` 永遠 pending | 高（必驗） |
| A3 | `seed_catalog_from_tag_cache` 未傳入 `folder_paths`，main_folder/relative_path 可能錯 | 中 |
| A4 | read-then-pipeline 非原子，批次 replaygain 並發有 lost-update | 中 |
| A5 | 未追蹤備份檔 `backups-compose-before-localhost-*.yml` 不應 commit；Navidrome hook 須有對應 watcher | 低 |

### B 區：稽核產出的優化項目（依優先序）

- **B1** 同步阻塞卡死 event loop（`playlists.py` / `music_import.py` / `audio.py` 多個 `async` 端點直接跑 `os.walk` / mutagen / `subprocess.run(ffmpeg)`，ReplayGain 最長 120s、轉檔無 timeout）
- **B2** `get_config` 每次開新 SQLite 連線、無連線池，在每檔熱路徑被呼叫上千次
- **B3** `replaygain.py:118` 呼叫不存在的 `redis_cache.invalidate_cache()`（應為 `remove_tags`），被 except 吞掉 → ReplayGain 後快取從未失效
- **B4** 列表 API 無真分頁：每翻頁都全量載入 catalog、轉換、排序，最後才切 100 筆
- **B5** task_manager 與全域狀態設計缺陷：`tasks.json` 無鎖全檔讀寫、`import_sessions` / batch 狀態為模組全域 dict（重啟即失、不共享、永不清理）
- **B6** 前端：搜尋輸入觸發 100 列重繪、`key={index}`、掛載時雙重 fetchSongs、`useGenerateAllM3U` 輪詢無 cleanup、每次 GET console.log
- **零散** CORS `allow_origins=["*"]` + `allow_credentials=True` 規範互斥；上傳一次性讀整檔入記憶體；多個 handler 缺 `except HTTPException: raise` 導致 4xx 被吞成 500

---

## 已完成的修正（9 個 commit，全部各自於容器內驗證）

| Commit | 對應 | 內容 |
|---|---|---|
| `0ef228a` | A 區 | Redis catalog 優化 + A1 阻塞 I/O 移出 event loop（`update_audio_tags` / `generate_audio_replaygain` / `confirm_file_move`）；確認 worker 啟動 |
| `107669c` | B3 | `replaygain.py` `invalidate_cache` → `remove_tags`，並移除呼叫端重複 log |
| `345a21f` | B2 | `get_config` 加進程內快取（執行緒安全、30s TTL 多 worker 安全網、寫入失效），消除熱路徑每檔上千次 SQLite 連線 |
| `cca7e0c` | B1 | 8 個 async handler 抽出同步 `_impl` + `run_in_executor`（playlists 3 個、music_import 5 個） |
| `38b6305` | B6 | `SongRow` `React.memo` 化、`key={song.FilePath}`、移除重複 fetch、`useGenerateAllM3U` unmount 清理、移除 `api.ts` GET console.log |
| `29f796d` | B4 | 列表 server-side 分頁：新增 `audio_catalog:by_mtime` ZSET（同步 upsert/remove/seed/rebuild/clear）、`get_audio_records_page` 用 `ZREVRANGE`+`MGET`、有 filter 仍走全量、缺索引 lazy backfill 無損回填 |
| `697a720` | B5 | task_manager → Redis：per-task key + index ZSET、原子單筆寫入、`get_all_tasks` O(limit)、啟動標記中斷、Redis 不可用退回記憶體；既有 `tasks.json` 一次性無損遷移（實測 42 筆） |
| `139746a` | B5 | `RedisDoc` 共用元件；batch replaygain / batch m3u 狀態 → Redis（跨重啟/多 worker 共享、崩潰後不卡 running）；`import_sessions` 修記憶體洩漏（終態 + TTL 6h 清理 + 上限 1000） |
| `df1287d` | 零散 | CORS 改 `CORS_ALLOW_ORIGINS` env 驅動且正確處理 `*` 與 credentials 互斥；上傳 1MB 分塊串流；music_import 11 個 handler 補 `except HTTPException: raise` |

### 行為與合約變更

- **API 合約**：所有列表/狀態端點回傳格式不變，前端免改。
- **排序平手**：B4 之後相同 mtime 的次序由 `ZREVRANGE` 的 member 字典序決定（原本是 `sorted(paths)` 再穩定排序），可接受的細微差異。
- **錯誤碼**：B5 / 零散修正之後，原本應該回 400/404 但被吞成 500 的錯誤路徑會正確回 4xx；正常路徑不變。
- **環境變數**：新增 `CORS_ALLOW_ORIGINS`（可選，未設為 `*`）。

### 驗證方式

- 每個 Python 變更：`py_compile` + 後端 image build + 容器內 `uv run python -c` 實際 import / 呼叫關鍵方法。
- 前端變更：`docker compose build frontend`（= `tsc && vite build`）通過。
- B5 跨行程持久化：兩個獨立 `docker compose run` 容器，行程 A 寫入、行程 B 讀回相同值，證明跨重啟 / 多 worker 共享。
- B4 ZSET 一致性：核對所有 `CATALOG_PATHS_KEY` mutation 點都有配對的 `CATALOG_MTIME_ZSET` mutation。

---

## 刻意保留的後續項

### import_sessions 完整 Redis 化

**為何不做**：`import_sessions` 存 `datetime`、`ImportStatus` enum 與 `errors` list（非 JSON 原生），且 55 處呼叫多半是「取出 session 後就地 mutate 不寫回」。完整 Redis 化要 (1) 改寫整個匯入精靈狀態模型（serialize/deserialize 跨型別會影響跨 55 處比較/格式化）、(2) 每個就地 mutate 點顯式寫回。此環境無法跑多步上傳 API 端到端驗證，硬塞進驗不了的大 commit 會危及核心匯入功能。

**已做的折衷**：先修最具體的危害——記憶體洩漏（終態 + TTL 6h 清理 + 上限 1000），不改型別/行為、不誤刪進行中 session。

**建議何時做**：配合實際匯入流程的端到端測試（手動或腳本）一起進行，可作為獨立 PR。

### 其他較小遺留

- `database.py` SQLite 連線池：B2 的 `get_config` 快取已大幅消除熱路徑壓力，剩餘呼叫量低，必要時再做。
- 前端 code-splitting（`React.lazy` 路由級拆分）：vite build 仍有 chunk 警告，bundle 偏大但可接受；要做時改 `router.tsx` 即可。
- task_manager 統一其他長任務類型（batch_replaygain / batch_m3u 改為 task_manager 任務）：行為合約變更面大、需配合前端輪詢端點變動，本次刻意只做持久化、不動機制。

---

## 部署提醒

1. **前端**：在容器內 `npm run build`（已驗證可建置）；本機開發無 `node_modules` 時無法跑 tsc。
2. **後端首次列表請求**：log 會出現「已由現有 catalog 回填 by_mtime 索引，共 N 筆」（B4 lazy backfill，一次性 O(N)，之後每頁 O(頁)）。若未出現且列表正常 → 走 fallback 全量路徑（正確、僅較慢），下次 rebuild 後即建立索引。
3. **task_manager 首次啟動**：log 會出現「已將 N 筆既有任務從 tasks.json 遷移到 Redis（原檔保留）」；後續啟動只在 flag 不存在時遷移，idempotent。
4. **可選環境變數**：`CORS_ALLOW_ORIGINS=https://your.domain,https://other.domain` 收斂跨域來源（credentials 自動啟用）；未設則保留 `*` + credentials=False（spec 正確）。
5. **Redis 故障時**：task_manager 與 RedisDoc 自動退回行程內記憶體（不持久化但服務不中斷）；catalog 路徑自動 fallback 至檔案系統掃描（較慢但正確）。

---

## 附錄：典型路徑前後對照

### 列表 API（無 filter、預設 Home）

| 項 | Before | After |
|---|---|---|
| Redis 操作 | `SMEMBERS paths`（全部）+ 全量 `MGET` | `ZCARD` + `ZREVRANGE start end` + 該頁 `MGET` |
| 轉換工作 | 全部 records 都呼叫 `_catalog_record_to_audio_details` | 只該頁 100 筆 |
| 排序 | Python 端 `.sort()` O(N log N) | Redis 端 score 排序，零 Python 排序 |
| 阻塞 event loop | 是（async handler 內全程同步） | 否（catalog 路徑無重 I/O；fallback 路徑仍同步但較少觸發） |

### 標籤更新 / ReplayGain 端點

| 項 | Before | After |
|---|---|---|
| event loop | 直接執行 mutagen 寫 + remote stat + ffmpeg 子程序（最長 120s）→ 卡死 | 全部丟 `run_in_executor` 執行緒池 |
| ReplayGain 後快取 | `invalidate_cache` 不存在 → except 吞掉 → 列表讀舊標籤 | `remove_tags` 正確失效，呼叫端 upsert 立即刷新 |

### task_manager / 任務狀態

| 項 | Before | After |
|---|---|---|
| 儲存 | `tasks.json` 全檔讀寫、無鎖、高頻 rewrite | per-task Redis key、單筆原子 SET |
| `get_all_tasks(limit)` | O(全部) load + sort | O(limit) `ZREVRANGE` + `MGET` |
| 跨重啟 / 多 worker | tasks.json 寫競態損毀；batch 狀態全失 | 全部 Redis 共享，崩潰後 `is_running` 不卡 |
| import_sessions | 永不清理，長期記憶體洩漏 | 終態 + TTL 6h 清除、上限 1000 |

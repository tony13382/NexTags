# 播放清單配置匯入匯出功能

## 功能概述

此功能允許您將所有播放清單的配置匯出為 JSON 檔案下載到本地，並可以從本地 JSON 檔案匯入配置。這對於備份、遷移或批量管理播放清單非常有用。

## 前端使用方式

### 1. 匯出播放清單配置

**位置：** 播放清單管理頁面 → 匯出配置按鈕

**功能：**
- 點擊「匯出配置」按鈕
- 自動下載包含所有播放清單配置的 JSON 檔案
- 檔案名稱格式：`playlist_config_YYYYMMDD_HHMMSS.json`
- 同時會在伺服器上保存一份 `/app/data/playlist_config.json`（供直接匯入使用）

### 2. 匯入播放清單配置

**位置：** 播放清單管理頁面 → 匯入配置按鈕

**步驟：**
1. 點擊「匯入配置」按鈕
2. 選擇要匯入的 JSON 檔案
3. 在確認對話框中：
   - 查看檔案名稱
   - 選擇匯入模式：
     - ☐ **新增模式**（預設）：只新增不存在的播放清單
     - ☑ **替換模式**：刪除所有現有播放清單後再匯入
4. 點擊「確認匯入」

**注意：**
- 替換模式會刪除所有現有播放清單，請謹慎使用
- 新增模式會跳過已存在的播放清單（根據名稱判斷）

## API 端點

### 1. 匯出播放清單配置

**端點：** `GET /api/playlists/export-config`

**說明：** 將所有播放清單的配置匯出為 JSON 檔案並下載。同時會在伺服器保存一份到 `/app/data/playlist_config.json`。

**回應：** 直接下載 JSON 檔案

**使用範例：**
```bash
# 使用瀏覽器直接訪問即可下載
http://localhost:4000/api/playlists/export-config

# 或使用 curl 下載
curl -O http://localhost:4000/api/playlists/export-config
```

### 2. 上傳播放清單配置

**端點：** `POST /api/playlists/upload-config`

**說明：** 上傳 JSON 配置檔案到伺服器（儲存為 `/app/data/playlist_config.json`）。

**請求：** multipart/form-data，包含檔案欄位

**回應範例：**
```json
{
  "success": true,
  "message": "成功上傳配置檔案，包含 2 個播放清單",
  "file_path": "/app/data/playlist_config.json",
  "total_playlists": 2
}
```

### 2. 匯入播放清單配置

**端點：** `POST /api/playlists/import-config`

**說明：** 從 `/app/data/playlist_config.json` 檔案匯入播放清單配置。

**查詢參數：**
- `replace_existing` (boolean, 預設: false)
  - `true`: 清空現有所有播放清單，然後匯入配置檔中的所有播放清單
  - `false`: 只新增配置檔中不存在的播放清單，已存在的會被跳過

**回應範例：**
```json
{
  "success": true,
  "message": "匯入完成：新增 2 個，更新 0 個，跳過 0 個",
  "imported_count": 2,
  "updated_count": 0,
  "skipped_count": 0,
  "total_in_file": 2
}
```

**使用範例：**
```bash
# 只新增不存在的播放清單
curl -X POST "http://localhost:4000/api/playlists/import-config?replace_existing=false"

# 替換所有現有播放清單
curl -X POST "http://localhost:4000/api/playlists/import-config?replace_existing=true"
```

## 配置檔案格式

`playlist_config.json` 檔案格式如下：

```json
{
  "version": "1.0",
  "exported_at": "2025-12-27T06:46:01.172499",
  "playlists": [
    {
      "name": "A01・所有純音樂 by Title",
      "base_folder": "A 純音樂",
      "filter_language": null,
      "filter_tags": [],
      "exclude_tags": [],
      "sort_by": "title",
      "is_system_level": false
    },
    {
      "name": "A01・所有人聲 by Title",
      "base_folder": "B 人聲",
      "filter_language": null,
      "filter_tags": [],
      "exclude_tags": [],
      "sort_by": "title",
      "is_system_level": false
    }
  ]
}
```

### 欄位說明

- `version`: 配置檔案版本
- `exported_at`: 匯出時間戳記
- `playlists`: 播放清單陣列
  - `name`: 播放清單名稱（必填）
  - `base_folder`: 基礎資料夾
  - `filter_language`: 語言篩選（可為 null）
  - `filter_tags`: 標籤篩選陣列
  - `exclude_tags`: 排除標籤陣列
  - `sort_by`: 排序方式（如：title, file_creation_time）
  - `is_system_level`: 是否為系統級播放清單

## 使用場景

### 1. 備份播放清單配置

定期匯出配置以備份：
```bash
curl http://localhost:4000/api/playlists/export-config
# 然後備份 /app/data/playlist_config.json 檔案
```

### 2. 遷移到新環境

1. 在舊環境匯出配置
2. 將 `playlist_config.json` 複製到新環境的 `/app/data/` 目錄
3. 在新環境執行匯入

```bash
# 在新環境中
curl -X POST "http://localhost:4000/api/playlists/import-config?replace_existing=true"
```

### 3. 批量修改播放清單

1. 匯出配置
2. 編輯 `playlist_config.json` 檔案
3. 匯入配置（使用 replace_existing=true）

### 4. 重置播放清單

如果需要重置到預設的播放清單配置：
1. 準備好標準的 `playlist_config.json`
2. 執行匯入（使用 replace_existing=true）

## 檔案位置

在 Docker 容器內：`/app/data/playlist_config.json`

在宿主機（透過 volume 掛載）：檢查 docker-compose.yml 中的 volume 設定

## 注意事項

1. **匯出會覆蓋現有檔案**：每次匯出都會覆蓋 `playlist_config.json`，請在匯出前備份重要的配置檔案
2. **匯入前先備份**：建議在匯入前先匯出現有配置作為備份
3. **replace_existing 要謹慎使用**：設為 true 會刪除所有現有播放清單
4. **名稱唯一性**：播放清單名稱用於判斷是否已存在，確保名稱唯一
5. **權限問題**：確保容器有權限讀寫 `/app/data/` 目錄

## 錯誤處理

- 404: 匯入時找不到配置檔案
- 400: 配置檔案格式錯誤
- 500: 資料庫錯誤或其他伺服器錯誤

## 版本歷史

- v1.0 (2025-12-27): 初始版本，支援基本的匯出和匯入功能

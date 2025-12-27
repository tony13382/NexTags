# 開發環境設定指南

此專案提供了生產環境和開發環境兩套 Docker Compose 設定檔。

## 開發環境 vs 生產環境

### 生產環境 (`docker-compose.yml`)
- 前端：使用 Nginx 提供靜態檔案服務
- 後端：使用生產模式啟動（無熱重載）
- 適合部署到伺服器

### 開發環境 (`docker-compose.dev.yml`)
- 前端：使用 Vite 開發伺服器，支援 HMR（熱模組替換）
- 後端：使用 `--reload` 模式，程式碼變更自動重啟
- 源代碼掛載到容器，修改立即生效
- 啟用詳細的除錯日誌

## 使用開發環境

### 1. 啟動開發環境

```bash
# 停止生產環境（如果正在運行）
docker-compose down

# 啟動開發環境
docker-compose -f docker-compose.dev.yml up --build
```

### 2. 訪問服務

- **前端**：http://localhost:4000
- **後端 API**：http://localhost:6000

### 3. 開發流程

#### 前端開發
1. 編輯 `frontend/src/` 下的檔案
2. Vite 開發伺服器會自動偵測變更並熱重載
3. 瀏覽器自動刷新顯示最新變更

#### 後端開發
1. 編輯 `backend/app/` 下的 Python 檔案
2. Uvicorn 會自動偵測變更並重啟服務
3. API 變更立即生效

### 4. 查看日誌

```bash
# 查看所有服務日誌
docker-compose -f docker-compose.dev.yml logs -f

# 查看特定服務日誌
docker-compose -f docker-compose.dev.yml logs -f backend
docker-compose -f docker-compose.dev.yml logs -f frontend
```

### 5. 停止開發環境

```bash
# 停止服務但保留資料
docker-compose -f docker-compose.dev.yml down

# 停止服務並清除所有資料（包括資料庫）
docker-compose -f docker-compose.dev.yml down -v
```

## 切換環境

### 從生產環境切換到開發環境

```bash
docker-compose down
docker-compose -f docker-compose.dev.yml up --build
```

### 從開發環境切換到生產環境

```bash
docker-compose -f docker-compose.dev.yml down
docker-compose up --build
```

## 常見問題

### Q: 前端修改後沒有自動更新？
A: 檢查瀏覽器控制台是否有 HMR 連接錯誤。確保容器正在運行：
```bash
docker-compose -f docker-compose.dev.yml ps
```

### Q: 後端修改後沒有自動重啟？
A: 檢查後端日誌是否有語法錯誤：
```bash
docker-compose -f docker-compose.dev.yml logs backend
```

### Q: 想要完全重建容器？
A: 使用 `--build` 參數強制重建：
```bash
docker-compose -f docker-compose.dev.yml up --build --force-recreate
```

### Q: 資料庫資料會保留嗎？
A: 是的，除非使用 `-v` 參數刪除 volumes：
```bash
# 保留資料
docker-compose -f docker-compose.dev.yml down

# 刪除資料
docker-compose -f docker-compose.dev.yml down -v
```

## 技術細節

### 前端開發伺服器設定
- 使用 Vite 開發伺服器（參考 `vite.config.ts`）
- 端口：3000（容器內部）→ 4000（主機）
- HMR WebSocket：自動配置
- API Proxy：`/api` → `http://backend:8000`

### 後端開發模式
- Uvicorn reload mode：檔案變更自動重啟
- LOG_LEVEL：DEBUG（詳細日誌）
- 源代碼掛載：`./backend` → `/app`

### Volume 掛載
- **Backend**：`./backend:/app`（源代碼）
- **Frontend**：`./frontend:/app`（源代碼）
- **Music**：`${MUSIC_ROOT_PATH}:/Music`（音樂檔案）
- **node_modules**：使用容器內的版本（避免主機與容器環境不一致）

## 建議的開發工作流程

1. **首次設定**
   ```bash
   # 啟動開發環境
   docker-compose -f docker-compose.dev.yml up --build

   # 前往系統設定頁面設定音樂資料夾
   open http://localhost:4000/settings
   ```

2. **日常開發**
   ```bash
   # 早上啟動
   docker-compose -f docker-compose.dev.yml up

   # 開發... 修改代碼會自動生效

   # 晚上關閉（保留資料）
   docker-compose -f docker-compose.dev.yml down
   ```

3. **測試生產版本**
   ```bash
   # 切換到生產環境測試
   docker-compose -f docker-compose.dev.yml down
   docker-compose up --build

   # 測試完畢切回開發環境
   docker-compose down
   docker-compose -f docker-compose.dev.yml up
   ```

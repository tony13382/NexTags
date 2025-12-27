# 音樂管理系統 (Personal Music Manager)

一個基於 FastAPI + React 的音樂管理系統，支援音樂檔案標籤管理、播放清單管理等功能。

## 功能特色

- 🎵 音樂檔案標籤管理（支援 FLAC, MP3, WAV 等格式）
- 📁 多資料夾管理
- 🏷️ 自訂標籤和語言設定
- 💾 Redis 快取支援
- 🗄️ PostgreSQL 資料庫
- 🐳 Docker 容器化部署
- 🔥 開發環境支援熱重載 (HMR)

## 技術棧

### 後端
- **FastAPI**: Python Web 框架
- **PostgreSQL**: 關聯式資料庫
- **Redis**: 快取層
- **Mutagen**: 音樂標籤讀取

### 前端
- **React 18**: UI 框架
- **Vite**: 構建工具
- **React Router**: 路由管理
- **TailwindCSS**: 樣式框架

## 快速開始

### 環境需求

- Docker & Docker Compose
- 音樂檔案目錄

### 1. 設定環境變數

複製 `.env.example` 並修改為 `.env`：

```bash
MUSIC_ROOT_PATH=/path/to/your/music
REDIS_HOST=redis
REDIS_PORT=6379
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
POSTGRES_DB=musicmanager
POSTGRES_USER=musicuser
POSTGRES_PASSWORD=musicpass
```

### 2. 選擇運行模式

#### 開發環境（推薦用於開發）

```bash
# 使用 Makefile（推薦）
make dev

# 或使用 Docker Compose
docker-compose -f docker-compose.dev.yml up
```

**開發環境特色：**
- ✅ 前端 HMR（熱模組替換）
- ✅ 後端自動重載
- ✅ 源代碼掛載
- ✅ 詳細的除錯日誌

訪問：
- 前端：http://localhost:4000
- 後端：http://localhost:6000

#### 生產環境

```bash
# 使用 Makefile（推薦）
make prod

# 或使用 Docker Compose
docker-compose up
```

**生產環境特色：**
- ✅ Nginx 靜態檔案服務
- ✅ 優化的建置產物
- ✅ 生產級別配置

訪問：http://localhost:4000

### 3. 初始設定

1. 訪問系統設定頁面：http://localhost:4000/settings
2. 設定允許的音樂資料夾（例如：「華語」、「日語」、「英語」）
3. 設定支援的標籤和語言
4. 前往快取管理頁面重建快取

## Makefile 命令

專案提供了便捷的 Makefile 命令：

```bash
make help         # 顯示所有可用命令
make dev          # 啟動開發環境
make dev-d        # 背景啟動開發環境
make prod         # 啟動生產環境
make prod-d       # 背景啟動生產環境
make stop         # 停止所有服務
make logs         # 顯示開發環境日誌
make rebuild      # 重建並啟動開發環境
make restart      # 重啟開發環境
make ps           # 查看容器狀態
```

## 專案結構

```
.
├── backend/              # 後端服務
│   ├── app/
│   │   ├── router/       # API 路由
│   │   ├── dependencies/ # 依賴注入
│   │   └── data/         # 資料檔案
│   ├── Dockerfile.dev    # 開發環境 Dockerfile
│   └── Dockerfile.prod   # 生產環境 Dockerfile
├── frontend/             # 前端服務
│   ├── src/
│   │   ├── pages/        # 頁面元件
│   │   ├── components/   # UI 元件
│   │   └── lib/          # 工具函式
│   ├── Dockerfile.dev    # 開發環境 Dockerfile
│   └── Dockerfile.nginx  # 生產環境 Dockerfile (Nginx)
├── docker-compose.yml        # 生產環境 Compose
├── docker-compose.dev.yml    # 開發環境 Compose
├── Makefile                  # 便捷命令
├── README.md                 # 本文件
├── README.dev.md             # 開發環境詳細說明
└── README.prod.md            # 生產環境詳細說明
```

## 開發指南

### 前端開發

1. 修改 `frontend/src/` 下的檔案
2. Vite 會自動偵測變更並熱重載
3. 瀏覽器自動刷新

### 後端開發

1. 修改 `backend/app/` 下的 Python 檔案
2. Uvicorn 會自動偵測變更並重啟
3. API 變更立即生效

### 查看日誌

```bash
# 所有服務
make logs

# 特定服務
docker-compose -f docker-compose.dev.yml logs -f backend
docker-compose -f docker-compose.dev.yml logs -f frontend
```

## 常見問題

### Q: 修改後沒有自動更新？

**前端：** 檢查瀏覽器控制台是否有 HMR 連接錯誤
```bash
docker-compose -f docker-compose.dev.yml logs frontend
```

**後端：** 檢查是否有語法錯誤
```bash
docker-compose -f docker-compose.dev.yml logs backend
```

### Q: 快取管理頁面空白？

這是因為尚未設定音樂資料夾。請：
1. 前往系統設定頁面
2. 新增允許的音樂資料夾
3. 回到快取管理頁面重建快取

### Q: 資料庫資料會保留嗎？

是的，使用 Docker volumes 儲存：
```bash
# 停止但保留資料
make stop

# 停止並刪除資料（危險！）
make clean
```

### Q: 如何切換環境？

```bash
# 從生產切換到開發
make stop
make dev

# 從開發切換到生產
make stop
make prod
```

### Q: 權限問題？

檢查 `.env` 中的 `USER_ID` 和 `GROUP_ID` 是否與您的系統用戶一致：
```bash
id -u  # 查看 USER_ID
id -g  # 查看 GROUP_ID
```

## 詳細文件

- [開發環境詳細說明](README.dev.md)
- [生產環境詳細說明](README.prod.md)
- [權限修復指南](PERMISSION_FIX.md)

## API 文件

啟動服務後訪問：
- Swagger UI: http://localhost:6000/docs
- ReDoc: http://localhost:6000/redoc

## 授權

本專案為個人使用專案。

## 貢獻

歡迎提交 Issue 和 Pull Request！

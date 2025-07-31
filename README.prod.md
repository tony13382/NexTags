# 生產環境部署說明

## 文件結構

```
├── docker-compose.prod.yml    # 生產環境 Docker Compose 配置
├── backend/
│   └── Dockerfile.prod        # 後端生產環境 Dockerfile
├── frontend/
│   ├── Dockerfile.prod        # 前端生產環境 Dockerfile
│   └── next.config.ts         # Next.js 配置 (已啟用 standalone 模式)
└── nginx/
    └── nginx.conf             # Nginx 反向代理配置
```

## 服務架構

- **Nginx** (Port 80): 反向代理服務器
  - `/` → 前端服務 (Next.js)
  - `/api` → 後端服務 (FastAPI)
  - `/health` → 後端健康檢查

- **Frontend**: Next.js 應用 (內部 Port 3000)
- **Backend**: FastAPI 應用 (內部 Port 8000, 4個worker)

## 部署命令

```bash
# 構建並啟動所有服務
docker-compose -f docker-compose.prod.yml up -d --build

# 查看服務狀態
docker-compose -f docker-compose.prod.yml ps

# 查看日誌
docker-compose -f docker-compose.prod.yml logs -f

# 停止服務
docker-compose -f docker-compose.prod.yml down
```

## 訪問方式

- 前端: http://localhost/
- 後端API: http://localhost/api/
- 健康檢查: http://localhost/health

## 注意事項

1. 確保 `./Music` 目錄存在，這是音樂文件的掛載點
2. 前端的 API 請求會自動路由到 `/api` 端點
3. 所有服務都會在容器重啟時自動重新啟動
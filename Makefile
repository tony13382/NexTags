.PHONY: help dev prod stop clean logs rebuild test

# 預設目標
help:
	@echo "可用的命令："
	@echo "  make dev        - 啟動開發環境"
	@echo "  make prod       - 啟動生產環境"
	@echo "  make stop       - 停止當前運行的環境"
	@echo "  make clean      - 停止並清除所有資料（危險操作！）"
	@echo "  make logs       - 顯示開發環境日誌"
	@echo "  make logs-prod  - 顯示生產環境日誌"
	@echo "  make rebuild    - 重建並啟動開發環境"
	@echo "  make rebuild-prod - 重建並啟動生產環境"
	@echo "  make restart    - 重啟開發環境"

# 啟動開發環境
dev:
	@echo "🚀 啟動開發環境..."
	docker-compose -f docker-compose.dev.yml up

# 背景啟動開發環境
dev-d:
	@echo "🚀 背景啟動開發環境..."
	docker-compose -f docker-compose.dev.yml up -d
	@echo "✅ 開發環境已在背景啟動"
	@echo "   前端: http://localhost:4000"
	@echo "   後端: http://localhost:6000"
	@echo "   查看日誌: make logs"

# 啟動生產環境
prod:
	@echo "🚀 啟動生產環境..."
	docker-compose up

# 背景啟動生產環境
prod-d:
	@echo "🚀 背景啟動生產環境..."
	docker-compose up -d
	@echo "✅ 生產環境已在背景啟動"
	@echo "   前端: http://localhost:4000"
	@echo "   後端: http://localhost:6000"

# 停止當前環境
stop:
	@echo "⏸️  停止所有服務..."
	-docker-compose -f docker-compose.dev.yml down 2>/dev/null || true
	-docker-compose down 2>/dev/null || true
	@echo "✅ 所有服務已停止"

# 清除所有資料（危險操作）
clean:
	@echo "⚠️  警告：這將刪除所有資料，包括資料庫！"
	@read -p "確定要繼續嗎？[y/N] " -n 1 -r; \
	echo; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		docker-compose -f docker-compose.dev.yml down -v; \
		docker-compose down -v; \
		echo "✅ 所有資料已清除"; \
	else \
		echo "❌ 操作已取消"; \
	fi

# 顯示開發環境日誌
logs:
	docker-compose -f docker-compose.dev.yml logs -f

# 顯示生產環境日誌
logs-prod:
	docker-compose logs -f

# 顯示特定服務的日誌
logs-backend:
	docker-compose -f docker-compose.dev.yml logs -f backend

logs-frontend:
	docker-compose -f docker-compose.dev.yml logs -f frontend

# 重建開發環境
rebuild:
	@echo "🔨 重建開發環境..."
	docker-compose -f docker-compose.dev.yml up --build --force-recreate

# 重建生產環境
rebuild-prod:
	@echo "🔨 重建生產環境..."
	docker-compose up --build --force-recreate

# 重啟開發環境
restart:
	@echo "🔄 重啟開發環境..."
	docker-compose -f docker-compose.dev.yml restart
	@echo "✅ 開發環境已重啟"

# 進入後端容器 shell
shell-backend:
	docker-compose -f docker-compose.dev.yml exec backend bash

# 進入前端容器 shell
shell-frontend:
	docker-compose -f docker-compose.dev.yml exec frontend sh

# 查看容器狀態
ps:
	@echo "開發環境容器狀態："
	@docker-compose -f docker-compose.dev.yml ps
	@echo "\n生產環境容器狀態："
	@docker-compose ps

#!/bin/bash
set -e

# 如果 /Music 目錄存在，確保 appuser 有寫入權限
if [ -d "/Music" ]; then
    echo "檢查 /Music 目錄權限..."

    # 嘗試創建測試檔案來檢查寫入權限
    if ! touch /Music/.permission_test 2>/dev/null; then
        echo "警告: 無法寫入 /Music 目錄"
        echo "請執行以下命令修復權限:"
        echo "  docker exec -u root <container_name> chmod -R a+w /Music"
    else
        rm -f /Music/.permission_test
        echo "✓ /Music 目錄權限正常"
    fi
fi

# 啟動應用
exec "$@"

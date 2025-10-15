# Docker 權限配置說明

## 問題說明

Docker 容器中的應用需要能夠讀寫掛載的音樂檔案目錄 `/Music`。如果容器內的用戶 UID/GID 與主機用戶不一致，會導致權限問題。

## 已配置的解決方案

### 1. 自動 UID/GID 匹配

在 `.env` 文件中配置了：
```env
USER_ID=197609
GROUP_ID=197609
```

這些值與您的主機用戶 UID/GID 一致，Docker 會自動使用這些值創建容器內的用戶。

### 2. 權限檢查腳本

容器啟動時會自動檢查 `/Music` 目錄的寫入權限，如果有問題會顯示警告和修復命令。

## 如果遇到權限問題

### 方法 1: 重新構建容器（推薦）

```bash
cd C:\Users\tony1\Music\Server\Personal-MusicManager
docker-compose down
docker-compose build --no-cache backend
docker-compose up -d
```

### 方法 2: 手動修復現有容器的權限

```bash
# 給所有用戶添加寫入權限（快速）
docker exec -u root personal-musicmanager-backend-1 chmod -R a+w /Music

# 或者改變擁有者為 appuser（較慢但更安全）
docker exec -u root personal-musicmanager-backend-1 chown -R appuser:appuser /Music
```

### 方法 3: 修復主機端的權限（Windows）

在 Windows 上，確保 Docker Desktop 有權限訪問音樂目錄：
1. 打開 Docker Desktop Settings
2. 進入 Resources > File Sharing
3. 確保 `C:\Users\tony1\Music` 已添加到共享目錄列表
4. 重啟 Docker Desktop

## 檢查權限狀態

```bash
# 檢查容器內用戶
docker exec personal-musicmanager-backend-1 id

# 檢查音樂目錄權限
docker exec personal-musicmanager-backend-1 ls -la /Music | head -10

# 查看容器日誌中的權限檢查結果
docker logs personal-musicmanager-backend-1 | grep -i "permission\|權限"
```

## 新增音樂檔案時的注意事項

當您在主機上添加新的音樂檔案時：

### Windows 系統
- 檔案會自動繼承目錄的權限
- 通常不需要額外操作

### Linux/macOS 系統
- 新檔案可能需要設置正確的權限：
  ```bash
  # 在主機上執行
  chmod -R 666 /path/to/new/music/files
  chmod -R 777 /path/to/new/music/directories
  ```

## 驗證配置是否生效

1. 重啟容器：
   ```bash
   docker-compose restart backend
   ```

2. 查看日誌確認權限檢查通過：
   ```bash
   docker logs personal-musicmanager-backend-1 --tail 20
   ```

3. 嘗試編輯一個音樂檔案的標籤，應該會成功。

## 技術細節

- **容器用戶**: appuser (UID: 197609, GID: 197609)
- **主機用戶**: Homo (UID: 197609, GID: 197609)
- **掛載目錄**: C:/Users/tony1/Music -> /Music (rw)
- **權限模式**: 讀寫 (rw)

通過匹配 UID/GID，容器內的 appuser 與主機用戶具有相同的權限，可以無縫讀寫音樂檔案。

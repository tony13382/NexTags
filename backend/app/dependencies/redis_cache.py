import json
import os
from typing import Dict, Optional, Any
import redis
from app.dependencies.logger import logger
from app.dependencies.mp3tag_reader import read_audio_tags


class RedisCache:
    def __init__(self):
        # 從環境變數讀取 Redis 連線資訊
        redis_host = os.getenv('REDIS_HOST', 'localhost')
        redis_port = int(os.getenv('REDIS_PORT', 6379))
        redis_db = int(os.getenv('REDIS_DB', 0))

        try:
            self.client = redis.Redis(
                host=redis_host,
                port=redis_port,
                db=redis_db,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_keepalive=True,
                retry_on_timeout=True
            )
            # 測試連線
            self.client.ping()
            logger.info(f"成功連接到 Redis: {redis_host}:{redis_port}")
        except Exception as e:
            logger.error(f"無法連接到 Redis: {str(e)}")
            raise

    def _get_cache_key(self, file_path: str) -> str:
        """生成快取鍵名"""
        return f"audio_tags:{file_path}"

    def get_tags(self, file_path: str) -> Optional[Dict[str, Any]]:
        """從快取獲取標籤"""
        try:
            cache_key = self._get_cache_key(file_path)
            cached_data_str = self.client.get(cache_key)

            if not cached_data_str:
                return None

            cached_data = json.loads(cached_data_str)

            # 檢查檔案是否仍然存在
            if not os.path.exists(file_path):
                logger.warning(f"檔案不存在，將從快取中移除: {file_path}")
                self.remove_tags(file_path)
                return None

            # 檢查檔案修改時間是否有變化
            try:
                current_mtime = os.path.getmtime(file_path)
                cached_mtime = cached_data.get('modification_time', 0)

                if current_mtime != cached_mtime:
                    logger.info(f"檔案已修改，需要重新讀取標籤: {file_path}")
                    return None

                return cached_data.get('tags', {})
            except Exception as e:
                logger.error(f"檢查檔案修改時間時發生錯誤 {file_path}: {str(e)}")
                return None
        except Exception as e:
            logger.error(f"從 Redis 獲取標籤時發生錯誤 {file_path}: {str(e)}")
            return None

    def _serialize_tags(self, tags: Dict[str, Any]) -> Dict[str, Any]:
        """將標籤資料序列化為 JSON 可序列化的格式"""
        serialized = {}
        for key, value in tags.items():
            if isinstance(value, (str, int, float, bool, type(None))):
                serialized[key] = value
            elif isinstance(value, list):
                serialized[key] = [str(v) if not isinstance(v, (str, int, float, bool, type(None))) else v for v in value]
            else:
                # 將不可序列化的物件轉為字串
                serialized[key] = str(value)
        return serialized

    def set_tags(self, file_path: str, tags: Dict[str, Any], ttl: Optional[int] = None):
        """將標籤加入快取

        Args:
            file_path: 檔案路徑
            tags: 標籤資料
            ttl: 過期時間（秒），None 表示永不過期
        """
        try:
            modification_time = os.path.getmtime(file_path) if os.path.exists(file_path) else 0

            # 序列化標籤資料
            serialized_tags = self._serialize_tags(tags)

            cache_data = {
                'tags': serialized_tags,
                'modification_time': modification_time
            }

            cache_key = self._get_cache_key(file_path)
            cache_data_str = json.dumps(cache_data, ensure_ascii=False)

            if ttl:
                self.client.setex(cache_key, ttl, cache_data_str)
            else:
                self.client.set(cache_key, cache_data_str)

            logger.debug(f"已快取標籤: {file_path}")
        except Exception as e:
            logger.error(f"快取標籤時發生錯誤 {file_path}: {str(e)}")

    def remove_tags(self, file_path: str):
        """從快取中移除指定檔案的標籤"""
        try:
            cache_key = self._get_cache_key(file_path)
            self.client.delete(cache_key)
            logger.info(f"已從快取中移除: {file_path}")
        except Exception as e:
            logger.error(f"從快取移除標籤時發生錯誤 {file_path}: {str(e)}")

    def rebuild_cache(self, file_paths: list[str]):
        """重建快取"""
        logger.info(f"開始重建標籤快取，包含 {len(file_paths)} 個檔案")

        success_count = 0
        removed_files = []

        # 清空舊快取
        try:
            # 使用 SCAN 來遍歷所有 audio_tags: 開頭的鍵
            cursor = 0
            pattern = "audio_tags:*"
            while True:
                cursor, keys = self.client.scan(cursor, match=pattern, count=100)
                if keys:
                    self.client.delete(*keys)
                if cursor == 0:
                    break
            logger.info("已清空舊快取")
        except Exception as e:
            logger.error(f"清空舊快取時發生錯誤: {str(e)}")

        # 處理新的檔案列表
        for file_path in file_paths:
            if os.path.exists(file_path):
                try:
                    tags = read_audio_tags(file_path)
                    self.set_tags(file_path, tags)
                    success_count += 1
                except Exception as e:
                    logger.error(f"讀取檔案標籤時發生錯誤 {file_path}: {str(e)}")
            else:
                removed_files.append(file_path)

        logger.info(f"快取重建完成，成功快取 {success_count} 個檔案")
        if removed_files:
            logger.info(f"移除了 {len(removed_files)} 個不存在的檔案")

        return {
            'total_files': success_count,
            'removed_files': removed_files
        }

    def get_cached_tags_with_fallback(self, file_path: str) -> Dict[str, Any]:
        """獲取標籤，如果快取中沒有或過期則重新讀取並快取"""
        cached_tags = self.get_tags(file_path)

        if cached_tags is not None:
            return cached_tags

        # 快取中沒有或已過期，重新讀取
        tags = read_audio_tags(file_path)
        self.set_tags(file_path, tags)
        return tags

    def clear_cache(self):
        """清空快取"""
        try:
            cursor = 0
            pattern = "audio_tags:*"
            total_deleted = 0

            while True:
                cursor, keys = self.client.scan(cursor, match=pattern, count=100)
                if keys:
                    deleted = self.client.delete(*keys)
                    total_deleted += deleted
                if cursor == 0:
                    break

            logger.info(f"已清空標籤快取，共刪除 {total_deleted} 個快取項目")
        except Exception as e:
            logger.error(f"清空快取時發生錯誤: {str(e)}")
            raise

    def get_cache_size(self) -> int:
        """獲取快取大小（快取的檔案數量）"""
        try:
            cursor = 0
            pattern = "audio_tags:*"
            count = 0

            while True:
                cursor, keys = self.client.scan(cursor, match=pattern, count=100)
                count += len(keys)
                if cursor == 0:
                    break

            return count
        except Exception as e:
            logger.error(f"獲取快取大小時發生錯誤: {str(e)}")
            return 0

    def get_cache_info(self) -> Dict[str, Any]:
        """獲取快取資訊"""
        try:
            info = self.client.info('memory')
            cache_size = self.get_cache_size()

            return {
                'cached_files_count': cache_size,
                'memory_used_bytes': info.get('used_memory', 0),
                'memory_used_human': info.get('used_memory_human', 'N/A'),
                'redis_version': self.client.info('server').get('redis_version', 'N/A')
            }
        except Exception as e:
            logger.error(f"獲取快取資訊時發生錯誤: {str(e)}")
            return {
                'cached_files_count': 0,
                'memory_used_bytes': 0,
                'memory_used_human': 'N/A',
                'redis_version': 'N/A'
            }

    def get_cache_stats_by_folders(self, folder_paths: Dict[str, str]) -> Dict[str, int]:
        """獲取各資料夾的快取統計

        Args:
            folder_paths: {folder_name: folder_path} 的字典

        Returns:
            {folder_name: count} 的字典
        """
        try:
            stats = {}
            cursor = 0
            pattern = "audio_tags:*"

            # 初始化所有資料夾計數為 0
            for folder_name in folder_paths.keys():
                stats[folder_name] = 0

            # 掃描所有快取鍵
            while True:
                cursor, keys = self.client.scan(cursor, match=pattern, count=100)

                for key in keys:
                    # 移除 "audio_tags:" 前綴得到檔案路徑
                    file_path = key.replace("audio_tags:", "")

                    # 檢查該檔案屬於哪個資料夾
                    for folder_name, folder_path in folder_paths.items():
                        if file_path.startswith(folder_path):
                            stats[folder_name] += 1
                            break

                if cursor == 0:
                    break

            return stats
        except Exception as e:
            logger.error(f"獲取資料夾快取統計時發生錯誤: {str(e)}")
            return {folder_name: 0 for folder_name in folder_paths.keys()}


# 建立全域快取實例
try:
    redis_cache = RedisCache()
except Exception as e:
    logger.error(f"無法初始化 Redis 快取: {str(e)}")
    redis_cache = None

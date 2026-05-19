import json
import os
from datetime import datetime, timezone
from typing import Callable, Dict, Optional, Any, List
import redis
from app.dependencies.logger import logger
from app.dependencies.mp3tag_reader import read_audio_tags


class RedisCache:
    AUDIO_TAG_PATTERN = "audio_tags:*"
    CATALOG_RECORD_PATTERN = "audio_catalog:record:*"
    CATALOG_FOLDER_PATTERN = "audio_catalog:folder:*"
    CATALOG_PATHS_KEY = "audio_catalog:paths"
    CATALOG_REBUILD_KEY = "audio_catalog:last_rebuild_at"

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

    def _get_catalog_record_key(self, file_path: str) -> str:
        """生成音訊 catalog record 鍵名"""
        return f"audio_catalog:record:{file_path}"

    def _get_catalog_folder_key(self, folder_name: str) -> str:
        """生成音訊 catalog folder set 鍵名"""
        return f"audio_catalog:folder:{folder_name}"

    def _clear_keys(self, pattern: str) -> int:
        """以 SCAN 清除符合 pattern 的鍵"""
        cursor = 0
        total_deleted = 0
        while True:
            cursor, keys = self.client.scan(cursor, match=pattern, count=100)
            if keys:
                total_deleted += self.client.delete(*keys)
            if cursor == 0:
                break
        return total_deleted

    def _find_cover_art(self, file_path: str) -> str:
        """在音訊檔案同目錄下尋找封面圖檔。只在 catalog 建立時執行。"""
        directory = os.path.dirname(file_path)
        cover_names = [
            'cover.jpg', 'cover.jpeg', 'cover.png',
            'folder.jpg', 'folder.jpeg', 'folder.png',
            'albumart.jpg', 'albumart.jpeg', 'albumart.png'
        ]

        for cover_name in cover_names:
            cover_path = os.path.join(directory, cover_name)
            if os.path.exists(cover_path):
                return cover_path
        return ""

    def _infer_main_folder(
        self,
        file_path: str,
        folder_paths: Optional[Dict[str, str]] = None
    ) -> str:
        """從 allow folder 對照或 /Music 路徑推導主資料夾名稱"""
        normalized_path = os.path.normpath(file_path)

        if folder_paths:
            for folder_name, folder_path in folder_paths.items():
                normalized_folder = os.path.normpath(folder_path)
                if normalized_path == normalized_folder or normalized_path.startswith(normalized_folder + os.sep):
                    return folder_name

        music_root = os.path.normpath("/Music")
        if normalized_path.startswith(music_root + os.sep):
            relative_path = normalized_path[len(music_root) + 1:]
            return relative_path.split(os.sep, 1)[0] if relative_path else "unknown"

        return "unknown"

    def _build_catalog_record(
        self,
        file_path: str,
        tags: Dict[str, Any],
        folder_paths: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """建立供列表與播放清單直接查詢的音訊 catalog record"""
        main_folder = self._infer_main_folder(file_path, folder_paths)
        folder_root = (folder_paths or {}).get(main_folder, os.path.join("/Music", main_folder))
        serialized_tags = self._serialize_tags(tags)

        try:
            relative_path = os.path.relpath(file_path, folder_root)
        except Exception:
            relative_path = os.path.basename(file_path)

        modification_time = os.path.getmtime(file_path) if os.path.exists(file_path) else 0
        file_size = os.path.getsize(file_path) if os.path.exists(file_path) else 0

        return {
            "file_path": file_path,
            "main_folder": main_folder,
            "relative_path": relative_path,
            "modification_time": modification_time,
            "size": file_size,
            "cover_path": self._find_cover_art(file_path),
            "tags": serialized_tags,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }

    def _build_catalog_record_from_cached_data(
        self,
        file_path: str,
        cached_data: Dict[str, Any],
        folder_paths: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """用既有 audio_tags 快取建立 catalog record，不觸發檔案系統讀取。"""
        tags = cached_data.get("tags", {}) or {}
        main_folder = self._infer_main_folder(file_path, folder_paths)
        folder_root = (folder_paths or {}).get(main_folder, os.path.join("/Music", main_folder))

        try:
            relative_path = os.path.relpath(file_path, folder_root)
        except Exception:
            relative_path = os.path.basename(file_path)

        return {
            "file_path": file_path,
            "main_folder": main_folder,
            "relative_path": relative_path,
            "modification_time": cached_data.get("modification_time", 0),
            "size": cached_data.get("size", 0),
            "cover_path": cached_data.get("cover_path", ""),
            "tags": tags,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }

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
            record_key = self._get_catalog_record_key(file_path)
            old_record_str = self.client.get(record_key)

            pipe = self.client.pipeline()
            pipe.delete(cache_key)
            pipe.delete(record_key)
            pipe.srem(self.CATALOG_PATHS_KEY, file_path)

            if old_record_str:
                try:
                    old_record = json.loads(old_record_str)
                    old_folder = old_record.get("main_folder")
                    if old_folder:
                        pipe.srem(self._get_catalog_folder_key(old_folder), file_path)
                except Exception:
                    pass

            pipe.execute()
            logger.info(f"已從快取中移除: {file_path}")
        except Exception as e:
            logger.error(f"從快取移除標籤時發生錯誤 {file_path}: {str(e)}")

    def upsert_audio_record(
        self,
        file_path: str,
        tags: Optional[Dict[str, Any]] = None,
        folder_paths: Optional[Dict[str, str]] = None
    ) -> Optional[Dict[str, Any]]:
        """更新單一音訊檔案的 tag cache 與 Redis catalog record"""
        try:
            if not os.path.exists(file_path):
                self.remove_tags(file_path)
                return None

            if tags is None:
                tags = read_audio_tags(file_path)

            self.set_tags(file_path, tags)
            record = self._build_catalog_record(file_path, tags, folder_paths)
            record_key = self._get_catalog_record_key(file_path)
            old_record_str = self.client.get(record_key)

            pipe = self.client.pipeline()
            if old_record_str:
                try:
                    old_record = json.loads(old_record_str)
                    old_folder = old_record.get("main_folder")
                    if old_folder and old_folder != record["main_folder"]:
                        pipe.srem(self._get_catalog_folder_key(old_folder), file_path)
                except Exception:
                    pass

            pipe.set(record_key, json.dumps(record, ensure_ascii=False))
            pipe.sadd(self.CATALOG_PATHS_KEY, file_path)
            pipe.sadd(self._get_catalog_folder_key(record["main_folder"]), file_path)
            pipe.execute()
            return record
        except Exception as e:
            logger.error(f"更新音訊 catalog 時發生錯誤 {file_path}: {str(e)}")
            return None

    def rebuild_cache(
        self,
        file_paths: list[str],
        progress_callback: Optional[Callable[[int, int], None]] = None,
        folder_paths: Optional[Dict[str, str]] = None
    ):
        """重建快取"""
        logger.info(f"開始重建標籤快取，包含 {len(file_paths)} 個檔案")

        success_count = 0
        removed_files = []

        # 清空舊快取
        try:
            deleted_tags = self._clear_keys(self.AUDIO_TAG_PATTERN)
            deleted_records = self._clear_keys(self.CATALOG_RECORD_PATTERN)
            deleted_folders = self._clear_keys(self.CATALOG_FOLDER_PATTERN)
            self.client.delete(self.CATALOG_PATHS_KEY)
            self.client.delete(self.CATALOG_REBUILD_KEY)
            logger.info(f"已清空舊快取：tags={deleted_tags}, records={deleted_records}, folders={deleted_folders}")
        except Exception as e:
            logger.error(f"清空舊快取時發生錯誤: {str(e)}")

        # 處理新的檔案列表
        total_files = len(file_paths)
        for index, file_path in enumerate(file_paths, start=1):
            if os.path.exists(file_path):
                try:
                    tags = read_audio_tags(file_path)
                    self.upsert_audio_record(file_path, tags, folder_paths)
                    success_count += 1
                except Exception as e:
                    logger.error(f"讀取檔案標籤時發生錯誤 {file_path}: {str(e)}")
            else:
                removed_files.append(file_path)

            if progress_callback and (index == total_files or index % 10 == 0):
                progress_callback(index, total_files)

        logger.info(f"快取重建完成，成功快取 {success_count} 個檔案")
        if removed_files:
            logger.info(f"移除了 {len(removed_files)} 個不存在的檔案")

        self.client.set(self.CATALOG_REBUILD_KEY, datetime.now(timezone.utc).isoformat())

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
            total_deleted = self._clear_keys(self.AUDIO_TAG_PATTERN)
            total_deleted += self._clear_keys(self.CATALOG_RECORD_PATTERN)
            total_deleted += self._clear_keys(self.CATALOG_FOLDER_PATTERN)
            total_deleted += self.client.delete(self.CATALOG_PATHS_KEY)
            total_deleted += self.client.delete(self.CATALOG_REBUILD_KEY)

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

            # 初始化所有資料夾計數為 0
            for folder_name in folder_paths.keys():
                stats[folder_name] = 0

            if self.client.exists(self.CATALOG_PATHS_KEY):
                for folder_name in folder_paths.keys():
                    stats[folder_name] = self.client.scard(self._get_catalog_folder_key(folder_name))
                return stats

            cursor = 0
            pattern = "audio_tags:*"

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

    def get_audio_records(self, base_folders: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """從 Redis catalog 讀取音訊 records，不觸發檔案系統掃描"""
        try:
            if base_folders:
                file_paths = set()
                for folder_name in base_folders:
                    file_paths.update(self.client.smembers(self._get_catalog_folder_key(folder_name)))
            else:
                file_paths = set(self.client.smembers(self.CATALOG_PATHS_KEY))

            if not file_paths:
                if not self.client.exists(self.CATALOG_PATHS_KEY):
                    return self.seed_catalog_from_tag_cache(base_folders=base_folders)
                return []

            sorted_paths = sorted(file_paths)
            keys = [self._get_catalog_record_key(file_path) for file_path in sorted_paths]
            record_values = self.client.mget(keys)

            records = []
            for value in record_values:
                if not value:
                    continue
                try:
                    records.append(json.loads(value))
                except json.JSONDecodeError:
                    continue
            return records
        except Exception as e:
            logger.error(f"讀取音訊 catalog 時發生錯誤: {str(e)}")
            return []

    def seed_catalog_from_tag_cache(
        self,
        base_folders: Optional[List[str]] = None,
        folder_paths: Optional[Dict[str, str]] = None
    ) -> List[Dict[str, Any]]:
        """從既有 audio_tags:* 建立 Redis catalog，避免第一次查詢就掃檔案系統。"""
        try:
            requested_folders = set(base_folders or [])
            records = []
            cursor = 0
            batch_count = 0
            pipe = self.client.pipeline()

            while True:
                cursor, keys = self.client.scan(cursor, match=self.AUDIO_TAG_PATTERN, count=100)

                for key in keys:
                    file_path = key.replace("audio_tags:", "", 1)
                    cached_data_str = self.client.get(key)
                    if not cached_data_str:
                        continue

                    try:
                        cached_data = json.loads(cached_data_str)
                    except json.JSONDecodeError:
                        continue

                    record = self._build_catalog_record_from_cached_data(file_path, cached_data, folder_paths)
                    record_key = self._get_catalog_record_key(file_path)

                    pipe.set(record_key, json.dumps(record, ensure_ascii=False))
                    pipe.sadd(self.CATALOG_PATHS_KEY, file_path)
                    pipe.sadd(self._get_catalog_folder_key(record["main_folder"]), file_path)
                    batch_count += 1

                    if not requested_folders or record["main_folder"] in requested_folders:
                        records.append(record)

                    if batch_count >= 100:
                        pipe.execute()
                        pipe = self.client.pipeline()
                        batch_count = 0

                if cursor == 0:
                    break

            if batch_count:
                pipe.execute()

            if records:
                self.client.set(self.CATALOG_REBUILD_KEY, f"seeded_from_tag_cache:{datetime.now(timezone.utc).isoformat()}")
                logger.info(f"已從既有 tag cache 建立音訊 catalog，共 {len(records)} 筆可用 records")

            return records
        except Exception as e:
            logger.error(f"從 tag cache 建立音訊 catalog 時發生錯誤: {str(e)}")
            return []

    def get_catalog_info(self) -> Dict[str, Any]:
        """取得 Redis catalog 基本資訊"""
        try:
            return {
                "records_count": self.client.scard(self.CATALOG_PATHS_KEY),
                "last_rebuild_at": self.client.get(self.CATALOG_REBUILD_KEY)
            }
        except Exception as e:
            logger.error(f"獲取 catalog 資訊時發生錯誤: {str(e)}")
            return {
                "records_count": 0,
                "last_rebuild_at": None
            }


# 建立全域快取實例
try:
    redis_cache = RedisCache()
except Exception as e:
    logger.error(f"無法初始化 Redis 快取: {str(e)}")
    redis_cache = None

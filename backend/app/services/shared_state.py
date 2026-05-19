"""跨重啟 / 多 worker 共享的狀態文件（Redis 持久化，含記憶體 fallback）。

用於批量任務的單一狀態文件（batch replaygain / batch m3u）。
值必須為 JSON 原生型別（str/int/float/bool/None/list/dict）。
"""
import json
import threading
from typing import Any, Dict, Optional

from app.dependencies.logger import logger


class RedisDoc:
    """一份以單一 Redis key 持久化的 JSON 文件；Redis 不可用時退回行程內記憶體。"""

    def __init__(self, key: str, default: Dict[str, Any], ttl: Optional[int] = None):
        self._key = key
        self._default = default
        self._ttl = ttl
        self._lock = threading.Lock()
        self._mem: Dict[str, Any] = json.loads(json.dumps(default))
        try:
            from app.dependencies.redis_cache import redis_cache
            self._redis = redis_cache.client if redis_cache is not None else None
        except Exception as e:
            logger.error(f"RedisDoc({key}) 取得 Redis 連線失敗，改用記憶體模式: {e}")
            self._redis = None

    def get(self) -> Dict[str, Any]:
        """讀取目前文件（回傳副本；不存在時回傳預設值副本）。"""
        try:
            if self._redis is not None:
                value = self._redis.get(self._key)
                if not value:
                    return json.loads(json.dumps(self._default))
                return json.loads(value)
            with self._lock:
                return json.loads(json.dumps(self._mem))
        except Exception as e:
            logger.error(f"RedisDoc({self._key}) 讀取失敗: {e}")
            return json.loads(json.dumps(self._default))

    def set(self, doc: Dict[str, Any]):
        """整份覆寫。"""
        try:
            if self._redis is not None:
                payload = json.dumps(doc, ensure_ascii=False)
                if self._ttl:
                    self._redis.set(self._key, payload, ex=self._ttl)
                else:
                    self._redis.set(self._key, payload)
            else:
                with self._lock:
                    self._mem = json.loads(json.dumps(doc))
        except Exception as e:
            logger.error(f"RedisDoc({self._key}) 寫入失敗: {e}")

    def update(self, **kwargs) -> Dict[str, Any]:
        """讀取-合併-寫回（加鎖避免併發覆寫），回傳更新後文件。"""
        with self._lock:
            doc = self.get()
            doc.update(kwargs)
            self.set(doc)
            return doc

    def reset(self) -> Dict[str, Any]:
        """重設為預設值。"""
        doc = json.loads(json.dumps(self._default))
        self.set(doc)
        return doc

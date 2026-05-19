import asyncio
import json
import uuid
import threading
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List
from enum import Enum
from app.dependencies.logger import logger


class TaskStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


# Redis 鍵：每個任務一個 key（原子單筆寫入，消除舊版全檔 read-modify-write 競態），
# 另用一個 ZSET 以 created_at epoch 為 score 做有序、可限量的列表查詢。
TASK_KEY_PREFIX = "taskmgr:task:"
TASK_INDEX_ZSET = "taskmgr:index"
TASK_MIGRATED_FLAG = "taskmgr:migrated_from_file"


def _created_score(task: Dict[str, Any]) -> float:
    """以 created_at 轉成排序用 score；解析失敗時退回 0。"""
    try:
        return datetime.fromisoformat(task["created_at"]).timestamp()
    except Exception:
        return 0.0


class TaskManager:
    """異步任務管理器（Redis 持久化，跨重啟 / 多 worker 共享）。

    儲存層改用 Redis：每個任務獨立 key，更新為單筆原子寫入；
    若 Redis 不可用則退回行程內記憶體（不持久化但不影響服務可用性）。
    公開與既有私有 API（_load_tasks / _save_tasks）維持不變。
    """

    def __init__(self, storage_path: str = "app/data/tasks.json"):
        self.storage_path = Path(storage_path)
        self.task_queue: asyncio.Queue = asyncio.Queue()
        self.running_tasks: Dict[str, asyncio.Task] = {}
        self.worker_running = False
        self._lock = threading.Lock()
        # 記憶體 fallback（僅在 Redis 不可用時使用）
        self._memory_store: Dict[str, Any] = {}

        # 取用與 redis_cache 相同的連線設定；None 表示 Redis 不可用。
        try:
            from app.dependencies.redis_cache import redis_cache
            self._redis = redis_cache.client if redis_cache is not None else None
        except Exception as e:
            logger.error(f"TaskManager 取得 Redis 連線失敗，改用記憶體模式: {e}")
            self._redis = None

        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        self._migrate_file_tasks_if_needed()
        self._mark_interrupted_tasks_failed()

    # ---- Redis 鍵工具 ----
    def _task_key(self, task_id: str) -> str:
        return f"{TASK_KEY_PREFIX}{task_id}"

    def _use_redis(self) -> bool:
        return self._redis is not None

    # ---- 一次性檔案遷移（不丟既有任務歷史，不刪原檔）----
    def _migrate_file_tasks_if_needed(self):
        if not self._use_redis():
            return
        try:
            if self._redis.get(TASK_MIGRATED_FLAG):
                return
            if not self.storage_path.exists():
                self._redis.set(TASK_MIGRATED_FLAG, datetime.now().isoformat())
                return
            with open(self.storage_path, "r", encoding="utf-8") as f:
                file_tasks = json.load(f)
            if isinstance(file_tasks, dict) and file_tasks:
                pipe = self._redis.pipeline()
                for task_id, task in file_tasks.items():
                    pipe.set(self._task_key(task_id), json.dumps(task, ensure_ascii=False))
                    pipe.zadd(TASK_INDEX_ZSET, {task_id: _created_score(task)})
                pipe.execute()
                logger.info(f"已將 {len(file_tasks)} 筆既有任務從 tasks.json 遷移到 Redis（原檔保留）")
            self._redis.set(TASK_MIGRATED_FLAG, datetime.now().isoformat())
        except Exception as e:
            logger.error(f"遷移 tasks.json 到 Redis 時發生錯誤: {e}")

    def _mark_interrupted_tasks_failed(self):
        """服務重啟後，將舊的 pending/running 任務標成失敗，避免卡住新任務。"""
        try:
            tasks = self._load_tasks()
            changed: Dict[str, Any] = {}
            for task_id, task in tasks.items():
                if task.get("status") in [TaskStatus.PENDING.value, TaskStatus.RUNNING.value]:
                    task["status"] = TaskStatus.FAILED.value
                    task["updated_at"] = datetime.now().isoformat()
                    task["error"] = "任務因服務重啟中斷"
                    changed[task_id] = task

            if changed:
                self._write_tasks(changed)
                logger.warning(f"已將服務重啟前未完成的 {len(changed)} 個任務標記為失敗")
        except Exception as e:
            logger.error(f"標記中斷任務時發生錯誤: {e}")

    # ---- 儲存層 ----
    def _write_tasks(self, tasks: Dict[str, Any]):
        """寫入（或覆寫）指定的數筆任務，不影響其他任務。"""
        if not tasks:
            return
        if self._use_redis():
            pipe = self._redis.pipeline()
            for task_id, task in tasks.items():
                pipe.set(self._task_key(task_id), json.dumps(task, ensure_ascii=False))
                pipe.zadd(TASK_INDEX_ZSET, {task_id: _created_score(task)})
            pipe.execute()
        else:
            with self._lock:
                self._memory_store.update(tasks)

    def _load_tasks(self) -> Dict[str, Any]:
        """載入全部任務狀態（保留給 tasks.py 的批次刪除 / 統計使用）。"""
        try:
            if self._use_redis():
                task_ids = self._redis.zrange(TASK_INDEX_ZSET, 0, -1)
                if not task_ids:
                    return {}
                keys = [self._task_key(tid) for tid in task_ids]
                values = self._redis.mget(keys)
                result: Dict[str, Any] = {}
                stale: List[str] = []
                for tid, value in zip(task_ids, values):
                    if not value:
                        stale.append(tid)
                        continue
                    try:
                        result[tid] = json.loads(value)
                    except json.JSONDecodeError:
                        stale.append(tid)
                if stale:
                    self._redis.zrem(TASK_INDEX_ZSET, *stale)
                return result
            with self._lock:
                return dict(self._memory_store)
        except Exception as e:
            logger.error(f"載入任務狀態失敗: {e}")
            return {}

    def _save_tasks(self, tasks: Dict[str, Any]):
        """保存任務狀態：以傳入的完整集合為準，缺少的任務視為刪除。

        維持與舊版相同語意，讓 tasks.py 的刪除 / 清理流程無需改動。
        """
        try:
            if self._use_redis():
                existing_ids = set(self._redis.zrange(TASK_INDEX_ZSET, 0, -1))
                new_ids = set(tasks.keys())
                removed = existing_ids - new_ids

                pipe = self._redis.pipeline()
                for task_id, task in tasks.items():
                    pipe.set(self._task_key(task_id), json.dumps(task, ensure_ascii=False))
                    pipe.zadd(TASK_INDEX_ZSET, {task_id: _created_score(task)})
                for task_id in removed:
                    pipe.delete(self._task_key(task_id))
                    pipe.zrem(TASK_INDEX_ZSET, task_id)
                pipe.execute()
            else:
                with self._lock:
                    self._memory_store = dict(tasks)
        except Exception as e:
            logger.error(f"保存任務狀態失敗: {e}")

    def create_task(self, task_type: str, task_data: Dict[str, Any]) -> str:
        """創建新任務"""
        task_id = str(uuid.uuid4())
        now = datetime.now().isoformat()
        task = {
            "task_id": task_id,
            "task_type": task_type,
            "status": TaskStatus.PENDING.value,
            "created_at": now,
            "updated_at": now,
            "data": task_data,
            "result": None,
            "error": None,
            "progress": 0,
        }
        # 單筆原子寫入，不需讀取/覆寫其他任務。
        self._write_tasks({task_id: task})

        # 將任務加入佇列（行程內派發；重啟前未處理者由啟動時標記為失敗）
        asyncio.create_task(self.task_queue.put({
            "task_id": task_id,
            "task_type": task_type,
            "data": task_data
        }))

        logger.info(f"創建任務: {task_id} (類型: {task_type})")
        return task_id

    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """獲取任務狀態"""
        try:
            if self._use_redis():
                value = self._redis.get(self._task_key(task_id))
                if not value:
                    return None
                return json.loads(value)
            with self._lock:
                return self._memory_store.get(task_id)
        except Exception as e:
            logger.error(f"讀取任務狀態失敗 {task_id}: {e}")
            return None

    def get_all_tasks(self, limit: int = 100) -> List[Dict[str, Any]]:
        """獲取任務（按創建時間新到舊），於儲存層做限量，避免 O(全部)。"""
        try:
            if self._use_redis():
                task_ids = self._redis.zrevrange(TASK_INDEX_ZSET, 0, max(0, limit - 1))
                if not task_ids:
                    return []
                values = self._redis.mget([self._task_key(tid) for tid in task_ids])
                tasks = []
                for value in values:
                    if not value:
                        continue
                    try:
                        tasks.append(json.loads(value))
                    except json.JSONDecodeError:
                        continue
                return tasks
            with self._lock:
                task_list = list(self._memory_store.values())
            task_list.sort(key=lambda x: x.get('created_at', ''), reverse=True)
            return task_list[:limit]
        except Exception as e:
            logger.error(f"讀取任務列表失敗: {e}")
            return []

    def update_task_status(self, task_id: str, status: TaskStatus,
                           result: Any = None, error: str = None, progress: int = None):
        """更新任務狀態（單筆 read-modify-write，加行程內鎖避免併發覆寫）。"""
        try:
            with self._lock:
                current = self.get_task_status(task_id)
                if not current:
                    return
                current['status'] = status.value
                current['updated_at'] = datetime.now().isoformat()
                if result is not None:
                    current['result'] = result
                if error is not None:
                    current['error'] = error
                if progress is not None:
                    current['progress'] = progress

                if self._use_redis():
                    self._redis.set(self._task_key(task_id),
                                    json.dumps(current, ensure_ascii=False))
                    self._redis.zadd(TASK_INDEX_ZSET, {task_id: _created_score(current)})
                else:
                    self._memory_store[task_id] = current
            logger.info(f"更新任務狀態: {task_id} -> {status.value}")
        except Exception as e:
            logger.error(f"更新任務狀態失敗 {task_id}: {e}")

    async def start_worker(self):
        """啟動任務工作器"""
        if self.worker_running:
            return

        self.worker_running = True
        logger.info("任務工作器已啟動")

        while self.worker_running:
            try:
                task_item = await asyncio.wait_for(
                    self.task_queue.get(), timeout=1.0
                )

                task_id = task_item["task_id"]
                task_type = task_item["task_type"]
                task_data = task_item["data"]

                self.update_task_status(task_id, TaskStatus.RUNNING)

                task_coroutine = self._execute_task(task_id, task_type, task_data)
                task = asyncio.create_task(task_coroutine)
                self.running_tasks[task_id] = task

                # 不等待任務完成，立即處理下一個

            except asyncio.TimeoutError:
                continue
            except Exception as e:
                # 單一迭代錯誤不可使工作器整體退出
                logger.error(f"任務工作器錯誤: {e}")

    def stop_worker(self):
        """停止任務工作器"""
        self.worker_running = False
        logger.info("任務工作器已停止")

    async def _execute_task(self, task_id: str, task_type: str, task_data: Dict[str, Any]):
        """執行任務"""
        try:
            logger.info(f"開始執行任務: {task_id} (類型: {task_type})")

            if task_type == "cache_rebuild":
                from app.router.cache import perform_cache_rebuild

                result = await perform_cache_rebuild(task_id)
            else:
                raise ValueError(f"未知的任務類型: {task_type}")

            self.update_task_status(task_id, TaskStatus.COMPLETED, result=result, progress=100)
            logger.info(f"任務完成: {task_id}")

        except Exception as e:
            error_msg = str(e)
            self.update_task_status(task_id, TaskStatus.FAILED, error=error_msg)
            logger.error(f"任務失敗: {task_id} - {error_msg}")

        finally:
            if task_id in self.running_tasks:
                del self.running_tasks[task_id]


# 創建全局任務管理器實例
task_manager = TaskManager()

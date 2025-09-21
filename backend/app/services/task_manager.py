import asyncio
import json
import uuid
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

class TaskManager:
    """異步任務管理器"""
    
    def __init__(self, storage_path: str = "app/data/tasks.json"):
        self.storage_path = Path(storage_path)
        self.task_queue: asyncio.Queue = asyncio.Queue()
        self.running_tasks: Dict[str, asyncio.Task] = {}
        self.worker_running = False
        
        # 確保存儲目錄存在
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        
    def _load_tasks(self) -> Dict[str, Any]:
        """載入任務狀態"""
        try:
            if self.storage_path.exists():
                with open(self.storage_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"載入任務狀態失敗: {e}")
        return {}
    
    def _save_tasks(self, tasks: Dict[str, Any]):
        """保存任務狀態"""
        try:
            with open(self.storage_path, 'w', encoding='utf-8') as f:
                json.dump(tasks, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存任務狀態失敗: {e}")
    
    def create_task(self, task_type: str, task_data: Dict[str, Any]) -> str:
        """創建新任務"""
        task_id = str(uuid.uuid4())
        
        tasks = self._load_tasks()
        tasks[task_id] = {
            "task_id": task_id,
            "task_type": task_type,
            "status": TaskStatus.PENDING.value,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "data": task_data,
            "result": None,
            "error": None,
            "progress": 0
        }
        self._save_tasks(tasks)
        
        # 將任務加入佇列
        asyncio.create_task(self.task_queue.put({
            "task_id": task_id,
            "task_type": task_type,
            "data": task_data
        }))
        
        logger.info(f"創建任務: {task_id} (類型: {task_type})")
        return task_id
    
    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """獲取任務狀態"""
        tasks = self._load_tasks()
        return tasks.get(task_id)
    
    def get_all_tasks(self, limit: int = 100) -> List[Dict[str, Any]]:
        """獲取所有任務（按創建時間排序）"""
        tasks = self._load_tasks()
        task_list = list(tasks.values())
        
        # 按創建時間排序（新到舊）
        task_list.sort(key=lambda x: x.get('created_at', ''), reverse=True)
        
        return task_list[:limit]
    
    def update_task_status(self, task_id: str, status: TaskStatus, 
                          result: Any = None, error: str = None, progress: int = None):
        """更新任務狀態"""
        tasks = self._load_tasks()
        if task_id in tasks:
            tasks[task_id]['status'] = status.value
            tasks[task_id]['updated_at'] = datetime.now().isoformat()
            
            if result is not None:
                tasks[task_id]['result'] = result
            if error is not None:
                tasks[task_id]['error'] = error
            if progress is not None:
                tasks[task_id]['progress'] = progress
                
            self._save_tasks(tasks)
            logger.info(f"更新任務狀態: {task_id} -> {status.value}")
    
    async def start_worker(self):
        """啟動任務工作器"""
        if self.worker_running:
            return
            
        self.worker_running = True
        logger.info("任務工作器已啟動")
        
        while self.worker_running:
            try:
                # 從佇列獲取任務
                task_item = await asyncio.wait_for(
                    self.task_queue.get(), timeout=1.0
                )
                
                task_id = task_item["task_id"]
                task_type = task_item["task_type"]
                task_data = task_item["data"]
                
                # 更新任務狀態為運行中
                self.update_task_status(task_id, TaskStatus.RUNNING)
                
                # 執行任務
                task_coroutine = self._execute_task(task_id, task_type, task_data)
                task = asyncio.create_task(task_coroutine)
                self.running_tasks[task_id] = task
                
                # 不等待任務完成，立即處理下一個
                
            except asyncio.TimeoutError:
                # 佇列為空，繼續等待
                continue
            except Exception as e:
                logger.error(f"任務工作器錯誤: {e}")
    
    def stop_worker(self):
        """停止任務工作器"""
        self.worker_running = False
        logger.info("任務工作器已停止")
    
    async def _execute_task(self, task_id: str, task_type: str, task_data: Dict[str, Any]):
        """執行任務"""
        try:
            logger.info(f"開始執行任務: {task_id} (類型: {task_type})")
            
            raise ValueError(f"未知的任務類型: {task_type}")
            
            # 任務完成
            self.update_task_status(task_id, TaskStatus.COMPLETED, result=result, progress=100)
            logger.info(f"任務完成: {task_id}")
            
        except Exception as e:
            # 任務失敗
            error_msg = str(e)
            self.update_task_status(task_id, TaskStatus.FAILED, error=error_msg)
            logger.error(f"任務失敗: {task_id} - {error_msg}")
        
        finally:
            # 清理運行任務記錄
            if task_id in self.running_tasks:
                del self.running_tasks[task_id]
    

# 創建全局任務管理器實例
task_manager = TaskManager()
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
            
            if task_type == "playlist_sync":
                result = await self._execute_playlist_sync(task_id, task_data)
            else:
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
    
    async def _execute_playlist_sync(self, task_id: str, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """執行播放清單同步任務"""
        from app.router.playlists import (
            load_playlists, find_audio_files, filter_songs_by_playlist,
            sort_songs_by_jellyfin_add_time, save_playlists
        )
        from app.dependencies.jellyfin_connetor import playlists as jellyfin_playlists
        from app.dependencies.tags_cache import tags_cache
        
        playlist_index = task_data["playlist_index"]
        
        # 更新進度: 開始載入播放清單
        self.update_task_status(task_id, TaskStatus.RUNNING, progress=10)
        
        # 載入播放清單
        playlists_data = load_playlists()
        if playlist_index >= len(playlists_data):
            raise ValueError(f"播放清單索引 {playlist_index} 不存在")
        
        playlist = playlists_data[playlist_index]
        jellyfin_playlist_id = playlist.get("jellyfin_playlist_id")
        
        if not jellyfin_playlist_id:
            raise ValueError("此播放清單沒有設定 Jellyfin Playlist ID")
        
        # 更新進度: 搜尋音樂檔案
        self.update_task_status(task_id, TaskStatus.RUNNING, progress=20)
        
        # 取得本地播放清單的歌曲
        audio_files = find_audio_files(playlist['base_folder'])
        filtered_songs = filter_songs_by_playlist(playlist, audio_files)
        
        if not filtered_songs:
            return {
                "message": f"播放清單 '{playlist['name']}' 沒有符合條件的歌曲",
                "songs_found": 0,
                "songs_added": 0
            }
        
        # 更新進度: 排序歌曲
        self.update_task_status(task_id, TaskStatus.RUNNING, progress=30)
        
        sorted_songs = sort_songs_by_jellyfin_add_time(filtered_songs)
        
        # 更新進度: 提取 Jellyfin ID
        self.update_task_status(task_id, TaskStatus.RUNNING, progress=40)
        
        jellyfin_song_ids = []
        for file_path in sorted_songs:
            try:
                tags = tags_cache.get_cached_tags_with_fallback(file_path)
                jellyfin_id = tags.get('jfid', '').strip()
                if jellyfin_id:
                    jellyfin_song_ids.append(jellyfin_id)
            except Exception as e:
                logger.error(f"讀取檔案標籤失敗: {file_path} - {str(e)}")
                continue
        
        if not jellyfin_song_ids:
            raise ValueError(f"播放清單 '{playlist['name']}' 中沒有找到有效的 Jellyfin ID")
        
        # 更新進度: 檢查 Jellyfin 播放清單
        self.update_task_status(task_id, TaskStatus.RUNNING, progress=50)
        
        existing_playlist = await jellyfin_playlists.get_playlist_by_id(jellyfin_playlist_id)
        if not existing_playlist:
            # 嘗試創建新的播放清單
            new_playlist_id = await jellyfin_playlists.create_playlist(
                name=playlist['name'],
                description=f"智慧播放清單：{playlist['name']}",
                song_ids=[]
            )
            
            if new_playlist_id:
                playlist['jellyfin_playlist_id'] = new_playlist_id
                playlists_data[playlist_index] = playlist
                save_playlists(playlists_data)
                jellyfin_playlist_id = new_playlist_id
                logger.info(f"成功創建新的 Jellyfin 播放清單，ID: {new_playlist_id}")
            else:
                raise ValueError(f"Jellyfin 中找不到 ID 為 {jellyfin_playlist_id} 的播放清單，且無法創建新的播放清單")
        
        # 更新進度: 清空播放清單
        self.update_task_status(task_id, TaskStatus.RUNNING, progress=60)
        
        clear_success = await jellyfin_playlists.clear_playlist(jellyfin_playlist_id)
        if not clear_success:
            logger.warning(f"清空播放清單失敗，但繼續執行添加操作: {jellyfin_playlist_id}")
        
        # 更新進度: 添加歌曲到播放清單
        self.update_task_status(task_id, TaskStatus.RUNNING, progress=80)
        
        success = await jellyfin_playlists.add_songs_to_playlist(jellyfin_playlist_id, jellyfin_song_ids)
        
        if not success:
            raise ValueError(f"無法將歌曲新增到 Jellyfin 播放清單 {jellyfin_playlist_id}")
        
        # 更新進度: 完成
        self.update_task_status(task_id, TaskStatus.RUNNING, progress=95)
        
        return {
            "message": f"成功同步播放清單 '{playlist['name']}' 到 Jellyfin",
            "jellyfin_playlist_id": jellyfin_playlist_id,
            "songs_found": len(filtered_songs),
            "songs_matched": len(jellyfin_song_ids),
            "songs_added": len(jellyfin_song_ids),
            "sort_method": "local_jellyfin_add_time"
        }

# 創建全局任務管理器實例
task_manager = TaskManager()
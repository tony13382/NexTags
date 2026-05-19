from fastapi import APIRouter, HTTPException, Query
from app.dependencies.redis_cache import redis_cache
from app.dependencies.logger import logger
from app.router.config import get_config
import os
import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import List

router = APIRouter(prefix="/cache", tags=["cache"])

def _scan_folder_sync(folder_path: str) -> List[str]:
    """同步掃描單一資料夾中的音訊檔案"""
    audio_extensions = {'.flac', '.mp3', '.wav', '.m4a', '.aac', '.ogg', '.wma'}
    audio_files = []
    
    for root, _, files in os.walk(folder_path):
        for file in files:
            # 排除點開頭的隱藏檔案
            if not file.startswith('.') and any(file.lower().endswith(ext) for ext in audio_extensions):
                audio_files.append(os.path.join(root, file))
    
    return audio_files

async def get_audio_files_in_folder(folder_path: str) -> List[str]:
    """異步遞歸搜尋資料夾中的音訊檔案，排除點開頭的隱藏檔案"""
    loop = asyncio.get_event_loop()
    with ThreadPoolExecutor() as executor:
        audio_files = await loop.run_in_executor(executor, _scan_folder_sync, folder_path)
    return audio_files

async def scan_multiple_folders_concurrent(folder_paths: List[str]) -> List[str]:
    """併發掃描多個資料夾"""
    tasks = []
    for folder_path in folder_paths:
        if os.path.exists(folder_path) and os.path.isdir(folder_path):
            tasks.append(get_audio_files_in_folder(folder_path))
    
    if not tasks:
        return []
    
    results = await asyncio.gather(*tasks)
    all_audio_files = []
    for audio_files in results:
        all_audio_files.extend(audio_files)
    
    return all_audio_files

def _update_cache_rebuild_progress(task_id: str | None, progress: int):
    if not task_id:
        return

    from app.services.task_manager import TaskStatus, task_manager

    task_manager.update_task_status(
        task_id,
        TaskStatus.RUNNING,
        progress=max(0, min(progress, 99))
    )

async def perform_cache_rebuild(task_id: str | None = None):
    """執行快取重建，供背景任務呼叫。"""
    logger.info("開始重建標籤快取")
    _update_cache_rebuild_progress(task_id, 5)

    allow_folders = get_config('allow_folders') or []
    music_base_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), 'Music')
    
    folder_paths = []
    folder_paths_by_name = {}
    for folder_name in allow_folders:
        folder_path = os.path.join(music_base_path, folder_name)
        folder_paths.append(folder_path)
        folder_paths_by_name[folder_name] = folder_path
    
    all_audio_files = []
    total_folders = len(folder_paths)
    for index, folder_path in enumerate(folder_paths, start=1):
        if os.path.exists(folder_path) and os.path.isdir(folder_path):
            all_audio_files.extend(await get_audio_files_in_folder(folder_path))

        scan_progress = 5 + int((index / max(total_folders, 1)) * 35)
        _update_cache_rebuild_progress(task_id, scan_progress)
    
    logger.info(f"找到 {len(all_audio_files)} 個音訊檔案，開始重建快取")

    if redis_cache is None:
        raise HTTPException(status_code=503, detail="Redis 快取服務無法使用")

    _update_cache_rebuild_progress(task_id, 45)

    def update_cache_progress(processed: int, total: int):
        cache_progress = 45 + int((processed / max(total, 1)) * 50)
        _update_cache_rebuild_progress(task_id, cache_progress)

    loop = asyncio.get_running_loop()
    result = await loop.run_in_executor(
        None,
        lambda: redis_cache.rebuild_cache(all_audio_files, update_cache_progress, folder_paths_by_name)
    )
    
    logger.info(f"快取重建完成，共處理 {result['total_files']} 個檔案")
    
    return {
        "success": True,
        "message": "快取重建完成",
        "total_files": result['total_files'],
        "removed_files_count": len(result['removed_files']),
        "removed_files": result['removed_files'][:10] if len(result['removed_files']) > 10 else result['removed_files'],
        "allow_folders": allow_folders
    }

@router.post("/rebuild")
async def rebuild_cache():
    """啟動背景標籤快取重建任務"""
    try:
        if redis_cache is None:
            raise HTTPException(status_code=503, detail="Redis 快取服務無法使用")

        from app.services.task_manager import task_manager

        active_task = next((
            task for task in task_manager.get_all_tasks(limit=50)
            if task.get("task_type") == "cache_rebuild"
            and task.get("status") in ["pending", "running"]
        ), None)

        if active_task:
            return {
                "success": True,
                "message": "快取重建已在背景執行",
                "task_id": active_task["task_id"],
                "status": active_task["status"]
            }

        task_id = task_manager.create_task("cache_rebuild", {})

        return {
            "success": True,
            "message": "快取重建已啟動，請稍候完成",
            "task_id": task_id,
            "status": "pending"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"啟動快取重建任務時發生錯誤: {str(e)}")
        raise HTTPException(status_code=500, detail=f"啟動快取重建任務時發生錯誤: {str(e)}")

@router.delete("/clear")
async def clear_cache():
    """清空標籤快取"""
    try:
        if redis_cache is None:
            raise HTTPException(status_code=503, detail="Redis 快取服務無法使用")

        redis_cache.clear_cache()
        return {
            "success": True,
            "message": "快取已清空"
        }
    except Exception as e:
        logger.error(f"清空快取時發生錯誤: {str(e)}")
        raise HTTPException(status_code=500, detail=f"清空快取時發生錯誤: {str(e)}")

@router.get("/status")
async def get_cache_status():
    """獲取快取狀態"""
    try:
        if redis_cache is None:
            return {
                "cache_available": False,
                "error": "Redis 快取服務無法使用"
            }

        cache_info = redis_cache.get_cache_info()

        return {
            "cache_available": True,
            "cache_type": "Redis",
            "cached_files_count": cache_info['cached_files_count'],
            "memory_used_bytes": cache_info['memory_used_bytes'],
            "memory_used_human": cache_info['memory_used_human'],
            "redis_version": cache_info['redis_version']
        }
    except Exception as e:
        logger.error(f"獲取快取狀態時發生錯誤: {str(e)}")
        raise HTTPException(status_code=500, detail=f"獲取快取狀態時發生錯誤: {str(e)}")

@router.get("/statistics")
async def get_cache_statistics(
    include_actual: bool = Query(False, description="是否同步掃描實際音樂檔案數量")
):
    """獲取快取統計資訊。預設避免同步掃描遠端掛載，避免請求逾時。"""
    try:
        if redis_cache is None:
            raise HTTPException(status_code=503, detail="Redis 快取服務無法使用")

        # 從資料庫載入設定
        allow_folders = get_config('allow_folders') or []

        music_base_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), 'Music')

        folder_paths = {}
        for folder_name in allow_folders:
            folder_path = os.path.join(music_base_path, folder_name)
            folder_paths[folder_name] = folder_path

        # 獲取快取資訊
        cache_info = redis_cache.get_cache_info()

        # 獲取各資料夾的快取統計
        cached_files_stats = redis_cache.get_cache_stats_by_folders(folder_paths)

        # 同步掃描 rclone/Google Drive 掛載很容易超過 nginx/Cloudflare timeout。
        # 預設用快取數量作為統計頁的快速估算；需要即時檔案數時才顯式 include_actual=true。
        actual_files_source = "cache"
        actual_files_stats = dict(cached_files_stats)
        total_actual_files = sum(actual_files_stats.values())

        if include_actual:
            actual_files_source = "filesystem"
            actual_files_stats = {}
            total_actual_files = 0
            for folder_name, folder_path in folder_paths.items():
                if os.path.exists(folder_path) and os.path.isdir(folder_path):
                    audio_files = await get_audio_files_in_folder(folder_path)
                    count = len(audio_files)
                    actual_files_stats[folder_name] = count
                    total_actual_files += count
                else:
                    actual_files_stats[folder_name] = 0

        return {
            "actual_files": {
                "total": total_actual_files,
                "by_folder": actual_files_stats,
                "source": actual_files_source
            },
            "cached_files": {
                "total": cache_info['cached_files_count'],
                "by_folder": cached_files_stats
            },
            "cache_info": {
                "cache_type": "Redis",
                "memory_used_bytes": cache_info['memory_used_bytes'],
                "memory_used_human": cache_info['memory_used_human'],
                "redis_version": cache_info['redis_version']
            },
            "folders": allow_folders
        }

    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="config.yaml 檔案不存在")
    except Exception as e:
        logger.error(f"獲取快取統計時發生錯誤: {str(e)}")
        raise HTTPException(status_code=500, detail=f"獲取快取統計時發生錯誤: {str(e)}")

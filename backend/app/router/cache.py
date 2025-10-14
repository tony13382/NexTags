from fastapi import APIRouter, HTTPException
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

@router.post("/rebuild")
async def rebuild_cache():
    """重建標籤快取"""
    try:
        logger.info("開始重建標籤快取")

        # 從資料庫載入設定
        allow_folders = get_config('allow_folders') or []
        
        music_base_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), 'Music')
        
        # 準備所有要掃描的資料夾路徑
        folder_paths = []
        for folder_name in allow_folders:
            folder_path = os.path.join(music_base_path, folder_name)
            folder_paths.append(folder_path)
        
        # 併發掃描所有資料夾
        all_audio_files = await scan_multiple_folders_concurrent(folder_paths)
        
        logger.info(f"找到 {len(all_audio_files)} 個音訊檔案，開始重建快取")

        # 檢查 Redis 是否可用
        if redis_cache is None:
            raise HTTPException(status_code=503, detail="Redis 快取服務無法使用")

        # 重建快取
        result = redis_cache.rebuild_cache(all_audio_files)
        
        logger.info(f"快取重建完成，共處理 {result['total_files']} 個檔案")
        
        return {
            "success": True,
            "message": "快取重建完成",
            "total_files": result['total_files'],
            "removed_files_count": len(result['removed_files']),
            "removed_files": result['removed_files'][:10] if len(result['removed_files']) > 10 else result['removed_files'],  # 只顯示前10個被移除的檔案
            "allow_folders": allow_folders
        }
        
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="config.yaml 檔案不存在")
    except Exception as e:
        logger.error(f"重建快取時發生錯誤: {str(e)}")
        raise HTTPException(status_code=500, detail=f"重建快取時發生錯誤: {str(e)}")

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
async def get_cache_statistics():
    """獲取快取統計資訊，包含實際檔案和快取數據的詳細分析"""
    try:
        if redis_cache is None:
            raise HTTPException(status_code=503, detail="Redis 快取服務無法使用")

        # 從資料庫載入設定
        allow_folders = get_config('allow_folders') or []

        music_base_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), 'Music')

        # 獲取實際檔案統計
        actual_files_stats = {}
        total_actual_files = 0
        folder_paths = {}

        for folder_name in allow_folders:
            folder_path = os.path.join(music_base_path, folder_name)
            folder_paths[folder_name] = folder_path
            if os.path.exists(folder_path) and os.path.isdir(folder_path):
                audio_files = await get_audio_files_in_folder(folder_path)
                count = len(audio_files)
                actual_files_stats[folder_name] = count
                total_actual_files += count
            else:
                actual_files_stats[folder_name] = 0

        # 獲取快取資訊
        cache_info = redis_cache.get_cache_info()

        # 獲取各資料夾的快取統計
        cached_files_stats = redis_cache.get_cache_stats_by_folders(folder_paths)

        return {
            "actual_files": {
                "total": total_actual_files,
                "by_folder": actual_files_stats
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
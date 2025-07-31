from fastapi import APIRouter, HTTPException
from app.dependencies.tags_cache import tags_cache
from app.dependencies.logger import logger
import os
import yaml
import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import List

router = APIRouter(prefix="/cache", tags=["cache"])

def load_config():
    """載入 config.yaml 設定檔"""
    config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'config.yaml')
    with open(config_path, 'r', encoding='utf-8') as file:
        return yaml.safe_load(file)

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
        
        # 載入設定檔
        config = load_config()
        allow_folders = config.get('allow_folders', [])
        
        music_base_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), 'Music')
        
        # 準備所有要掃描的資料夾路徑
        folder_paths = []
        for folder_name in allow_folders:
            folder_path = os.path.join(music_base_path, folder_name)
            folder_paths.append(folder_path)
        
        # 併發掃描所有資料夾
        all_audio_files = await scan_multiple_folders_concurrent(folder_paths)
        
        logger.info(f"找到 {len(all_audio_files)} 個音訊檔案，開始重建快取")
        
        # 重建快取
        result = tags_cache.rebuild_cache(all_audio_files)
        
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
        tags_cache.clear_cache()
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
        cache_file_exists = os.path.exists(tags_cache.cache_file_path)
        cache_size = len(tags_cache._cache)
        
        cache_file_size = 0
        if cache_file_exists:
            try:
                cache_file_size = os.path.getsize(tags_cache.cache_file_path)
            except:
                pass
        
        return {
            "cache_file_exists": cache_file_exists,
            "cache_file_path": tags_cache.cache_file_path,
            "cached_files_count": cache_size,
            "cache_file_size_bytes": cache_file_size
        }
    except Exception as e:
        logger.error(f"獲取快取狀態時發生錯誤: {str(e)}")
        raise HTTPException(status_code=500, detail=f"獲取快取狀態時發生錯誤: {str(e)}")
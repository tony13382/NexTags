import json
import os
from typing import Dict, Optional, Any
from app.dependencies.logger import logger
from app.dependencies.mp3tag_reader import read_audio_tags


class TagsCache:
    def __init__(self):
        self.cache_file_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), 
            'data', 
            'tags_cache.json'
        )
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._load_cache()
    
    def _load_cache(self):
        """從檔案載入快取"""
        try:
            if os.path.exists(self.cache_file_path):
                with open(self.cache_file_path, 'r', encoding='utf-8') as f:
                    self._cache = json.load(f)
                logger.info(f"成功載入標籤快取，包含 {len(self._cache)} 個檔案")
            else:
                self._cache = {}
                logger.info("標籤快取檔案不存在，初始化空快取")
        except Exception as e:
            logger.error(f"載入標籤快取時發生錯誤: {str(e)}")
            self._cache = {}
    
    def _save_cache(self):
        """將快取儲存到檔案"""
        try:
            # 確保目錄存在
            os.makedirs(os.path.dirname(self.cache_file_path), exist_ok=True)
            
            with open(self.cache_file_path, 'w', encoding='utf-8') as f:
                json.dump(self._cache, f, ensure_ascii=False, indent=2)
            logger.info(f"成功儲存標籤快取，包含 {len(self._cache)} 個檔案")
        except Exception as e:
            logger.error(f"儲存標籤快取時發生錯誤: {str(e)}")
    
    def get_tags(self, file_path: str) -> Optional[Dict[str, Any]]:
        """從快取獲取標籤"""
        if file_path in self._cache:
            cached_data = self._cache[file_path]
            
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
        
        return None
    
    def set_tags(self, file_path: str, tags: Dict[str, Any]):
        """將標籤加入快取"""
        try:
            modification_time = os.path.getmtime(file_path) if os.path.exists(file_path) else 0
            
            self._cache[file_path] = {
                'tags': tags,
                'modification_time': modification_time
            }
            self._save_cache()
        except Exception as e:
            logger.error(f"快取標籤時發生錯誤 {file_path}: {str(e)}")
    
    def remove_tags(self, file_path: str):
        """從快取中移除指定檔案的標籤"""
        if file_path in self._cache:
            del self._cache[file_path]
            self._save_cache()
            logger.info(f"已從快取中移除: {file_path}")
    
    def rebuild_cache(self, file_paths: list[str]):
        """重建快取"""
        logger.info(f"開始重建標籤快取，包含 {len(file_paths)} 個檔案")
        
        new_cache = {}
        removed_files = []
        
        # 處理新的檔案列表
        for file_path in file_paths:
            if os.path.exists(file_path):
                try:
                    tags = read_audio_tags(file_path)
                    modification_time = os.path.getmtime(file_path)
                    
                    new_cache[file_path] = {
                        'tags': tags,
                        'modification_time': modification_time
                    }
                except Exception as e:
                    logger.error(f"讀取檔案標籤時發生錯誤 {file_path}: {str(e)}")
            else:
                removed_files.append(file_path)
        
        # 檢查原有快取中是否有不存在的檔案
        for cached_file_path in list(self._cache.keys()):
            if cached_file_path not in file_paths:
                if not os.path.exists(cached_file_path):
                    removed_files.append(cached_file_path)
                else:
                    # 檔案存在但不在新列表中，保留在快取中
                    new_cache[cached_file_path] = self._cache[cached_file_path]
        
        self._cache = new_cache
        self._save_cache()
        
        logger.info(f"快取重建完成，包含 {len(self._cache)} 個檔案")
        if removed_files:
            logger.info(f"移除了 {len(removed_files)} 個不存在的檔案")
        
        return {
            'total_files': len(self._cache),
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
        self._cache = {}
        self._save_cache()
        logger.info("已清空標籤快取")


# 建立全域快取實例
tags_cache = TagsCache()
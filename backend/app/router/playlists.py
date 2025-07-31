import json
import os
import glob
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
from fastapi import APIRouter, HTTPException, Path as FastAPIPath
from app.schemas.playlists import (
    SmartPlaylist,
    SmartPlaylistCreate,
    SmartPlaylistUpdate,
    SmartPlaylistResponse,
    PlaylistSongsResponse,
    ErrorResponse
)
from app.dependencies.logger import logger
from app.dependencies.mp3tag_reader import read_audio_tags
from app.dependencies.tags_cache import tags_cache
from app.dependencies.jellyfin_connetor import playlists as jellyfin_playlists
from app.dependencies.jellyfin_connetor import songs as jellyfin_songs
import yaml

router = APIRouter(prefix="/playlists", tags=["playlists"])

# 播放清單檔案路徑
SMART_PLAYLIST_FILE = "app/data/smart_playlist.json"
SMART_PLAYLIST_EXAMPLE_FILE = "app/data/smart_playlist.example.json"
CONFIG_FILE = "config.yaml"

# 支援的音訊檔案格式
SUPPORTED_AUDIO_EXTENSIONS = ['.mp3', '.flac', '.m4a', '.ogg', '.wav']

def load_config() -> Dict[str, Any]:
    """載入配置檔案"""
    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as file:
            return yaml.safe_load(file)
    except Exception as e:
        logger.error(f"載入配置檔案失敗: {str(e)}")
        return {
            "supported_tags": [],
            "supported_languages": {},
            "allow_folders": []
        }

def ensure_playlist_file_exists():
    """確保播放清單檔案存在，如果不存在則創建"""
    if not os.path.exists(SMART_PLAYLIST_FILE):
        try:
            # 確保目錄存在
            os.makedirs(os.path.dirname(SMART_PLAYLIST_FILE), exist_ok=True)
            
            # 嘗試從範例檔案複製
            if os.path.exists(SMART_PLAYLIST_EXAMPLE_FILE):
                with open(SMART_PLAYLIST_EXAMPLE_FILE, 'r', encoding='utf-8') as example_file:
                    example_data = json.load(example_file)
                    
                with open(SMART_PLAYLIST_FILE, 'w', encoding='utf-8') as playlist_file:
                    json.dump(example_data, playlist_file, ensure_ascii=False, indent=2)
                    
                logger.info(f"從範例檔案建立播放清單檔案: {SMART_PLAYLIST_FILE}")
            else:
                # 創建空的播放清單檔案
                with open(SMART_PLAYLIST_FILE, 'w', encoding='utf-8') as playlist_file:
                    json.dump([], playlist_file, ensure_ascii=False, indent=2)
                    
                logger.info(f"建立空的播放清單檔案: {SMART_PLAYLIST_FILE}")
                
        except Exception as e:
            logger.error(f"建立播放清單檔案失敗: {str(e)}")
            raise HTTPException(status_code=500, detail=f"無法建立播放清單檔案: {str(e)}")

def load_playlists() -> List[Dict[str, Any]]:
    """載入播放清單"""
    ensure_playlist_file_exists()
    
    try:
        with open(SMART_PLAYLIST_FILE, 'r', encoding='utf-8') as file:
            playlists = json.load(file)
            return playlists if isinstance(playlists, list) else []
    except Exception as e:
        logger.error(f"載入播放清單失敗: {str(e)}")
        return []

def save_playlists(playlists: List[Dict[str, Any]]):
    """儲存播放清單"""
    try:
        with open(SMART_PLAYLIST_FILE, 'w', encoding='utf-8') as file:
            json.dump(playlists, file, ensure_ascii=False, indent=2)
        logger.info(f"成功儲存 {len(playlists)} 個播放清單")
    except Exception as e:
        logger.error(f"儲存播放清單失敗: {str(e)}")
        raise HTTPException(status_code=500, detail=f"無法儲存播放清單: {str(e)}")

def find_audio_files(base_folder: str) -> List[str]:
    """搜尋指定資料夾中的音訊檔案"""
    audio_files = []
    
    # 自動在 base_folder 前面加上 /Music/ 前綴（Docker 容器中的絕對路徑）
    full_path = os.path.join("/Music", base_folder)
    
    if not os.path.exists(full_path):
        logger.warning(f"指定的基礎資料夾不存在: {full_path}")
        return audio_files
    
    try:
        for ext in SUPPORTED_AUDIO_EXTENSIONS:
            pattern = os.path.join(full_path, "**", f"*{ext}")
            files = glob.glob(pattern, recursive=True)
            audio_files.extend(files)
        
        # 去重並排序
        audio_files = list(set(audio_files))
        logger.info(f"在資料夾 {full_path} 中找到 {len(audio_files)} 個音訊檔案")
        
    except Exception as e:
        logger.error(f"搜尋音訊檔案失敗: {str(e)}")
    
    return audio_files

def filter_songs_by_playlist(playlist: Dict[str, Any], audio_files: List[str]) -> List[str]:
    """根據播放清單條件篩選歌曲"""
    filtered_songs = []
    
    for file_path in audio_files:
        try:
            # 使用快取讀取檔案標籤
            tags = tags_cache.get_cached_tags_with_fallback(file_path)
            
            # 檢查語言過濾條件
            if playlist.get('filter_language'):
                file_language = tags.get('language', '').lower()
                if file_language != playlist['filter_language'].lower():
                    continue
            
            # 檢查標籤過濾條件
            if playlist.get('filter_tags'):
                file_genre = tags.get('genre', [])
                if isinstance(file_genre, str):
                    file_genre = [file_genre]
                
                # 檢查是否包含任一指定標籤
                has_required_tag = any(
                    tag in file_genre for tag in playlist['filter_tags']
                )
                if not has_required_tag:
                    continue
            
            # 檢查我的最愛過濾條件
            if playlist.get('filter_favorites') is not None:
                file_favorite = tags.get('favorite', '').strip().lower()
                # 將標籤值轉換為布林值，null 或空值視為 False
                is_favorite = file_favorite in ['true', '1', 'yes']
                
                # 如果播放清單要求只包含我的最愛，但歌曲不是我的最愛，則跳過
                if playlist['filter_favorites'] and not is_favorite:
                    continue
                # 如果播放清單要求排除我的最愛，但歌曲是我的最愛，則跳過
                elif not playlist['filter_favorites'] and is_favorite:
                    continue
            
            filtered_songs.append(file_path)
            
        except Exception as e:
            logger.warning(f"處理檔案 {file_path} 時發生錯誤: {str(e)}")
            continue
    
    return filtered_songs

def sort_songs_by_creation_time(songs: List[str]) -> List[str]:
    """根據檔案建立時間排序（新→舊）"""
    try:
        songs_with_time = []
        logger.info(f"開始排序 {len(songs)} 首歌曲")
        
        for i, song in enumerate(songs):
            try:
                # 獲取檔案時間戳
                stat = os.stat(song)
                # Linux/Unix: st_ctime 是狀態改變時間，st_mtime 是修改時間
                # Windows: st_ctime 是建立時間
                # 為了跨平台相容性，我們同時記錄兩個時間戳
                creation_time = stat.st_ctime  # 可能是建立時間（Windows）或狀態改變時間（Linux）
                modification_time = stat.st_mtime  # 修改時間
                
                # 使用修改時間作為排序基準，因為它在跨平台上更一致
                sort_time = modification_time
                
                songs_with_time.append((song, sort_time))
                
                # 詳細日誌前5個檔案的時間戳
                if i < 5:
                    from datetime import datetime
                    ctime_str = datetime.fromtimestamp(creation_time).strftime('%Y-%m-%d %H:%M:%S')
                    mtime_str = datetime.fromtimestamp(modification_time).strftime('%Y-%m-%d %H:%M:%S')
                    logger.info(f"檔案 {i+1}: {os.path.basename(song)}")
                    logger.info(f"  st_ctime: {ctime_str}")
                    logger.info(f"  st_mtime: {mtime_str}")
                    logger.info(f"  使用時間: {mtime_str}")
                    
            except Exception as e:
                logger.warning(f"無法獲取檔案 {song} 的時間戳: {str(e)}")
                # 如果無法獲取時間，使用0（排到最後）
                songs_with_time.append((song, 0))
        
        # 按排序時間排序（新→舊）
        songs_with_time.sort(key=lambda x: x[1], reverse=True)
        sorted_songs = [song for song, _ in songs_with_time]
        
        # 日誌排序結果
        logger.info(f"排序完成，前3首歌曲:")
        for i, (song, sort_time) in enumerate(songs_with_time[:3]):
            from datetime import datetime
            time_str = datetime.fromtimestamp(sort_time).strftime('%Y-%m-%d %H:%M:%S')
            logger.info(f"  {i+1}. {os.path.basename(song)} ({time_str})")
        
        return sorted_songs
        
    except Exception as e:
        logger.error(f"排序歌曲失敗: {str(e)}")
        return songs

def sort_songs_by_jellyfin_add_time(songs: List[str]) -> List[str]:
    """根據 jellyfin_add_time 標籤排序（新→舊）
    
    優先使用本地 jellyfin_add_time 標籤，若不存在則使用檔案修改時間
    
    Args:
        songs: 歌曲檔案路徑列表
        
    Returns:
        排序後的歌曲檔案路徑列表
    """
    try:
        songs_with_time = []
        logger.info(f"開始使用 jellyfin_add_time 標籤排序 {len(songs)} 首歌曲")
        
        for i, song in enumerate(songs):
            try:
                # 使用快取讀取檔案標籤
                tags = tags_cache.get_cached_tags_with_fallback(song)
                jellyfin_add_time = tags.get('jellyfin_add_time', '').strip()
                
                if jellyfin_add_time:
                    # 解析 jellyfin_add_time 標籤中的時間
                    try:
                        # Jellyfin 時間格式通常是 ISO 格式，例如 "2024-01-15T10:30:00.0000000Z"
                        if 'T' in jellyfin_add_time:
                            # 移除多餘的零和時區標記進行解析
                            clean_date = jellyfin_add_time.split('.')[0] if '.' in jellyfin_add_time else jellyfin_add_time.rstrip('Z')
                            sort_time = datetime.fromisoformat(clean_date).timestamp()
                        else:
                            # 如果不是標準 ISO 格式，嘗試其他格式
                            sort_time = datetime.fromisoformat(jellyfin_add_time).timestamp()
                        
                        songs_with_time.append((song, sort_time, 'jellyfin_add_time'))
                        
                        # 詳細日誌前5個檔案的標籤時間
                        if i < 5:
                            time_str = datetime.fromtimestamp(sort_time).strftime('%Y-%m-%d %H:%M:%S')
                            logger.info(f"檔案 {i+1}: {os.path.basename(song)}")
                            logger.info(f"  jellyfin_add_time: {jellyfin_add_time}")
                            logger.info(f"  解析後時間: {time_str}")
                        
                    except Exception as parse_error:
                        logger.warning(f"無法解析 jellyfin_add_time '{jellyfin_add_time}' for {song}: {str(parse_error)}")
                        # 回退到檔案修改時間
                        stat = os.stat(song)
                        sort_time = stat.st_mtime
                        songs_with_time.append((song, sort_time, 'file_mtime'))
                else:
                    # 如果沒有 jellyfin_add_time 標籤，使用檔案修改時間
                    stat = os.stat(song)
                    sort_time = stat.st_mtime
                    songs_with_time.append((song, sort_time, 'file_mtime'))
                    
                    if i < 5:
                        time_str = datetime.fromtimestamp(sort_time).strftime('%Y-%m-%d %H:%M:%S')
                        logger.info(f"檔案 {i+1}: {os.path.basename(song)}")
                        logger.info(f"  使用檔案修改時間: {time_str}")
                    
            except Exception as e:
                logger.warning(f"無法獲取檔案 {song} 的時間資訊: {str(e)}")
                # 如果無法獲取時間，使用0（排到最後）
                songs_with_time.append((song, 0, 'error'))
        
        # 按排序時間排序（新→舊）
        songs_with_time.sort(key=lambda x: x[1], reverse=True)
        sorted_songs = [song for song, _, _ in songs_with_time]
        
        # 統計排序方式
        tag_count = sum(1 for _, _, source in songs_with_time if source == 'jellyfin_add_time')
        file_count = sum(1 for _, _, source in songs_with_time if source == 'file_mtime')
        error_count = sum(1 for _, _, source in songs_with_time if source == 'error')
        
        logger.info(f"排序完成：{tag_count} 個使用 jellyfin_add_time 標籤，{file_count} 個使用檔案時間，{error_count} 個錯誤")
        
        # 日誌排序結果
        logger.info(f"排序結果前3首歌曲:")
        for i, (song, sort_time, source) in enumerate(songs_with_time[:3]):
            time_str = datetime.fromtimestamp(sort_time).strftime('%Y-%m-%d %H:%M:%S') if sort_time > 0 else 'Unknown'
            logger.info(f"  {i+1}. {os.path.basename(song)} ({time_str}, 來源: {source})")
        
        return sorted_songs
        
    except Exception as e:
        logger.error(f"使用 jellyfin_add_time 標籤排序歌曲失敗: {str(e)}")
        # 回退到原始的檔案時間排序
        logger.info("回退到檔案修改時間排序")
        return sort_songs_by_creation_time(songs)

def get_language_display_name(language_code: str, config: Dict[str, Any]) -> str:
    """根據語言代碼獲取顯示名稱"""
    if not language_code:
        return "不篩選"
    
    supported_languages = config.get("supported_languages", {})
    return supported_languages.get(language_code, language_code)

def get_tags_display_names(tags: List[str], config: Dict[str, Any]) -> List[str]:
    """獲取標籤的顯示名稱（目前標籤直接使用中文名稱）"""
    return tags if tags else ["不篩選"]

def get_favorites_display_name(favorites: Optional[bool]) -> str:
    """獲取我的最愛過濾條件的顯示名稱"""
    if favorites is None:
        return "不篩選"
    return "只包含我的最愛" if favorites else "排除我的最愛"

def enrich_playlist_data(playlist_data: Dict[str, Any], config: Dict[str, Any]) -> Dict[str, Any]:
    """豐富播放清單資料，加入顯示名稱"""
    enriched_data = playlist_data.copy()
    
    # 加入語言顯示名稱
    enriched_data["filter_language_display"] = get_language_display_name(
        playlist_data.get("filter_language"), config
    )
    
    # 加入標籤顯示名稱
    enriched_data["filter_tags_display"] = get_tags_display_names(
        playlist_data.get("filter_tags", []), config
    )
    
    # 加入我的最愛顯示名稱
    enriched_data["filter_favorites_display"] = get_favorites_display_name(
        playlist_data.get("filter_favorites")
    )
    
    return enriched_data

@router.get("/", response_model=SmartPlaylistResponse)
async def get_playlists():
    """取得所有智慧播放清單"""
    try:
        logger.info("取得所有播放清單")
        
        # 載入配置
        config = load_config()
        
        playlists_data = load_playlists()
        
        # 豐富播放清單資料
        enriched_playlists_data = [
            enrich_playlist_data(playlist, config) for playlist in playlists_data
        ]
        
        playlists = [SmartPlaylist(**playlist) for playlist in enriched_playlists_data]
        
        return SmartPlaylistResponse(
            success=True,
            message="成功取得播放清單",
            data=playlists,
            total_count=len(playlists)
        )
        
    except Exception as e:
        error_msg = f"取得播放清單失敗: {str(e)}"
        logger.error(error_msg)
        raise HTTPException(status_code=500, detail=error_msg)

@router.post("/", response_model=SmartPlaylistResponse)
async def create_playlist(playlist: SmartPlaylistCreate):
    """建立新的智慧播放清單"""
    try:
        logger.info(f"建立新播放清單: {playlist.name}")
        
        # 載入現有播放清單
        playlists_data = load_playlists()
        
        # 檢查是否有重複名稱
        existing_names = [p.get('name', '') for p in playlists_data]
        if playlist.name in existing_names:
            raise HTTPException(
                status_code=400, 
                detail=f"播放清單名稱 '{playlist.name}' 已存在"
            )
        
        # 新增播放清單
        new_playlist = playlist.model_dump()
        playlists_data.append(new_playlist)
        
        # 儲存播放清單
        save_playlists(playlists_data)
        
        created_playlist = SmartPlaylist(**new_playlist)
        
        return SmartPlaylistResponse(
            success=True,
            message=f"成功建立播放清單 '{playlist.name}'",
            data=created_playlist
        )
        
    except HTTPException:
        raise
    except Exception as e:
        error_msg = f"建立播放清單失敗: {str(e)}"
        logger.error(error_msg)
        raise HTTPException(status_code=500, detail=error_msg)

@router.put("/{index}", response_model=SmartPlaylistResponse)
async def update_playlist(
    index: int = FastAPIPath(..., ge=0, description="播放清單索引"),
    playlist: SmartPlaylistUpdate = ...
):
    """更新指定的智慧播放清單"""
    try:
        logger.info(f"更新播放清單索引 {index}")
        
        # 載入現有播放清單
        playlists_data = load_playlists()
        
        # 檢查索引是否有效
        if index >= len(playlists_data):
            raise HTTPException(
                status_code=404, 
                detail=f"播放清單索引 {index} 不存在"
            )
        
        # 更新播放清單
        current_playlist = playlists_data[index]
        update_data = playlist.model_dump(exclude_unset=True)
        
        # 檢查名稱是否重複（除了自己）
        if 'name' in update_data:
            existing_names = [
                p.get('name', '') for i, p in enumerate(playlists_data) 
                if i != index
            ]
            if update_data['name'] in existing_names:
                raise HTTPException(
                    status_code=400, 
                    detail=f"播放清單名稱 '{update_data['name']}' 已存在"
                )
        
        # 合併更新資料
        current_playlist.update(update_data)
        playlists_data[index] = current_playlist
        
        # 儲存播放清單
        save_playlists(playlists_data)
        
        updated_playlist = SmartPlaylist(**current_playlist)
        
        return SmartPlaylistResponse(
            success=True,
            message=f"成功更新播放清單 '{updated_playlist.name}'",
            data=updated_playlist
        )
        
    except HTTPException:
        raise
    except Exception as e:
        error_msg = f"更新播放清單失敗: {str(e)}"
        logger.error(error_msg)
        raise HTTPException(status_code=500, detail=error_msg)

@router.get("/{index}/songs")
async def get_playlist_songs(
    index: int = FastAPIPath(..., ge=0, description="播放清單索引")
):
    """取得指定播放清單的歌曲清單，包含排序日期資訊"""
    try:
        logger.info(f"取得播放清單 {index} 的歌曲清單（包含排序日期）")
        
        # 載入播放清單
        playlists_data = load_playlists()
        
        # 檢查索引是否有效
        if index >= len(playlists_data):
            raise HTTPException(
                status_code=404,
                detail=f"播放清單索引 {index} 不存在"
            )
        
        playlist = playlists_data[index]
        
        # 搜尋基礎資料夾中的音訊檔案
        audio_files = find_audio_files(playlist['base_folder'])
        
        # 根據播放清單條件篩選歌曲
        filtered_songs = filter_songs_by_playlist(playlist, audio_files)
        
        logger.info(f"篩選後找到 {len(filtered_songs)} 首歌曲，開始使用本地標籤排序")
        
        if not filtered_songs:
            return {
                "success": True,
                "message": f"播放清單 '{playlist['name']}' 沒有符合條件的歌曲",
                "playlist_name": playlist['name'],
                "playlist_index": index,
                "filter_summary": {
                    "base_folder": playlist['base_folder'],
                    "filter_tags": playlist.get('filter_tags', []),
                    "filter_language": playlist.get('filter_language'),
                    "filter_favorites": playlist.get('filter_favorites'),
                    "total_files_found": len(audio_files),
                    "files_after_filtering": 0
                },
                "songs": [],
                "total_count": 0
            }
        
        # 使用本地 jellyfin_add_time 標籤排序（新→舊）
        sorted_songs = sort_songs_by_jellyfin_add_time(filtered_songs)
        
        # 建立回傳的歌曲列表（包含排序日期資訊）
        songs_with_dates = []
        for file_path in sorted_songs:
            try:
                # 使用快取讀取檔案標籤
                tags = tags_cache.get_cached_tags_with_fallback(file_path)
                jellyfin_add_time = tags.get('jellyfin_add_time', '').strip()
                jellyfin_id = tags.get('jfid', '').strip()
                song_name = tags.get('title', '') or os.path.basename(file_path)
                
                # 格式化日期顯示
                formatted_date = ""
                if jellyfin_add_time:
                    try:
                        if 'T' in jellyfin_add_time:
                            clean_date = jellyfin_add_time.split('.')[0] if '.' in jellyfin_add_time else jellyfin_add_time.rstrip('Z')
                            dt = datetime.fromisoformat(clean_date)
                            formatted_date = dt.strftime('%Y-%m-%d %H:%M:%S')
                    except Exception as e:
                        logger.warning(f"無法格式化日期 {jellyfin_add_time}: {str(e)}")
                        formatted_date = jellyfin_add_time
                
                # 如果沒有 jellyfin_add_time，使用檔案修改時間
                if not formatted_date:
                    try:
                        stat = os.stat(file_path)
                        dt = datetime.fromtimestamp(stat.st_mtime)
                        formatted_date = dt.strftime('%Y-%m-%d %H:%M:%S')
                        jellyfin_add_time = dt.isoformat()
                    except Exception:
                        formatted_date = "無日期資訊"
                        jellyfin_add_time = ""
                
                songs_with_dates.append({
                    "file_path": file_path,
                    "jellyfin_date_created": jellyfin_add_time,  # 使用本地標籤或檔案時間
                    "formatted_date": formatted_date,
                    "jellyfin_id": jellyfin_id,
                    "song_name": song_name
                })
                
            except Exception as e:
                logger.warning(f"處理檔案 {file_path} 時發生錯誤: {str(e)}")
                songs_with_dates.append({
                    "file_path": file_path,
                    "jellyfin_date_created": "",
                    "formatted_date": "無日期資訊",
                    "jellyfin_id": "",
                    "song_name": os.path.basename(file_path)
                })
        
        # 建立過濾條件摘要
        filter_summary = {
            "base_folder": playlist['base_folder'],
            "filter_tags": playlist.get('filter_tags', []),
            "filter_language": playlist.get('filter_language'),
            "filter_favorites": playlist.get('filter_favorites'),
            "total_files_found": len(audio_files),
            "files_after_filtering": len(songs_with_dates),
            "sort_method": "local_jellyfin_add_time"
        }
        
        return {
            "success": True,
            "message": f"成功取得播放清單 '{playlist['name']}' 的歌曲清單（按本地 jellyfin_add_time 標籤排序）",
            "playlist_name": playlist['name'],
            "playlist_index": index,
            "filter_summary": filter_summary,
            "songs": songs_with_dates,
            "total_count": len(songs_with_dates)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        error_msg = f"取得播放清單歌曲失敗: {str(e)}"
        logger.error(error_msg)
        raise HTTPException(status_code=500, detail=error_msg)

@router.delete("/{index}")
async def delete_playlist(
    index: int = FastAPIPath(..., ge=0, description="播放清單索引")
):
    """刪除指定的智慧播放清單"""
    try:
        logger.info(f"刪除播放清單索引 {index}")
        
        # 載入現有播放清單
        playlists_data = load_playlists()
        
        # 檢查索引是否有效
        if index >= len(playlists_data):
            raise HTTPException(
                status_code=404, 
                detail=f"播放清單索引 {index} 不存在"
            )
        
        # 刪除播放清單
        deleted_playlist = playlists_data.pop(index)
        
        # 儲存播放清單
        save_playlists(playlists_data)
        
        return {
            "success": True,
            "message": f"成功刪除播放清單 '{deleted_playlist.get('name', '未知')}'",
            "deleted_playlist": deleted_playlist
        }
        
    except HTTPException:
        raise
    except Exception as e:
        error_msg = f"刪除播放清單失敗: {str(e)}"
        logger.error(error_msg)
        raise HTTPException(status_code=500, detail=error_msg)


async def find_jellyfin_songs_by_file_paths(file_paths: List[str]) -> List[Dict[str, Any]]:
    """根據本地檔案路徑找到對應的 Jellyfin 歌曲詳細資訊
    
    直接從音訊檔案標籤中讀取 jfid（Jellyfin ID），並獲取 Jellyfin 歌曲詳細資訊
    
    Args:
        file_paths: 本地檔案路徑列表
        
    Returns:
        Jellyfin 歌曲詳細資訊列表（包含 ID 和 DateCreated）
    """
    jellyfin_songs_info = []
    
    for file_path in file_paths:
        try:
            logger.info(f"正在處理檔案: {file_path}")
            
            # 使用快取讀取檔案標籤中的 Jellyfin ID
            tags = tags_cache.get_cached_tags_with_fallback(file_path)
            jellyfin_id = tags.get('jfid', '').strip()
            
            if jellyfin_id:
                # 從 Jellyfin 獲取歌曲詳細資訊
                song_info = await jellyfin_songs.get_song_by_id(jellyfin_id)
                if song_info:
                    jellyfin_songs_info.append({
                        'file_path': file_path,
                        'jellyfin_id': jellyfin_id,
                        'jellyfin_info': song_info
                    })
                    logger.info(f"找到 Jellyfin 歌曲: {file_path} -> {jellyfin_id} (DateCreated: {song_info.get('DateCreated')})")
                else:
                    logger.warning(f"無法從 Jellyfin 獲取歌曲資訊: {jellyfin_id} (檔案: {file_path})")
            else:
                logger.warning(f"檔案沒有 Jellyfin ID: {file_path}")
                
        except Exception as e:
            logger.error(f"處理檔案 {file_path} 時發生錯誤: {str(e)}")
            continue
    
    logger.info(f"總共找到 {len(jellyfin_songs_info)} 個 Jellyfin 歌曲資訊，共處理 {len(file_paths)} 個檔案")
    return jellyfin_songs_info


@router.post("/{index}/sync-to-jellyfin")
async def sync_playlist_to_jellyfin(
    index: int = FastAPIPath(..., ge=0, description="播放清單索引")
):
    """將智慧播放清單同步到 Jellyfin"""
    try:
        logger.info(f"開始同步播放清單 {index} 到 Jellyfin")
        
        # 載入播放清單
        playlists_data = load_playlists()
        
        # 檢查索引是否有效
        if index >= len(playlists_data):
            raise HTTPException(
                status_code=404,
                detail=f"播放清單索引 {index} 不存在"
            )
        
        playlist = playlists_data[index]
        jellyfin_playlist_id = playlist.get("jellyfin_playlist_id")
        
        if not jellyfin_playlist_id:
            raise HTTPException(
                status_code=400,
                detail="此播放清單沒有設定 Jellyfin Playlist ID"
            )
        
        # 取得本地播放清單的歌曲
        audio_files = find_audio_files(playlist['base_folder'])
        filtered_songs = filter_songs_by_playlist(playlist, audio_files)
        
        logger.info(f"篩選後找到 {len(filtered_songs)} 首歌曲")
        
        if not filtered_songs:
            return {
                "success": True,
                "message": f"播放清單 '{playlist['name']}' 沒有符合條件的歌曲",
                "jellyfin_playlist_id": jellyfin_playlist_id,
                "songs_found": 0,
                "songs_added": 0
            }
        
        # 使用本地 jellyfin_add_time 標籤排序（新→舊）
        logger.info(f"使用本地 jellyfin_add_time 標籤排序 {len(filtered_songs)} 首歌曲")
        sorted_songs = sort_songs_by_jellyfin_add_time(filtered_songs)
        
        # 從排序後的歌曲中提取 Jellyfin ID
        jellyfin_song_ids = []
        for file_path in sorted_songs:
            try:
                tags = tags_cache.get_cached_tags_with_fallback(file_path)
                jellyfin_id = tags.get('jfid', '').strip()
                if jellyfin_id:
                    jellyfin_song_ids.append(jellyfin_id)
                else:
                    logger.warning(f"檔案沒有 Jellyfin ID: {file_path}")
            except Exception as e:
                logger.error(f"讀取檔案標籤失敗: {file_path} - {str(e)}")
                continue
        
        if not jellyfin_song_ids:
            return {
                "success": False,
                "message": f"播放清單 '{playlist['name']}' 中沒有找到有效的 Jellyfin ID",
                "jellyfin_playlist_id": jellyfin_playlist_id,
                "songs_found": len(filtered_songs),
                "songs_matched": 0
            }
        
        # 日誌排序結果
        logger.info(f"本地標籤排序結果 (前3首):")
        for i, file_path in enumerate(sorted_songs[:3]):
            try:
                tags = tags_cache.get_cached_tags_with_fallback(file_path)
                jellyfin_add_time = tags.get('jellyfin_add_time', 'Unknown')
                file_name = os.path.basename(file_path)
                logger.info(f"  {i+1}. {file_name} (jellyfin_add_time: {jellyfin_add_time})")
            except Exception:
                file_name = os.path.basename(file_path)
                logger.info(f"  {i+1}. {file_name} (無法讀取標籤)")
        
        # 檢查 Jellyfin 播放清單是否存在
        existing_playlist = await jellyfin_playlists.get_playlist_by_id(jellyfin_playlist_id)
        if not existing_playlist:
            raise HTTPException(
                status_code=404,
                detail=f"Jellyfin 中找不到 ID 為 {jellyfin_playlist_id} 的播放清單"
            )
        
        # 先清空播放清單，再添加新歌曲
        logger.info(f"清空播放清單 {jellyfin_playlist_id} 中的所有項目")
        clear_success = await jellyfin_playlists.clear_playlist(jellyfin_playlist_id)
        
        if not clear_success:
            logger.warning(f"清空播放清單失敗，但繼續執行添加操作: {jellyfin_playlist_id}")
        
        # 新增歌曲到 Jellyfin 播放清單（保持 DateCreated 排序順序）
        logger.info(f"即將添加到 Jellyfin 的歌曲 ID 順序 (前3個):")
        for i, song_id in enumerate(jellyfin_song_ids[:3]):
            logger.info(f"  {i+1}. {song_id}")
        
        success = await jellyfin_playlists.add_songs_to_playlist(jellyfin_playlist_id, jellyfin_song_ids)
        
        if success:
            logger.info(f"成功同步播放清單 '{playlist['name']}' 到 Jellyfin，共 {len(jellyfin_song_ids)} 首歌曲，使用本地 jellyfin_add_time 標籤排序")
            return {
                "success": True,
                "message": f"成功同步播放清單 '{playlist['name']}' 到 Jellyfin (按本地 jellyfin_add_time 標籤排序)",
                "jellyfin_playlist_id": jellyfin_playlist_id,
                "songs_found": len(filtered_songs),
                "songs_matched": len(jellyfin_song_ids),
                "songs_added": len(jellyfin_song_ids),
                "sort_method": "local_jellyfin_add_time"
            }
        else:
            raise HTTPException(
                status_code=500,
                detail=f"無法將歌曲新增到 Jellyfin 播放清單 {jellyfin_playlist_id}"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        error_msg = f"同步播放清單到 Jellyfin 失敗: {str(e)}"
        logger.error(error_msg)
        raise HTTPException(status_code=500, detail=error_msg)
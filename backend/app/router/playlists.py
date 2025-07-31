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
            # 讀取檔案標籤
            tags = read_audio_tags(file_path)
            
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
        for song in songs:
            try:
                # 獲取檔案建立時間
                stat = os.stat(song)
                creation_time = stat.st_ctime
                songs_with_time.append((song, creation_time))
            except Exception as e:
                logger.warning(f"無法獲取檔案 {song} 的建立時間: {str(e)}")
                # 如果無法獲取時間，使用當前時間
                songs_with_time.append((song, 0))
        
        # 按建立時間排序（新→舊）
        songs_with_time.sort(key=lambda x: x[1], reverse=True)
        return [song for song, _ in songs_with_time]
        
    except Exception as e:
        logger.error(f"排序歌曲失敗: {str(e)}")
        return songs

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

@router.get("/{index}/songs", response_model=PlaylistSongsResponse)
async def get_playlist_songs(
    index: int = FastAPIPath(..., ge=0, description="播放清單索引")
):
    """取得指定播放清單的歌曲清單，根據篩選條件並按檔案建立時間排序（新→舊）"""
    try:
        logger.info(f"取得播放清單 {index} 的歌曲清單")
        
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
        
        # 根據檔案建立時間排序（新→舊）
        sorted_songs = sort_songs_by_creation_time(filtered_songs)
        
        # 建立過濾條件摘要
        filter_summary = {
            "base_folder": playlist['base_folder'],
            "filter_tags": playlist.get('filter_tags', []),
            "filter_language": playlist.get('filter_language'),
            "filter_favorites": playlist.get('filter_favorites'),
            "total_files_found": len(audio_files),
            "files_after_filtering": len(sorted_songs)
        }
        
        return PlaylistSongsResponse(
            success=True,
            message=f"成功取得播放清單 '{playlist['name']}' 的歌曲清單",
            playlist_name=playlist['name'],
            playlist_index=index,
            filter_summary=filter_summary,
            songs=sorted_songs,
            total_count=len(sorted_songs)
        )
        
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


async def find_jellyfin_songs_by_file_paths(file_paths: List[str]) -> List[str]:
    """根據本地檔案路徑找到對應的 Jellyfin 歌曲 ID
    
    直接從音訊檔案標籤中讀取 jfid（Jellyfin ID），不需要重新搜尋匹配
    
    Args:
        file_paths: 本地檔案路徑列表
        
    Returns:
        Jellyfin 歌曲 ID 列表
    """
    jellyfin_song_ids = []
    
    for file_path in file_paths:
        try:
            logger.info(f"正在處理檔案: {file_path}")
            
            # 直接從檔案標籤讀取 Jellyfin ID
            tags = read_audio_tags(file_path)
            jellyfin_id = tags.get('jfid', '').strip()
            
            if jellyfin_id:
                jellyfin_song_ids.append(jellyfin_id)
                logger.info(f"找到 Jellyfin ID: {file_path} -> {jellyfin_id}")
            else:
                logger.warning(f"檔案沒有 Jellyfin ID: {file_path}")
                
        except Exception as e:
            logger.error(f"處理檔案 {file_path} 時發生錯誤: {str(e)}")
            continue
    
    logger.info(f"總共找到 {len(jellyfin_song_ids)} 個 Jellyfin ID，共處理 {len(file_paths)} 個檔案")
    return jellyfin_song_ids


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
        sorted_songs = sort_songs_by_creation_time(filtered_songs)
        
        if not sorted_songs:
            return {
                "success": True,
                "message": f"播放清單 '{playlist['name']}' 沒有符合條件的歌曲",
                "jellyfin_playlist_id": jellyfin_playlist_id,
                "songs_found": 0,
                "songs_added": 0
            }
        
        # 將本地檔案路徑轉換為 Jellyfin 歌曲 ID
        logger.info(f"正在轉換 {len(sorted_songs)} 個本地檔案路徑為 Jellyfin 歌曲 ID")
        jellyfin_song_ids = await find_jellyfin_songs_by_file_paths(sorted_songs)
        
        if not jellyfin_song_ids:
            return {
                "success": False,
                "message": f"在 Jellyfin 中找不到播放清單 '{playlist['name']}' 的任何歌曲",
                "jellyfin_playlist_id": jellyfin_playlist_id,
                "songs_found": len(sorted_songs),
                "songs_matched": 0
            }
        
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
        
        # 新增歌曲到 Jellyfin 播放清單
        success = await jellyfin_playlists.add_songs_to_playlist(jellyfin_playlist_id, jellyfin_song_ids)
        
        if success:
            logger.info(f"成功同步播放清單 '{playlist['name']}' 到 Jellyfin，共 {len(jellyfin_song_ids)} 首歌曲")
            return {
                "success": True,
                "message": f"成功同步播放清單 '{playlist['name']}' 到 Jellyfin",
                "jellyfin_playlist_id": jellyfin_playlist_id,
                "songs_found": len(sorted_songs),
                "songs_matched": len(jellyfin_song_ids),
                "songs_added": len(jellyfin_song_ids)
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
import json
import os
import glob
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
from fastapi import APIRouter, HTTPException, Path as FastAPIPath, Query
from fastapi.responses import Response
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
from app.dependencies.redis_cache import redis_cache
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
        # 遞迴搜尋資料夾中的所有音訊檔案
        for root, _, files in os.walk(full_path):
            for file in files:
                # 檢查檔案副檔名是否在支援列表中
                file_ext = os.path.splitext(file)[1].lower()
                if file_ext in SUPPORTED_AUDIO_EXTENSIONS:
                    file_path = os.path.join(root, file)
                    audio_files.append(file_path)

        # 按檔案路徑排序，確保每次執行順序一致
        audio_files = sorted(audio_files)
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
            if redis_cache is None:
                tags = read_audio_tags(file_path)
            else:
                tags = redis_cache.get_cached_tags_with_fallback(file_path)
            
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

def sort_songs_by_title(songs: List[str]) -> List[str]:
    """根據歌曲標題排序（A→Z）"""
    try:
        songs_with_title = []
        logger.info(f"開始依標題排序 {len(songs)} 首歌曲")

        for i, song in enumerate(songs):
            try:
                # 使用快取讀取檔案標籤
                tags = tags_cache.get_cached_tags_with_fallback(song)

                # 優先使用 titlesort，其次使用 title，最後使用檔案名
                sort_title = tags.get('titlesort', '') or tags.get('title', '') or os.path.basename(song)
                display_title = tags.get('title', '') or os.path.basename(song)

                # 將排序標題轉為小寫進行排序，以便不區分大小寫
                sort_key = sort_title.lower()

                songs_with_title.append((song, sort_key, display_title))

                # 詳細日誌前5個檔案的標題
                if i < 5:
                    logger.info(f"檔案 {i+1}: {os.path.basename(song)}")
                    logger.info(f"  顯示標題: {display_title}")
                    logger.info(f"  排序標題 (TitleSort): {sort_title}")

            except Exception as e:
                logger.warning(f"無法獲取檔案 {song} 的標題: {str(e)}")
                # 如果無法獲取標題，使用檔案名稱
                filename = os.path.basename(song)
                songs_with_title.append((song, filename.lower(), filename))

        # 按標題排序（A→Z）
        songs_with_title.sort(key=lambda x: x[1])
        sorted_songs = [song for song, _, _ in songs_with_title]

        # 日誌排序結果
        logger.info(f"標題排序完成，前3首歌曲:")
        for i, (song, sort_key, display_title) in enumerate(songs_with_title[:3]):
            logger.info(f"  {i+1}. {display_title} (排序鍵: {sort_key})")

        return sorted_songs

    except Exception as e:
        logger.error(f"依標題排序歌曲失敗: {str(e)}")
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

def get_sort_method_display_name(sort_method: str) -> str:
    """獲取排序方式的顯示名稱"""
    sort_methods = {
        "creation_time": "檔案建立時間",
        "title": "標題 (TitleSort)"
    }
    return sort_methods.get(sort_method, "檔案建立時間")

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

    # 加入排序方式顯示名稱
    enriched_data["sort_method_display"] = get_sort_method_display_name(
        playlist_data.get("sort_method", "creation_time")
    )

    # 確保 sort_method 欄位存在，預設為 creation_time
    if "sort_method" not in enriched_data:
        enriched_data["sort_method"] = "creation_time"

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
    index: int = FastAPIPath(..., ge=0, description="播放清單索引"),
    sort_by: str = Query("creation_time", description="排序方式: creation_time 或 title")
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
        
        # 根據排序方式選擇排序函數，優先使用查詢參數，其次使用播放清單設定
        effective_sort_method = sort_by if sort_by != "creation_time" else playlist.get('sort_method', 'creation_time')

        if effective_sort_method == "title":
            sorted_songs = sort_songs_by_title(filtered_songs)
            sort_method_desc = "title"
        else:
            # 預設使用檔案建立時間排序（新→舊）
            sorted_songs = sort_songs_by_creation_time(filtered_songs)
            sort_method_desc = "file_creation_time"
        
        # 建立回傳的歌曲列表（包含排序日期資訊）
        songs_with_dates = []
        for file_path in sorted_songs:
            try:
                # 使用快取讀取檔案標籤
                if redis_cache is None:
                    tags = read_audio_tags(file_path)
                else:
                    tags = redis_cache.get_cached_tags_with_fallback(file_path)
                song_name = tags.get('title', '') or os.path.basename(file_path)
                
                # 使用檔案修改時間作為主要時間來源
                formatted_date = ""
                file_creation_time = ""
                try:
                    stat = os.stat(file_path)
                    dt = datetime.fromtimestamp(stat.st_mtime)
                    formatted_date = dt.strftime('%Y-%m-%d %H:%M:%S')
                    file_creation_time = dt.isoformat()
                except Exception as e:
                    logger.warning(f"無法獲取檔案時間 {file_path}: {str(e)}")
                    formatted_date = "無日期資訊"
                    file_creation_time = ""
                
                songs_with_dates.append({
                    "file_path": file_path,
                    "formatted_date": formatted_date,
                    "song_name": song_name
                })
                
            except Exception as e:
                logger.warning(f"處理檔案 {file_path} 時發生錯誤: {str(e)}")
                songs_with_dates.append({
                    "file_path": file_path,
                    "formatted_date": "無日期資訊",
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
            "sort_method": sort_method_desc
        }
        
        return {
            "success": True,
            "message": f"成功取得播放清單 '{playlist['name']}' 的歌曲清單（排序方式: {sort_method_desc}）",
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




def generate_m3u_content(playlist: Dict[str, Any], playlist_name: str, use_relative_paths: bool = True) -> str:
    """生成 M3U 檔案內容的通用函數"""
    # 搜尋基礎資料夾中的音訊檔案
    audio_files = find_audio_files(playlist['base_folder'])

    # 根據播放清單條件篩選歌曲
    filtered_songs = filter_songs_by_playlist(playlist, audio_files)

    # 根據播放清單設定的排序方式排序
    sort_method = playlist.get('sort_method', 'creation_time')
    if sort_method == 'title':
        sorted_songs = sort_songs_by_title(filtered_songs)
    else:
        # 預設使用檔案建立時間排序（新→舊）
        sorted_songs = sort_songs_by_creation_time(filtered_songs)
    
    logger.info(f"找到 {len(sorted_songs)} 首歌曲，生成 M3U 檔案")
    
    # 生成 M3U 內容
    m3u_content = "#EXTM3U\n"
    m3u_content += f"# Playlist: {playlist_name}\n"
    m3u_content += f"# Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
    
    # M3U 檔案將保存在 /Music/{base_folder}/Playlist/ 目錄
    if use_relative_paths:
        base_folder = playlist['base_folder']
        m3u_folder = os.path.join("/Music", base_folder, "Playlist")
    
    for file_path in sorted_songs:
        try:
            # 使用快取讀取檔案標籤
            if redis_cache is None:
                tags = read_audio_tags(file_path)
            else:
                tags = redis_cache.get_cached_tags_with_fallback(file_path)
            title = tags.get('title', '')
            artist = tags.get('artist', '')
            
            # 如果有標題和藝術家資訊，使用 EXTINF 格式
            if title or artist:
                display_name = f"{artist} - {title}".strip(' - ')
                m3u_content += f"#EXTINF:-1,{display_name}\n"
            else:
                # 使用檔案名稱
                display_name = os.path.basename(file_path)
                m3u_content += f"#EXTINF:-1,{display_name}\n"
            
            # 生成檔案路徑（絕對路徑或相對路徑）
            if use_relative_paths:
                # 計算相對於 M3U 檔案的相對路徑
                # M3U 檔案在 /Music/{base_folder}/Playlist/
                # 音訊檔案在 /Music/{base_folder}/... 
                relative_path = os.path.relpath(file_path, m3u_folder)
                m3u_content += f"{relative_path}\n"
            else:
                # 使用絕對路徑
                m3u_content += f"{file_path}\n"
            
        except Exception as e:
            logger.warning(f"處理檔案 {file_path} 時發生錯誤: {str(e)}")
            # 如果讀取標籤失敗，直接使用檔案路徑
            display_name = os.path.basename(file_path)
            m3u_content += f"#EXTINF:-1,{display_name}\n"
            
            if use_relative_paths:
                try:
                    relative_path = os.path.relpath(file_path, m3u_folder)
                    m3u_content += f"{relative_path}\n"
                except:
                    m3u_content += f"{file_path}\n"
            else:
                m3u_content += f"{file_path}\n"
    
    return m3u_content


@router.post("/{index}/generate-m3u")
async def generate_playlist_m3u_to_file(
    index: int = FastAPIPath(..., ge=0, description="播放清單索引")
):
    """生成播放清單 M3U 檔案到檔案系統"""
    try:
        logger.info(f"生成播放清單 {index} M3U 檔案到檔案系統")
        
        # 載入播放清單
        playlists_data = load_playlists()
        
        # 檢查索引是否有效
        if index >= len(playlists_data):
            raise HTTPException(
                status_code=404,
                detail=f"播放清單索引 {index} 不存在"
            )
        
        playlist = playlists_data[index]
        playlist_name = playlist.get('name', f'playlist_{index}')
        base_folder = playlist.get('base_folder', '')
        
        # 生成 M3U 內容（檔案系統生成使用相對路徑）
        m3u_content = generate_m3u_content(playlist, playlist_name, use_relative_paths=True)
        
        # 建立輸出目錄路徑：/Music/{BaseFolder}/Playlist/
        playlist_dir = os.path.join("/Music", base_folder, "Playlist")
        
        # 確保目錄存在
        os.makedirs(playlist_dir, exist_ok=True)
        
        # 清理播放清單名稱，作為檔案名稱
        safe_filename = "".join(c for c in playlist_name if c.isalnum() or c in (' ', '-', '_', '・', '。', '，', '；', '：', '！', '？')).rstrip()
        if not safe_filename:
            safe_filename = f"playlist_{index}"
        
        # M3U 檔案完整路徑
        m3u_file_path = os.path.join(playlist_dir, f"{safe_filename}.m3u")
        
        # 寫入 M3U 檔案
        try:
            with open(m3u_file_path, 'w', encoding='utf-8') as m3u_file:
                m3u_file.write(m3u_content)
        except PermissionError:
            logger.error(f"權限不足，無法寫入 {m3u_file_path}")
            raise HTTPException(
                status_code=500,
                detail=f"無法寫入檔案 {m3u_file_path}，請檢查檔案權限。可能需要執行: docker exec -u root personal-musicmanager-backend-1 chown -R appuser:appuser '/Music/{base_folder}/Playlist/'"
            )

        logger.info(f"成功生成 M3U 檔案到: {m3u_file_path}")
        
        return {
            "success": True,
            "message": f"成功生成播放清單 '{playlist_name}' 的 M3U 檔案",
            "file_path": m3u_file_path,
            "playlist_name": playlist_name,
            "songs_count": m3u_content.count('\n#EXTINF')
        }
        
    except HTTPException:
        raise
    except Exception as e:
        error_msg = f"生成 M3U 檔案到檔案系統失敗: {str(e)}"
        logger.error(error_msg)
        raise HTTPException(status_code=500, detail=error_msg)


@router.get("/{index}/download-m3u")
async def download_playlist_m3u(
    index: int = FastAPIPath(..., ge=0, description="播放清單索引")
):
    """下載播放清單為 M3U 格式"""
    try:
        logger.info(f"下載播放清單 {index} 為 M3U 格式")
        
        # 載入播放清單
        playlists_data = load_playlists()
        
        # 檢查索引是否有效
        if index >= len(playlists_data):
            raise HTTPException(
                status_code=404,
                detail=f"播放清單索引 {index} 不存在"
            )
        
        playlist = playlists_data[index]
        playlist_name = playlist.get('name', f'playlist_{index}')
        
        # 生成 M3U 內容（下載功能使用絕對路徑）
        m3u_content = generate_m3u_content(playlist, playlist_name, use_relative_paths=False)
        
        # 清理播放清單名稱，作為檔案名稱
        safe_filename = "".join(c for c in playlist_name if c.isalnum() or c in (' ', '-', '_', '・', '。', '，', '；', '：', '！', '？')).rstrip()
        if not safe_filename:
            safe_filename = f"playlist_{index}"
        
        filename = f"{safe_filename}.m3u"
        
        logger.info(f"成功生成 M3U 檔案: {filename}，包含 {m3u_content.count('#EXTINF')} 首歌曲")
        
        # 返回 M3U 檔案
        return Response(
            content=m3u_content.encode('utf-8'),
            media_type="audio/x-mpegurl",
            headers={
                "Content-Disposition": f"attachment; filename*=UTF-8''{filename.encode('utf-8').hex()}",
                "Content-Type": "audio/x-mpegurl; charset=utf-8"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        error_msg = f"下載 M3U 檔案失敗: {str(e)}"
        logger.error(error_msg)
        raise HTTPException(status_code=500, detail=error_msg)


@router.post("/generate-all-m3u")
async def generate_all_playlists_m3u():
    """批量生成所有播放清單的 M3U 檔案到檔案系統"""
    try:
        logger.info("開始批量生成所有播放清單的 M3U 檔案")
        
        # 載入所有播放清單
        playlists_data = load_playlists()
        
        if not playlists_data:
            return {
                "success": True,
                "message": "沒有播放清單需要生成",
                "generated_files": [],
                "total_count": 0,
                "success_count": 0,
                "error_count": 0
            }
        
        generated_files = []
        success_count = 0
        error_count = 0
        errors = []
        
        for index, playlist in enumerate(playlists_data):
            try:
                playlist_name = playlist.get('name', f'playlist_{index}')
                base_folder = playlist.get('base_folder', '')
                
                logger.info(f"正在生成播放清單 {index}: {playlist_name}")
                
                # 生成 M3U 內容（使用相對路徑）
                m3u_content = generate_m3u_content(playlist, playlist_name, use_relative_paths=True)
                
                # 建立輸出目錄路徑：/Music/{BaseFolder}/Playlist/
                playlist_dir = os.path.join("/Music", base_folder, "Playlist")
                
                # 確保目錄存在
                os.makedirs(playlist_dir, exist_ok=True)
                
                # 清理播放清單名稱，作為檔案名稱
                safe_filename = "".join(c for c in playlist_name if c.isalnum() or c in (' ', '-', '_', '・', '。', '，', '；', '：', '！', '？')).rstrip()
                if not safe_filename:
                    safe_filename = f"playlist_{index}"
                
                # M3U 檔案完整路徑
                m3u_file_path = os.path.join(playlist_dir, f"{safe_filename}.m3u")
                
                # 寫入 M3U 檔案
                try:
                    with open(m3u_file_path, 'w', encoding='utf-8') as m3u_file:
                        m3u_file.write(m3u_content)
                except PermissionError:
                    # 如果權限不足，嘗試以追加模式打開並清空檔案
                    logger.warning(f"權限不足，無法直接寫入 {m3u_file_path}，嘗試替代方法")
                    raise PermissionError(f"無法寫入檔案 {m3u_file_path}，請檢查檔案權限")
                
                # 計算歌曲數量
                songs_count = m3u_content.count('\n#EXTINF')
                
                generated_files.append({
                    "index": index,
                    "playlist_name": playlist_name,
                    "file_path": m3u_file_path,
                    "songs_count": songs_count,
                    "success": True
                })
                
                success_count += 1
                logger.info(f"成功生成播放清單 {index}: {playlist_name} -> {m3u_file_path}")
                
            except Exception as e:
                error_msg = f"生成播放清單 {index} ({playlist.get('name', 'Unknown')}) 失敗: {str(e)}"
                logger.error(error_msg)
                
                generated_files.append({
                    "index": index,
                    "playlist_name": playlist.get('name', f'playlist_{index}'),
                    "file_path": None,
                    "songs_count": 0,
                    "success": False,
                    "error": str(e)
                })
                
                errors.append(error_msg)
                error_count += 1
        
        logger.info(f"批量生成完成：成功 {success_count} 個，失敗 {error_count} 個")
        
        return {
            "success": True,
            "message": f"批量生成完成：成功 {success_count} 個，失敗 {error_count} 個",
            "generated_files": generated_files,
            "total_count": len(playlists_data),
            "success_count": success_count,
            "error_count": error_count,
            "errors": errors if errors else None
        }
        
    except Exception as e:
        error_msg = f"批量生成 M3U 檔案失敗: {str(e)}"
        logger.error(error_msg)
        raise HTTPException(status_code=500, detail=error_msg)
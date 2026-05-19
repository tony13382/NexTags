from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from app.schemas.audios import AudioTagsRequest, AudioTagsResponse, AudioUpdateRequest, AudioUpdateResponse
from app.dependencies.mp3tag_reader import read_audio_tags
from app.dependencies.mp3tag_writer import write_tags
from app.dependencies.redis_cache import redis_cache
from app.dependencies.utils.replaygain import generate_replaygain
from app.router.config import get_config
from app.services.shared_state import RedisDoc
import os
import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, List, Optional
import math

router = APIRouter(prefix="/audios", tags=["tools"])

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

def _find_cover_art(file_path: str) -> str:
    """在音訊檔案同目錄下尋找封面圖檔"""
    directory = os.path.dirname(file_path)
    cover_names = ['cover.jpg', 'cover.jpeg', 'cover.png', 'folder.jpg', 'folder.jpeg', 'folder.png', 'albumart.jpg', 'albumart.jpeg', 'albumart.png']
    
    for cover_name in cover_names:
        cover_path = os.path.join(directory, cover_name)
        if os.path.exists(cover_path):
            return cover_path
    return ""

def _tag_to_string(value, field_name=None):
    if isinstance(value, list):
        if field_name in ['artist', 'artistsort', 'albumartist', 'albumartistsort', 'composer', 'composersort', 'performer', 'performersort']:
            return ';'.join(str(v) for v in value) if value else ''
        return ' '.join(str(v) for v in value) if value else ''
    return str(value) if value else ''

def _get_favorite_status(tags: Dict[str, Any]) -> str:
    favorite_keys = [
        'favorite', 'FAVORITE', 'Favorite',
        'fav', 'FAV', 'Fav',
        'liked', 'LIKED', 'Liked',
        'love', 'LOVE', 'Love',
        'rating', 'RATING', 'Rating'
    ]

    for key in favorite_keys:
        if key in tags:
            value = _tag_to_string(tags[key]).lower()
            if value in ['true', '1', 'yes', 'y', 'liked', 'favorite', 'love']:
                return "True"
            if value in ['false', '0', 'no', 'n', '']:
                return "False"
            if key.lower() == 'rating':
                try:
                    rating_value = float(value)
                    return "True" if rating_value > 3 else "False"
                except Exception:
                    pass

    return "False"

def _audio_details_from_tags(
    file_path: str,
    tags: Dict[str, Any],
    allow_folders: List[str],
    modification_time: Optional[float] = None,
    cover_path: Optional[str] = None,
    main_folder: Optional[str] = None
) -> dict:
    if modification_time is None:
        modification_time = os.path.getmtime(file_path) if os.path.exists(file_path) else 0

    if not main_folder:
        main_folder = "unknown"
        music_base_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), 'Music')
        for folder_name in allow_folders:
            folder_path = os.path.join(music_base_path, folder_name)
            if file_path.startswith(folder_path):
                main_folder = folder_name
                break

    genre = tags.get('genre', [])
    if isinstance(genre, list):
        genre_list = genre if genre else ['']
    elif isinstance(genre, str):
        genre_list = [genre] if genre else ['']
    else:
        genre_list = ['']

    return {
        "Title": _tag_to_string(tags.get('title', ''), 'title'),
        "SortTitle": _tag_to_string(tags.get('titlesort', ''), 'titlesort'),
        "Artist": _tag_to_string(tags.get('artist', ''), 'artist'),
        "SortArtist": _tag_to_string(tags.get('artistsort', ''), 'artistsort'),
        "Album": _tag_to_string(tags.get('album', ''), 'album'),
        "SortAlbum": _tag_to_string(tags.get('albumsort', ''), 'albumsort'),
        "AlbumArtist": _tag_to_string(tags.get('albumartist', ''), 'albumartist'),
        "SortAlbumArtist": _tag_to_string(tags.get('albumartistsort', ''), 'albumartistsort'),
        "Composer": _tag_to_string(tags.get('composer', ''), 'composer'),
        "SortComposer": _tag_to_string(tags.get('composersort', ''), 'composersort'),
        "Performer": _tag_to_string(tags.get('performer', ''), 'performer'),
        "SortPerformer": _tag_to_string(tags.get('performersort', ''), 'performersort'),
        "DiscNumber": _tag_to_string(tags.get('discnumber', ''), 'discnumber'),
        "DiscTotal": _tag_to_string(tags.get('disctotal', ''), 'disctotal'),
        "MainFolder": main_folder,
        "FilePath": file_path,
        "Genre": genre_list,
        "Language": _tag_to_string(tags.get('language', ''), 'language'),
        "Favorite": _get_favorite_status(tags),
        "Cover": cover_path if cover_path is not None else _find_cover_art(file_path),
        "Lyrics": _tag_to_string(tags.get('lyrics', ''), 'lyrics'),
        "Comment": _tag_to_string(tags.get('comment', ''), 'comment'),
        "ReplayGainTrackGain": _tag_to_string(tags.get('replaygain_track_gain', ''), 'replaygain_track_gain'),
        "ReplayGainTrackPeak": _tag_to_string(tags.get('replaygain_track_peak', ''), 'replaygain_track_peak'),
        "ModificationTime": modification_time
    }

def _catalog_record_to_audio_details(record: Dict[str, Any], allow_folders: List[str]) -> dict:
    return _audio_details_from_tags(
        record.get("file_path", ""),
        record.get("tags", {}) or {},
        allow_folders,
        modification_time=record.get("modification_time", 0),
        cover_path=record.get("cover_path", ""),
        main_folder=record.get("main_folder")
    )

def _extract_audio_details_sync(file_path: str, allow_folders: List[str]) -> dict:
    """同步提取單個音訊檔案的詳細資訊"""
    try:
        # 使用快取讀取標籤
        if redis_cache is None:
            tags = read_audio_tags(file_path)
        else:
            tags = redis_cache.get_cached_tags_with_fallback(file_path)
        
        # 取得檔案修改時間
        modification_time = os.path.getmtime(file_path) if os.path.exists(file_path) else 0
        
        # 判斷主資料夾
        main_folder = "unknown"
        music_base_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), 'Music')
        for folder_name in allow_folders:
            folder_path = os.path.join(music_base_path, folder_name)
            if file_path.startswith(folder_path):
                main_folder = folder_name
                break
        
        # 處理流派（現在統一為 List[str] 格式）
        genre = tags.get('genre', [])
        if isinstance(genre, list):
            genre_list = genre if genre else ['']
        elif isinstance(genre, str):
            # 備用處理，以防萬一還是收到字符串格式
            genre_list = [genre] if genre else ['']
        else:
            genre_list = ['']
        
        # 尋找封面圖檔
        cover_path = _find_cover_art(file_path)
        
        # 輔助函數：將標籤值轉為字串
        def tag_to_string(value, field_name=None):
            if isinstance(value, list):
                # Artist 相關字段使用分號分隔
                if field_name in ['artist', 'artistsort', 'albumartist', 'albumartistsort', 'composer', 'composersort', 'performer', 'performersort']:
                    return ';'.join(str(v) for v in value) if value else ''
                else:
                    return ' '.join(str(v) for v in value) if value else ''
            return str(value) if value else ''
        
        # 檢查最愛狀態的多種可能標籤名稱
        def get_favorite_status():
            favorite_keys = [
                'favorite', 'FAVORITE', 'Favorite',
                'fav', 'FAV', 'Fav',
                'liked', 'LIKED', 'Liked',
                'love', 'LOVE', 'Love',
                'rating', 'RATING', 'Rating'
            ]
            
            for key in favorite_keys:
                if key in tags:
                    value = tag_to_string(tags[key]).lower()
                    # 檢查各種可能的 "true" 值
                    if value in ['true', '1', 'yes', 'y', 'liked', 'favorite', 'love']:
                        return "True"
                    elif value in ['false', '0', 'no', 'n', '']:
                        return "False"
                    # 對於 rating，如果 > 3 則視為最愛
                    elif key.lower() == 'rating':
                        try:
                            rating_value = float(value)
                            return "True" if rating_value > 3 else "False"
                        except:
                            pass
            
            return "False"
        
        return {
            "Title": tag_to_string(tags.get('title', ''), 'title'),
            "SortTitle": tag_to_string(tags.get('titlesort', ''), 'titlesort'),
            "Artist": tag_to_string(tags.get('artist', ''), 'artist'),
            "SortArtist": tag_to_string(tags.get('artistsort', ''), 'artistsort'),
            "Album": tag_to_string(tags.get('album', ''), 'album'),
            "SortAlbum": tag_to_string(tags.get('albumsort', ''), 'albumsort'),
            "AlbumArtist": tag_to_string(tags.get('albumartist', ''), 'albumartist'),
            "SortAlbumArtist": tag_to_string(tags.get('albumartistsort', ''), 'albumartistsort'),
            "Composer": tag_to_string(tags.get('composer', ''), 'composer'),
            "SortComposer": tag_to_string(tags.get('composersort', ''), 'composersort'),
            "Performer": tag_to_string(tags.get('performer', ''), 'performer'),
            "SortPerformer": tag_to_string(tags.get('performersort', ''), 'performersort'),
            "DiscNumber": tag_to_string(tags.get('discnumber', ''), 'discnumber'),
            "DiscTotal": tag_to_string(tags.get('disctotal', ''), 'disctotal'),
            "MainFolder": main_folder,
            "FilePath": file_path,
            "Genre": genre_list,
            "Language": tag_to_string(tags.get('language', ''), 'language'),
            "Favorite": get_favorite_status(),
            "Cover": cover_path,
            "Lyrics": tag_to_string(tags.get('lyrics', ''), 'lyrics'),
            "Comment": tag_to_string(tags.get('comment', ''), 'comment'),
            "ReplayGainTrackGain": tag_to_string(tags.get('replaygain_track_gain', ''), 'replaygain_track_gain'),
            "ReplayGainTrackPeak": tag_to_string(tags.get('replaygain_track_peak', ''), 'replaygain_track_peak'),
            "ModificationTime": modification_time
        }
    except Exception:
        # 如果讀取失敗，回傳基本資訊
        modification_time = os.path.getmtime(file_path) if os.path.exists(file_path) else 0
        return {
            "Title": "",
            "SortTitle": "",
            "Artist": "",
            "SortArtist": "",
            "Album": "",
            "SortAlbum": "",
            "AlbumArtist": "",
            "SortAlbumArtist": "",
            "Composer": "",
            "SortComposer": "",
            "Performer": "",
            "SortPerformer": "",
            "DiscNumber": "",
            "DiscTotal": "",
            "MainFolder": "unknown",
            "FilePath": file_path,
            "Genre": [""],
            "Language": "",
            "Favorite": "False",
            "Cover": "",
            "Lyrics": "",
            "Comment": "",
            "ReplayGainTrackGain": "",
            "ReplayGainTrackPeak": "",
            "ModificationTime": modification_time
        }

async def get_audio_details_concurrent(file_paths: List[str], allow_folders: List[str]) -> List[dict]:
    """併發提取多個音訊檔案的詳細資訊"""
    loop = asyncio.get_event_loop()
    with ThreadPoolExecutor() as executor:
        tasks = [
            loop.run_in_executor(executor, _extract_audio_details_sync, file_path, allow_folders)
            for file_path in file_paths
        ]
        results = await asyncio.gather(*tasks)
    return results

def apply_filters(audio_details: List[dict], filter_title: Optional[str], filter_folder: Optional[str], filter_favorite: Optional[str], filter_language: Optional[str]) -> List[dict]:
    """對音訊詳細資訊套用過濾條件"""
    filtered_results = audio_details

    # 標題過濾（模糊搜尋，不區分大小寫）
    if filter_title:
        filter_title_lower = filter_title.lower()
        filtered_results = [
            item for item in filtered_results
            if filter_title_lower in item.get('Title', '').lower()
        ]

    # 資料夾過濾（精確匹配）
    if filter_folder:
        filtered_results = [
            item for item in filtered_results
            if item.get('MainFolder', '') == filter_folder
        ]

    # 最愛過濾
    if filter_favorite:
        favorite_value = filter_favorite.lower() == 'true'
        favorite_str = "True" if favorite_value else "False"
        filtered_results = [
            item for item in filtered_results
            if item.get('Favorite', 'False') == favorite_str
        ]

    # 語言過濾（精確匹配）
    if filter_language:
        filtered_results = [
            item for item in filtered_results
            if item.get('Language', '').lower() == filter_language.lower()
        ]

    return filtered_results

def _get_file_modification_time(file_path: str) -> float:
    """獲取檔案修改時間"""
    try:
        return os.path.getmtime(file_path) if os.path.exists(file_path) else 0
    except Exception:
        return 0


@router.get("")
@router.get("/")
async def get_audios(
    p: Optional[int] = Query(1, ge=1, description="頁數，從1開始"),
    details: bool = Query(False, description="是否回傳詳細資訊"),
    filterTitle: Optional[str] = Query(None, description="標題過濾，模糊搜尋"),
    filterFolder: Optional[str] = Query(None, description="資料夾過濾"),
    filterFavorite: Optional[str] = Query(None, description="最愛過濾，True或False"),
    filterLanguage: Optional[str] = Query(None, description="語言過濾"),
    sortBy: Optional[str] = Query("modification_time", description="排序方式：modification_time")
):
    """獲取允許資料夾中的所有音訊檔案路徑（併發優化版本，支援分頁）"""
    try:
        allow_folders = get_config('allow_folders') or []
        supported_languages = get_config('supported_languages') or {}
        
        music_base_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), 'Music')

        # 準備所有要掃描的資料夾路徑
        folder_paths = []
        for folder_name in allow_folders:
            folder_path = os.path.join(music_base_path, folder_name)
            folder_paths.append(folder_path)

        # 檢查是否需要過濾（有任何過濾參數或需要詳細資訊）
        has_filters = filterTitle or filterFolder or filterFavorite or filterLanguage
        need_details = details or has_filters

        # 無任何 filter 時走 server-side 分頁（by_mtime ZSET），只讀該頁，
        # 不再每次翻頁都全量載入+轉換+排序整個 catalog。
        # 有 filter 或索引不可用時，落回下方既有全量路徑（資料不丟、僅較慢）。
        if redis_cache is not None and not has_filters:
            page_size = 100
            paged = redis_cache.get_audio_records_page(p, page_size)
            if paged is not None:
                page = paged["page"]
                if need_details:
                    audio_data = [
                        _catalog_record_to_audio_details(record, allow_folders)
                        for record in paged["records"]
                        if record.get("file_path")
                    ]
                else:
                    audio_data = [
                        record.get("file_path")
                        for record in paged["records"]
                        if record.get("file_path")
                    ]
                total_count = paged["total_count"]
                total_pages = paged["total_pages"]
                return {
                    "audio_files": audio_data,
                    "pagination": {
                        "current_page": page,
                        "page_size": page_size,
                        "total_count": total_count,
                        "total_pages": total_pages,
                        "has_previous": page > 1,
                        "has_next": page < total_pages
                    },
                    "allow_folders": allow_folders,
                    "supported_languages": supported_languages,
                    "details_mode": need_details,
                    "filters": {
                        "title": filterTitle,
                        "folder": filterFolder,
                        "favorite": filterFavorite,
                        "language": filterLanguage
                    },
                    "sort_by": sortBy,
                    "data_source": "redis_catalog"
                }

        data_source = "filesystem"
        catalog_records = []

        if redis_cache is not None:
            catalog_records = redis_cache.get_audio_records()

        if catalog_records:
            data_source = "redis_catalog"

        if catalog_records and need_details:
            all_detailed_info = [
                _catalog_record_to_audio_details(record, allow_folders)
                for record in catalog_records
                if record.get("file_path")
            ]

            if has_filters:
                filtered_info = apply_filters(all_detailed_info, filterTitle, filterFolder, filterFavorite, filterLanguage)
            else:
                filtered_info = all_detailed_info

            filtered_info.sort(key=lambda x: x.get('ModificationTime', 0), reverse=True)

            page_size = 100
            total_count = len(filtered_info)
            total_pages = math.ceil(total_count / page_size) if total_count > 0 else 1

            if p > total_pages:
                p = total_pages

            start_index = (p - 1) * page_size
            end_index = start_index + page_size
            audio_data = filtered_info[start_index:end_index]

        elif catalog_records:
            catalog_records.sort(key=lambda x: x.get('modification_time', 0), reverse=True)

            page_size = 100
            total_count = len(catalog_records)
            total_pages = math.ceil(total_count / page_size) if total_count > 0 else 1

            if p > total_pages:
                p = total_pages

            start_index = (p - 1) * page_size
            end_index = start_index + page_size
            audio_data = [
                record.get("file_path")
                for record in catalog_records[start_index:end_index]
                if record.get("file_path")
            ]

        else:
            # Redis catalog 尚未建立時，保留舊的檔案系統掃描 fallback。
            all_audio_files = await scan_multiple_folders_concurrent(folder_paths)
        
            if need_details:
                # 提取所有檔案的詳細資訊（用於過濾）
                all_detailed_info = await get_audio_details_concurrent(all_audio_files, allow_folders)

                # 套用過濾條件
                if has_filters:
                    filtered_info = apply_filters(all_detailed_info, filterTitle, filterFolder, filterFavorite, filterLanguage)
                else:
                    filtered_info = all_detailed_info

                # 按修改時間排序（最新的在前）
                filtered_info.sort(key=lambda x: x.get('ModificationTime', 0), reverse=True)

                # 分頁參數（基於過濾後的結果）
                page_size = 100
                total_count = len(filtered_info)
                total_pages = math.ceil(total_count / page_size) if total_count > 0 else 1

                # 驗證頁數
                if p > total_pages:
                    p = total_pages

                # 計算分頁範圍
                start_index = (p - 1) * page_size
                end_index = start_index + page_size
                paginated_data = filtered_info[start_index:end_index]

                audio_data = paginated_data

            else:
                # 簡單模式（無過濾，無詳細資訊）
                # 按修改時間排序（最新的在前）
                all_audio_files.sort(key=lambda x: _get_file_modification_time(x), reverse=True)

                page_size = 100
                total_count = len(all_audio_files)
                total_pages = math.ceil(total_count / page_size) if total_count > 0 else 1

                # 驗證頁數
                if p > total_pages:
                    p = total_pages

                # 計算分頁範圍
                start_index = (p - 1) * page_size
                end_index = start_index + page_size
                paginated_files = all_audio_files[start_index:end_index]

                audio_data = paginated_files
        
        return {
            "audio_files": audio_data,
            "pagination": {
                "current_page": p,
                "page_size": page_size,
                "total_count": total_count,
                "total_pages": total_pages,
                "has_previous": p > 1,
                "has_next": p < total_pages
            },
            "allow_folders": allow_folders,
            "supported_languages": supported_languages,
            "details_mode": need_details,
            "filters": {
                "title": filterTitle,
                "folder": filterFolder,
                "favorite": filterFavorite,
                "language": filterLanguage
            },
            "sort_by": sortBy,
            "data_source": data_source
        }
        
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="config.yaml 檔案不存在")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"獲取音訊檔案時發生錯誤: {str(e)}")

@router.get("/debug-tags")
async def debug_audio_tags(file_path: str = Query(..., description="音訊檔案完整路徑")):
    """調試端點：查看音訊檔案的原始標籤資訊"""
    try:
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="檔案不存在")
        
        raw_tags = read_audio_tags(file_path)
        
        return {
            "file_path": file_path,
            "raw_tags": raw_tags,
            "tag_keys": list(raw_tags.keys()) if raw_tags else []
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"讀取標籤時發生錯誤: {str(e)}")

def _write_tags_and_refresh_sync(path: str, merged_tags: dict) -> bool:
    """寫入標籤並刷新 Redis catalog（同步、阻塞，需在執行緒池中執行）。"""
    success = write_tags(path, merged_tags)
    if not success:
        return False
    # 更新完標籤後，同步刷新 Redis catalog，避免列表與播放清單讀到舊資料。
    if redis_cache is not None:
        redis_cache.upsert_audio_record(path, read_audio_tags(path))
    return True

@router.put("/update", response_model=AudioUpdateResponse)
async def update_audio_tags(request: AudioUpdateRequest):
    """更新音訊檔案的標籤"""
    try:
        if not os.path.exists(request.path):
            raise HTTPException(status_code=404, detail="檔案不存在")

        if not os.path.isfile(request.path):
            raise HTTPException(status_code=400, detail="路徑不是檔案")

        # 將 tags 列表合併為單一字典
        merged_tags = {}
        for tag_dict in request.tags:
            merged_tags.update(tag_dict)

        # 寫標籤 + 刷新 catalog 都是阻塞 I/O（mutagen 寫檔、遠端掛載 stat、Redis），
        # 丟到執行緒池，避免卡住 event loop 影響其他請求。
        loop = asyncio.get_event_loop()
        success = await loop.run_in_executor(
            None, _write_tags_and_refresh_sync, request.path, merged_tags
        )

        if not success:
            return AudioUpdateResponse(
                success=False,
                message="無法更新檔案標籤"
            )

        return AudioUpdateResponse(
            success=True,
            message="成功更新標籤",
            updated_tags=merged_tags
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"更新標籤時發生錯誤: {str(e)}")

def get_folder_from_path(file_path: str) -> str:
    """根據檔案路徑判斷屬於哪個 allow_folder"""
    try:
        allow_folders = get_config('allow_folders') or []
        
        music_base_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), 'Music')
        
        for folder_name in allow_folders:
            folder_path = os.path.join(music_base_path, folder_name)
            if file_path.startswith(folder_path):
                return folder_name
        
        return "unknown"
    except Exception:
        return "unknown"

@router.post("/", response_model=AudioTagsResponse)
async def get_audio_tags(request: AudioTagsRequest):
    """獲取音訊檔案的標籤信息"""
    try:
        if not os.path.exists(request.path):
            raise HTTPException(status_code=404, detail="檔案不存在")
        
        if not os.path.isfile(request.path):
            raise HTTPException(status_code=400, detail="路徑不是檔案")
        
        # 使用快取讀取標籤
        if redis_cache is None:
            tags = read_audio_tags(request.path)
        else:
            tags = redis_cache.get_cached_tags_with_fallback(request.path)
        folder = get_folder_from_path(request.path)
        
        if not tags:
            return AudioTagsResponse(
                tags={},
                success=False,
                message="無法讀取檔案標籤或檔案不含標籤",
                path=request.path,
                folder=folder
            )
        
        return AudioTagsResponse(
            tags=tags,
            success=True,
            message="成功讀取標籤",
            path=request.path,
            folder=folder
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"讀取標籤時發生錯誤: {str(e)}")

class ReplayGainRequest(BaseModel):
    path: str

class ReplayGainResponse(BaseModel):
    success: bool
    message: str
    path: str

def _generate_replaygain_and_refresh_sync(path: str):
    """生成 ReplayGain 並刷新 catalog（同步、阻塞，需在執行緒池中執行）。"""
    success, message = generate_replaygain(path)
    if success and redis_cache is not None:
        # 刷新快取，讓列表與播放清單立即看到新的 ReplayGain 標籤
        redis_cache.upsert_audio_record(path, read_audio_tags(path))
    return success, message

@router.post("/replaygain", response_model=ReplayGainResponse)
async def generate_audio_replaygain(request: ReplayGainRequest):
    """為音訊檔案生成 ReplayGain 標籤"""
    try:
        if not os.path.exists(request.path):
            raise HTTPException(status_code=404, detail="檔案不存在")

        if not os.path.isfile(request.path):
            raise HTTPException(status_code=400, detail="路徑不是檔案")

        # ffmpeg 子程序（最長 120s）+ mutagen 讀檔 + Redis 寫入皆為阻塞 I/O，
        # 一律丟執行緒池，避免單一請求卡死整個 worker。
        loop = asyncio.get_event_loop()
        success, message = await loop.run_in_executor(
            None, _generate_replaygain_and_refresh_sync, request.path
        )

        if success:
            return ReplayGainResponse(
                success=True,
                message=message,
                path=request.path
            )
        else:
            return ReplayGainResponse(
                success=False,
                message=message,
                path=request.path
            )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"生成 ReplayGain 時發生錯誤: {str(e)}")

class BatchReplayGainResponse(BaseModel):
    success: bool
    message: str
    total_files: int
    processed_files: int
    failed_files: int

# 批量處理狀態：改用 Redis 持久化（跨重啟 / 多 worker；崩潰後 is_running
# 不會卡住）。累加在行程內 local dict 進行，於關鍵點寫入快照到 Redis。
_BATCH_RG_DEFAULT = {
    "is_running": False,
    "total_files": 0,
    "processed_files": 0,
    "failed_files": 0,
    "current_file": "",
    "start_time": None
}
_batch_replaygain_doc = RedisDoc("taskmgr:batch_replaygain", _BATCH_RG_DEFAULT)

def _run_batch_replaygain_sync():
    """同步執行批量 ReplayGain 生成（在背景執行）"""
    from app.dependencies.logger import logger
    status = dict(_BATCH_RG_DEFAULT)

    try:
        status["is_running"] = True
        status["start_time"] = asyncio.get_event_loop().time() if asyncio.get_event_loop() else 0
        _batch_replaygain_doc.set(status)

        allow_folders = get_config('allow_folders') or []
        music_base_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), 'Music')

        # 準備所有要掃描的資料夾路徑並同步掃描
        all_audio_files = []
        for folder_name in allow_folders:
            folder_path = os.path.join(music_base_path, folder_name)
            if os.path.exists(folder_path) and os.path.isdir(folder_path):
                audio_files = _scan_folder_sync(folder_path)
                all_audio_files.extend(audio_files)

        status["total_files"] = len(all_audio_files)
        status["processed_files"] = 0
        status["failed_files"] = 0
        _batch_replaygain_doc.set(status)

        logger.info(f"開始批量生成 ReplayGain，共 {len(all_audio_files)} 個檔案")

        # 批量處理每個檔案
        for i, file_path in enumerate(all_audio_files, 1):
            try:
                status["current_file"] = file_path
                logger.info(f"處理 [{i}/{len(all_audio_files)}]: {file_path}")
                success, msg = generate_replaygain(file_path)
                if success:
                    status["processed_files"] += 1
                    logger.info(f"成功 [{i}/{len(all_audio_files)}]: {file_path}")
                    if redis_cache is not None:
                        redis_cache.upsert_audio_record(file_path, read_audio_tags(file_path))
                else:
                    status["failed_files"] += 1
                    logger.error(f"失敗 [{i}/{len(all_audio_files)}]: {file_path} - {msg}")
            except Exception as e:
                status["failed_files"] += 1
                logger.error(f"異常 [{i}/{len(all_audio_files)}]: {file_path} - {str(e)}")
            _batch_replaygain_doc.set(status)

        logger.info(f"批量生成完成：總計 {len(all_audio_files)}，成功 {status['processed_files']}，失敗 {status['failed_files']}")

    except Exception as e:
        logger.error(f"批量生成 ReplayGain 異常: {str(e)}")
    finally:
        status["is_running"] = False
        status["current_file"] = ""
        _batch_replaygain_doc.set(status)

@router.post("/replaygain/batch")
async def generate_batch_replaygain():
    """啟動批量生成 ReplayGain 標籤（後台執行）"""
    current = _batch_replaygain_doc.get()

    if current.get("is_running"):
        return {
            "success": False,
            "message": "批量生成已在進行中",
            "status": current
        }

    # 在背景執行批量處理
    loop = asyncio.get_event_loop()
    loop.run_in_executor(None, _run_batch_replaygain_sync)

    return {
        "success": True,
        "message": "批量生成已啟動，請使用 /audios/replaygain/batch/status 查詢進度"
    }

@router.get("/replaygain/batch/status")
async def get_batch_replaygain_status():
    """查詢批量生成 ReplayGain 的進度"""
    return {
        "success": True,
        "status": _batch_replaygain_doc.get()
    }

from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List, Dict, Any
from app.dependencies.jellyfin_connetor import songs
from app.dependencies.logger import logger

router = APIRouter(prefix="/jellyfin", tags=["jellyfin"])


@router.get("/songs")
async def get_jellyfin_songs(
    title: Optional[str] = Query(None, description="歌曲標題搜尋關鍵字"),
    album: Optional[str] = Query(None, description="專輯名稱搜尋關鍵字"),
    artist: Optional[str] = Query(None, description="演出者名稱搜尋關鍵字"),
    limit: int = Query(50, ge=1, le=500, description="返回結果數量限制"),
    q: Optional[str] = Query(None, description="通用搜尋關鍵字（搜尋歌曲名稱、演出者、專輯等）")
) -> Dict[str, Any]:
    """
    搜尋 Jellyfin 歌曲資料
    
    支援以下搜尋方式：
    1. 使用 title 參數搜尋特定歌曲標題
    2. 使用 album 參數搜尋特定專輯的歌曲
    3. 使用 artist 參數搜尋特定演出者的歌曲
    4. 使用 q 參數進行通用搜尋
    5. 組合使用多個參數進行精確搜尋
    
    返回格式化的 Jellyfin 歌曲資訊列表
    """
    try:
        logger.info(f"接收到 Jellyfin 歌曲搜尋請求 - title: {title}, album: {album}, artist: {artist}, q: {q}")
        
        songs_list = []
        search_params = []
        
        # 根據不同參數執行搜尋
        if q:
            # 通用搜尋
            search_params.append(f"通用搜尋: {q}")
            songs_list = await songs.search_songs(q, limit=limit)
            
        elif artist:
            # 根據演出者搜尋
            search_params.append(f"演出者: {artist}")
            songs_list = await songs.get_songs_by_artist(artist, limit=limit)
            
        elif album:
            # 根據專輯搜尋
            search_params.append(f"專輯: {album}")
            songs_list = await songs.get_songs_by_album(album, limit=limit)
            
        elif title:
            # 根據標題搜尋
            search_params.append(f"標題: {title}")
            songs_list = await songs.search_songs(title, limit=limit)
            
        else:
            # 如果沒有提供任何搜尋參數，回傳錯誤
            raise HTTPException(
                status_code=400, 
                detail="請提供至少一個搜尋參數：title、album、artist 或 q"
            )
        
        # 如果有多個搜尋條件，進行結果過濾
        if len([p for p in [title, album, artist] if p]) > 1:
            filtered_songs = []
            for song in songs_list:
                # 檢查標題匹配
                title_match = not title or title.lower() in song.get('Name', '').lower()
                
                # 檢查專輯匹配
                album_match = not album or album.lower() in song.get('Album', '').lower()
                
                # 檢查演出者匹配
                artist_match = not artist or any(
                    artist.lower() in artist_name.lower() 
                    for artist_name in song.get('Artists', [])
                )
                
                if title_match and album_match and artist_match:
                    filtered_songs.append(song)
            
            songs_list = filtered_songs
            search_params.append("已套用多重過濾條件")
        
        # 格式化響應
        response_data = {
            "success": True,
            "total_count": len(songs_list),
            "search_params": search_params,
            "limit": limit,
            "songs": songs_list
        }
        
        logger.info(f"Jellyfin 歌曲搜尋完成 - 找到 {len(songs_list)} 首歌曲")
        return response_data
        
    except Exception as e:
        error_msg = f"搜尋 Jellyfin 歌曲時發生錯誤: {str(e)}"
        logger.error(error_msg)
        raise HTTPException(status_code=500, detail=error_msg)


@router.get("/songs/{song_id}")
async def get_jellyfin_song_by_id(song_id: str) -> Dict[str, Any]:
    """
    根據 ID 取得特定 Jellyfin 歌曲的詳細資訊
    
    Args:
        song_id: Jellyfin 歌曲 ID
        
    Returns:
        歌曲詳細資訊
    """
    try:
        logger.info(f"取得 Jellyfin 歌曲詳細資訊 - ID: {song_id}")
        
        song_detail = await songs.get_song_by_id(song_id)
        
        if not song_detail:
            raise HTTPException(
                status_code=404, 
                detail=f"找不到 ID 為 {song_id} 的歌曲"
            )
        
        response_data = {
            "success": True,
            "song": song_detail
        }
        
        logger.info(f"成功取得歌曲資訊: {song_detail.get('Name', 'Unknown')}")
        return response_data
        
    except HTTPException:
        raise
    except Exception as e:
        error_msg = f"取得 Jellyfin 歌曲詳細資訊時發生錯誤: {str(e)}"
        logger.error(error_msg)
        raise HTTPException(status_code=500, detail=error_msg)


@router.get("/songs/{song_id}/stream")
async def get_jellyfin_song_stream_url(
    song_id: str,
    format: str = Query("mp3", description="音訊格式 (mp3, flac, ogg 等)"),
    bitrate: int = Query(320000, ge=64000, le=1411000, description="位元率")
) -> Dict[str, Any]:
    """
    取得 Jellyfin 歌曲的串流 URL
    
    Args:
        song_id: Jellyfin 歌曲 ID
        format: 音訊格式
        bitrate: 位元率
        
    Returns:
        包含串流 URL 的響應
    """
    try:
        logger.info(f"取得 Jellyfin 歌曲串流 URL - ID: {song_id}, 格式: {format}, 位元率: {bitrate}")
        
        # 先檢查歌曲是否存在
        song_detail = await songs.get_song_by_id(song_id)
        if not song_detail:
            raise HTTPException(
                status_code=404, 
                detail=f"找不到 ID 為 {song_id} 的歌曲"
            )
        
        # 取得串流 URL
        stream_url = await songs.get_song_stream_url(song_id, format=format, bitrate=bitrate)
        
        if not stream_url:
            raise HTTPException(
                status_code=500, 
                detail="無法產生串流 URL"
            )
        
        response_data = {
            "success": True,
            "song_id": song_id,
            "song_name": song_detail.get('Name', 'Unknown'),
            "format": format,
            "bitrate": bitrate,
            "stream_url": stream_url
        }
        
        logger.info(f"成功產生串流 URL: {song_detail.get('Name', 'Unknown')}")
        return response_data
        
    except HTTPException:
        raise
    except Exception as e:
        error_msg = f"取得 Jellyfin 歌曲串流 URL 時發生錯誤: {str(e)}"
        logger.error(error_msg)
        raise HTTPException(status_code=500, detail=error_msg)


@router.get("/health")
async def jellyfin_health_check() -> Dict[str, Any]:
    """
    Jellyfin 連接器健康檢查
    
    檢查 Jellyfin 連接器是否正常初始化
    """
    try:
        # 檢查連接器是否正常初始化
        if songs.jellyfin_songs is None:
            return {
                "status": "error",
                "message": "Jellyfin Songs Client 未正確初始化",
                "details": "請檢查 .env 檔案中的 JELLYFIN_HOST, JELLYFIN_USER_NAME, JELLYFIN_USER_PW 設定"
            }
        
        # 嘗試執行一個簡單的搜尋來測試連接
        try:
            test_results = await songs.search_songs("test", limit=1)
            connection_status = "connected"
            test_message = f"連接測試成功，可以存取 Jellyfin API"
        except Exception as e:
            connection_status = "connection_error"
            test_message = f"連接測試失敗: {str(e)}"
        
        return {
            "status": "ok",
            "jellyfin_client_initialized": True,
            "connection_status": connection_status,
            "test_message": test_message,
            "host": songs.jellyfin_songs.host if songs.jellyfin_songs else None,
            "user_id": songs.jellyfin_songs.user_id if songs.jellyfin_songs else None
        }
        
    except Exception as e:
        logger.error(f"Jellyfin 健康檢查失敗: {str(e)}")
        return {
            "status": "error",
            "message": f"健康檢查失敗: {str(e)}"
        }
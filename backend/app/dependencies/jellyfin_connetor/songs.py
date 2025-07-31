import httpx
import asyncio
from typing import Dict, List, Optional, Any
from urllib.parse import urlencode

from app.dependencies.logger import logger
from config import JELLYFIN_HOST
from .auth import jellyfin_auth, get_auth_headers, get_authenticated_user_id


class JellyfinSongsClient:
    """Jellyfin 歌曲搜尋和資訊取得客戶端"""
    
    def __init__(self):
        self.host = JELLYFIN_HOST
        self.base_url = f"{self.host}/emby"
        
        if not self.host:
            raise ValueError("Jellyfin 配置不完整：需要 JELLYFIN_HOST")
        
        if not jellyfin_auth:
            raise ValueError("Jellyfin 認證客戶端未初始化")
    
    def _build_url(self, endpoint: str, params: Dict[str, Any] = None) -> str:
        """建構 API URL"""
        url = f"{self.base_url}/{endpoint}"
        if params:
            url += f"?{urlencode(params)}"
        return url
    
    async def _make_request(self, method: str, endpoint: str, params: Dict[str, Any] = None, data: Dict[str, Any] = None) -> Optional[Dict]:
        """發送 HTTP 請求到 Jellyfin API"""
        # 確保已認證並取得標頭
        auth_headers = await get_auth_headers()
        if not auth_headers:
            logger.error("無法取得認證標頭")
            return None
        
        url = self._build_url(endpoint, params)
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                if method.upper() == "GET":
                    response = await client.get(url, headers=auth_headers)
                elif method.upper() == "POST":
                    response = await client.post(url, json=data, headers=auth_headers)
                elif method.upper() == "PUT":
                    response = await client.put(url, json=data, headers=auth_headers)
                elif method.upper() == "DELETE":
                    response = await client.delete(url, headers=auth_headers)
                else:
                    raise ValueError(f"不支援的 HTTP 方法: {method}")
                
                response.raise_for_status()
                return response.json()
                
        except httpx.HTTPStatusError as e:
            logger.error(f"Jellyfin API HTTP 錯誤: {e.response.status_code} - {e.response.text}")
            return None
        except httpx.RequestError as e:
            logger.error(f"Jellyfin API 請求錯誤: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Jellyfin API 未知錯誤: {str(e)}")
            return None
    
    async def search_songs(self, query: str, limit: int = 50, include_item_types: str = "Audio") -> List[Dict]:
        """搜尋歌曲
        
        Args:
            query: 搜尋關鍵字
            limit: 返回結果數量限制
            include_item_types: 項目類型，預設為 Audio
            
        Returns:
            歌曲資訊列表
        """
        logger.info(f"搜尋歌曲: {query}")
        
        # 取得用戶 ID
        user_id = await get_authenticated_user_id()
        if not user_id:
            logger.error("無法取得用戶 ID")
            return []
        
        params = {
            "searchTerm": query,
            "limit": limit,
            "includeItemTypes": include_item_types,
            "recursive": "true",
            "userId": user_id
        }
        
        result = await self._make_request("GET", f"Users/{user_id}/Items", params)
        
        if result and "Items" in result:
            songs = []
            for item in result["Items"]:
                song_info = self._format_song_info(item)
                songs.append(song_info)
            
            logger.info(f"找到 {len(songs)} 首歌曲")
            return songs
        
        logger.warning(f"搜尋歌曲失敗或無結果：{query}")
        return []
    
    async def get_song_by_id(self, song_id: str) -> Optional[Dict]:
        """根據 ID 取得歌曲詳細資訊
        
        Args:
            song_id: Jellyfin 歌曲 ID
            
        Returns:
            歌曲詳細資訊或 None
        """
        logger.info(f"取得歌曲資訊: {song_id}")
        
        # 取得用戶 ID
        user_id = await get_authenticated_user_id()
        if not user_id:
            logger.error("無法取得用戶 ID")
            return None
        
        params = {"userId": user_id}
        result = await self._make_request("GET", f"Users/{user_id}/Items/{song_id}", params)
        
        if result:
            song_info = self._format_song_info(result)
            logger.info(f"成功取得歌曲資訊: {song_info.get('Name', 'Unknown')}")
            return song_info
        
        logger.warning(f"無法取得歌曲資訊: {song_id}")
        return None
    
    async def get_songs_by_artist(self, artist_name: str, limit: int = 100) -> List[Dict]:
        """根據演出者搜尋歌曲
        
        Args:
            artist_name: 演出者名稱
            limit: 返回結果數量限制
            
        Returns:
            歌曲資訊列表
        """
        logger.info(f"搜尋演出者歌曲: {artist_name}")
        
        # 取得用戶 ID
        user_id = await get_authenticated_user_id()
        if not user_id:
            logger.error("無法取得用戶 ID")
            return []
        
        params = {
            "searchTerm": artist_name,
            "limit": limit,
            "includeItemTypes": "Audio",
            "recursive": "true",
            "userId": user_id,
            "fields": "Artists,AlbumArtists"
        }
        
        result = await self._make_request("GET", f"Users/{user_id}/Items", params)
        
        if result and "Items" in result:
            # 過濾包含指定演出者的歌曲
            filtered_songs = []
            for item in result["Items"]:
                artists = item.get("Artists", []) + item.get("AlbumArtists", [])
                if any(artist_name.lower() in artist.lower() for artist in artists):
                    song_info = self._format_song_info(item)
                    filtered_songs.append(song_info)
            
            logger.info(f"找到演出者 {artist_name} 的 {len(filtered_songs)} 首歌曲")
            return filtered_songs
        
        logger.warning(f"搜尋演出者歌曲失敗：{artist_name}")
        return []
    
    async def get_songs_by_album(self, album_name: str, limit: int = 100) -> List[Dict]:
        """根據專輯搜尋歌曲
        
        Args:
            album_name: 專輯名稱  
            limit: 返回結果數量限制
            
        Returns:
            歌曲資訊列表
        """
        logger.info(f"搜尋專輯歌曲: {album_name}")
        
        # 取得用戶 ID
        user_id = await get_authenticated_user_id()
        if not user_id:
            logger.error("無法取得用戶 ID")
            return []
        
        params = {
            "searchTerm": album_name,
            "limit": limit,
            "includeItemTypes": "Audio",
            "recursive": "true",
            "userId": user_id,
            "fields": "Album"
        }
        
        result = await self._make_request("GET", f"Users/{user_id}/Items", params)
        
        if result and "Items" in result:
            # 過濾包含指定專輯的歌曲
            filtered_songs = []
            for item in result["Items"]:
                if item.get("Album", "").lower() == album_name.lower():
                    song_info = self._format_song_info(item)
                    filtered_songs.append(song_info)
            
            logger.info(f"找到專輯 {album_name} 的 {len(filtered_songs)} 首歌曲")
            return filtered_songs
        
        logger.warning(f"搜尋專輯歌曲失敗：{album_name}")
        return []
    
    async def get_song_stream_url(self, song_id: str, format: str = "mp3", bitrate: int = 320000) -> Optional[str]:
        """取得歌曲串流 URL
        
        Args:
            song_id: Jellyfin 歌曲 ID
            format: 音訊格式 (mp3, flac, ogg 等)
            bitrate: 位元率
            
        Returns:
            串流 URL 或 None
        """
        # 取得用戶 ID 和 Access Token
        user_id = await get_authenticated_user_id()
        auth_headers = await get_auth_headers()
        if not user_id or not auth_headers:
            logger.error("無法取得認證資訊")
            return None
        
        # 從認證標頭提取 Token
        auth_header = auth_headers.get('Authorization', '')
        token_start = auth_header.find('Token="') + 7
        token_end = auth_header.find('"', token_start)
        access_token = auth_header[token_start:token_end] if token_start > 6 and token_end > token_start else ""
        
        if not access_token:
            logger.error("無法從認證標頭提取 Access Token")
            return None
        
        params = {
            "userId": user_id,
            "audioCodec": format,
            "audioBitRate": bitrate,
            "api_key": access_token  # 使用 Access Token 而非 API Key
        }
        
        stream_url = f"{self.base_url}/Audio/{song_id}/stream?{urlencode(params)}"
        logger.info(f"產生串流 URL: {song_id}")
        return stream_url
    
    def _format_song_info(self, item: Dict) -> Dict:
        """格式化歌曲資訊
        
        Args:
            item: Jellyfin 回傳的項目資訊
            
        Returns:
            格式化後的歌曲資訊
        """
        return {
            "Id": item.get("Id"),
            "Name": item.get("Name"),
            "Artists": item.get("Artists", []),
            "AlbumArtists": item.get("AlbumArtists", []),
            "Album": item.get("Album"),
            "IndexNumber": item.get("IndexNumber"),  # 曲目編號
            "ParentIndexNumber": item.get("ParentIndexNumber"),  # 光碟編號
            "ProductionYear": item.get("ProductionYear"),
            "Genres": item.get("Genres", []),
            "RunTimeTicks": item.get("RunTimeTicks"),  # 播放時間（以 ticks 為單位）
            "PlayCount": item.get("UserData", {}).get("PlayCount", 0),
            "IsFavorite": item.get("UserData", {}).get("IsFavorite", False),
            "DateCreated": item.get("DateCreated"),
            "Path": item.get("Path"),
            "MediaType": item.get("MediaType"),
            "Type": item.get("Type"),
            "ServerId": item.get("ServerId"),
            "ChannelId": item.get("ChannelId"),
            "MediaStreams": item.get("MediaStreams", []),
            "ImageTags": item.get("ImageTags", {}),
            "BackdropImageTags": item.get("BackdropImageTags", []),
            "LocationType": item.get("LocationType")
        }


# 創建全域實例
try:
    jellyfin_songs = JellyfinSongsClient()
except ValueError as e:
    logger.error(f"初始化 Jellyfin Songs Client 失敗: {e}")
    jellyfin_songs = None


# 便捷函數
async def search_songs(query: str, limit: int = 50) -> List[Dict]:
    """搜尋歌曲的便捷函數"""
    if not jellyfin_songs:
        logger.error("Jellyfin Songs Client 未初始化")
        return []
    return await jellyfin_songs.search_songs(query, limit)


async def get_song_by_id(song_id: str) -> Optional[Dict]:
    """取得歌曲資訊的便捷函數"""
    if not jellyfin_songs:
        logger.error("Jellyfin Songs Client 未初始化")
        return None
    return await jellyfin_songs.get_song_by_id(song_id)


async def get_songs_by_artist(artist_name: str, limit: int = 100) -> List[Dict]:
    """根據演出者搜尋歌曲的便捷函數"""
    if not jellyfin_songs:
        logger.error("Jellyfin Songs Client 未初始化")
        return []
    return await jellyfin_songs.get_songs_by_artist(artist_name, limit)


async def get_songs_by_album(album_name: str, limit: int = 100) -> List[Dict]:
    """根據專輯搜尋歌曲的便捷函數"""
    if not jellyfin_songs:
        logger.error("Jellyfin Songs Client 未初始化")
        return []
    return await jellyfin_songs.get_songs_by_album(album_name, limit)


async def get_song_stream_url(song_id: str, format: str = "mp3", bitrate: int = 320000) -> Optional[str]:
    """取得歌曲串流 URL 的便捷函數"""
    if not jellyfin_songs:
        logger.error("Jellyfin Songs Client 未初始化")
        return None
    return await jellyfin_songs.get_song_stream_url(song_id, format, bitrate)
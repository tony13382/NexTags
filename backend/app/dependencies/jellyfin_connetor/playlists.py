import httpx
import asyncio
from typing import Dict, List, Optional, Any
from urllib.parse import urlencode

from app.dependencies.logger import logger
from config import JELLYFIN_HOST
from .auth import jellyfin_auth, get_auth_headers, get_authenticated_user_id


class JellyfinPlaylistsClient:
    """Jellyfin 播放清單搜尋和操作客戶端"""
    
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
        logger.info(f"DEBUG: 完整請求 URL - {method} {url}")
        
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
                
                logger.info(f"DEBUG: 回應狀態碼: {response.status_code}")
                logger.info(f"DEBUG: 回應內容: {response.text[:500]}")  # 限制日誌長度
                
                response.raise_for_status()
                
                # 某些 API 可能返回空響應
                if response.status_code == 204:
                    return {"success": True}
                
                try:
                    return response.json()
                except:
                    return {"success": True, "content": response.text}
                
        except httpx.HTTPStatusError as e:
            logger.error(f"Jellyfin API HTTP 錯誤: {e.response.status_code} - {e.response.text}")
            # 嘗試解析具體的錯誤訊息
            try:
                error_detail = e.response.json()
                logger.error(f"詳細錯誤信息: {error_detail}")
            except:
                pass
            return None
        except httpx.RequestError as e:
            logger.error(f"Jellyfin API 請求錯誤: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Jellyfin API 未知錯誤: {str(e)}")
            return None
    
    async def get_playlists(self) -> List[Dict]:
        """取得使用者的所有播放清單
        
        Returns:
            播放清單資訊列表
        """
        logger.info("取得使用者播放清單")
        
        # 取得用戶 ID
        user_id = await get_authenticated_user_id()
        if not user_id:
            logger.error("無法取得用戶 ID")
            return []
        
        params = {
            "userId": user_id,
            "includeItemTypes": "Playlist",
            "recursive": "true"
        }
        
        result = await self._make_request("GET", f"Users/{user_id}/Items", params)
        
        if result and "Items" in result:
            playlists = []
            for item in result["Items"]:
                playlist_info = self._format_playlist_info(item)
                playlists.append(playlist_info)
            
            logger.info(f"找到 {len(playlists)} 個播放清單")
            return playlists
        
        logger.warning("取得播放清單失敗或無結果")
        return []
    
    async def search_playlists(self, query: str, limit: int = 50) -> List[Dict]:
        """搜尋播放清單
        
        Args:
            query: 搜尋關鍵字
            limit: 返回結果數量限制
            
        Returns:
            播放清單資訊列表
        """
        logger.info(f"搜尋播放清單: {query}")
        
        # 取得用戶 ID
        user_id = await get_authenticated_user_id()
        if not user_id:
            logger.error("無法取得用戶 ID")
            return []
        
        params = {
            "searchTerm": query,
            "limit": limit,
            "includeItemTypes": "Playlist",
            "recursive": "true",
            "userId": user_id
        }
        
        result = await self._make_request("GET", f"Users/{user_id}/Items", params)
        
        if result and "Items" in result:
            playlists = []
            for item in result["Items"]:
                playlist_info = self._format_playlist_info(item)
                playlists.append(playlist_info)
            
            logger.info(f"找到 {len(playlists)} 個播放清單")
            return playlists
        
        logger.warning(f"搜尋播放清單失敗或無結果：{query}")
        return []
    
    async def get_playlist_by_id(self, playlist_id: str) -> Optional[Dict]:
        """根據 ID 取得播放清單詳細資訊
        
        Args:
            playlist_id: Jellyfin 播放清單 ID
            
        Returns:
            播放清單詳細資訊或 None
        """
        logger.info(f"取得播放清單資訊: {playlist_id}")
        
        # 取得用戶 ID
        user_id = await get_authenticated_user_id()
        if not user_id:
            logger.error("無法取得用戶 ID")
            return None
        
        params = {"userId": user_id}
        result = await self._make_request("GET", f"Users/{user_id}/Items/{playlist_id}", params)
        
        if result:
            playlist_info = self._format_playlist_info(result)
            logger.info(f"成功取得播放清單資訊: {playlist_info.get('Name', 'Unknown')}")
            return playlist_info
        
        logger.warning(f"無法取得播放清單資訊: {playlist_id}")
        return None
    
    async def get_playlist_items(self, playlist_id: str, limit: int = 1000) -> List[Dict]:
        """取得播放清單中的歌曲
        
        Args:
            playlist_id: Jellyfin 播放清單 ID
            limit: 返回結果數量限制
            
        Returns:
            播放清單中的歌曲列表
        """
        logger.info(f"取得播放清單歌曲: {playlist_id}")
        
        # 取得用戶 ID
        user_id = await get_authenticated_user_id()
        if not user_id:
            logger.error("無法取得用戶 ID")
            return []
        
        params = {
            "userId": user_id,
            "limit": limit,
            "fields": "Artists,Album,Genres,RunTimeTicks,UserData,PlaylistItemId"
        }
        
        result = await self._make_request("GET", f"Playlists/{playlist_id}/Items", params)
        
        if result and "Items" in result:
            songs = []
            logger.info(f"DEBUG: 原始 API 回應包含 {len(result['Items'])} 個項目")
            
            for i, item in enumerate(result["Items"]):
                logger.info(f"DEBUG: 項目 {i} 的可用鍵: {list(item.keys())}")
                logger.info(f"DEBUG: 項目 {i} 的 PlaylistItemId: {item.get('PlaylistItemId')}")
                logger.info(f"DEBUG: 項目 {i} 的 Id: {item.get('Id')}")
                
                # 使用與 songs.py 相同的格式化方法
                song_info = self._format_song_info(item)
                songs.append(song_info)
            
            logger.info(f"播放清單包含 {len(songs)} 首歌曲")
            return songs
        
        logger.warning(f"取得播放清單歌曲失敗: {playlist_id}")
        return []
    
    async def create_playlist(self, name: str, description: str = "", song_ids: List[str] = None) -> Optional[str]:
        """建立新的播放清單
        
        Args:
            name: 播放清單名稱
            description: 播放清單描述
            song_ids: 要添加到播放清單的歌曲 ID 列表
            
        Returns:
            新建立的播放清單 ID 或 None
        """
        logger.info(f"建立播放清單: {name}")
        
        # 取得用戶 ID
        user_id = await get_authenticated_user_id()
        if not user_id:
            logger.error("無法取得用戶 ID")
            return None
        
        # 如果歌曲數量過多，先建立空播放清單，再分批添加歌曲
        if song_ids and len(song_ids) > 50:
            logger.info(f"歌曲數量過多 ({len(song_ids)})，將先建立空播放清單再分批添加歌曲")
            
            # 先建立空播放清單
            data = {
                "Name": name,
                "Overview": description,
                "Ids": [],
                "UserId": user_id
            }
            
            result = await self._make_request("POST", "Playlists", data=data)
            
            if result and "Id" in result:
                playlist_id = result["Id"]
                logger.info(f"成功建立空播放清單: {name} (ID: {playlist_id})")
                
                # 分批添加歌曲
                success = await self.add_songs_to_playlist(playlist_id, song_ids)
                if success:
                    logger.info(f"成功建立播放清單並添加 {len(song_ids)} 首歌曲: {name}")
                    return playlist_id
                else:
                    logger.error(f"建立播放清單成功但添加歌曲失敗: {name}")
                    return playlist_id  # 仍返回播放清單 ID，因為播放清單已建立
            else:
                logger.error(f"建立播放清單失敗: {name}")
                return None
        else:
            # 歌曲數量不多，直接建立
            data = {
                "Name": name,
                "Overview": description,
                "Ids": song_ids or [],
                "UserId": user_id
            }
            
            result = await self._make_request("POST", "Playlists", data=data)
            
            if result and "Id" in result:
                playlist_id = result["Id"]
                logger.info(f"成功建立播放清單: {name} (ID: {playlist_id})")
                return playlist_id
            
            logger.error(f"建立播放清單失敗: {name}")
            return None
    
    async def add_songs_to_playlist(self, playlist_id: str, song_ids: List[str]) -> bool:
        """添加歌曲到播放清單（支援批次處理以避免 URL 過長）
        
        Args:
            playlist_id: 播放清單 ID
            song_ids: 要添加的歌曲 ID 列表
            
        Returns:
            操作是否成功
        """
        logger.info(f"添加 {len(song_ids)} 首歌曲到播放清單: {playlist_id}")
        logger.info(f"歌曲 ID 順序檢查 (前5個):")
        for i, song_id in enumerate(song_ids[:5]):
            logger.info(f"  位置 {i+1}: {song_id}")
        
        if not song_ids:
            logger.info("沒有歌曲需要添加")
            return True
        
        # 取得用戶 ID
        user_id = await get_authenticated_user_id()
        if not user_id:
            logger.error("無法取得用戶 ID")
            return False
        
        # 批次處理以避免 URL 過長（HTTP 414 錯誤）
        batch_size = 30  # 減少批次大小以確保順序穩定性
        total_batches = (len(song_ids) + batch_size - 1) // batch_size
        successful_batches = 0
        
        logger.info(f"將 {len(song_ids)} 首歌曲分成 {total_batches} 批次處理（每批 {batch_size} 首）")
        
        for batch_num in range(total_batches):
            start_idx = batch_num * batch_size
            end_idx = min(start_idx + batch_size, len(song_ids))
            batch_song_ids = song_ids[start_idx:end_idx]
            
            logger.info(f"處理第 {batch_num + 1}/{total_batches} 批次，包含 {len(batch_song_ids)} 首歌曲")
            logger.info(f"第 {batch_num + 1} 批次歌曲 ID 順序: {','.join(batch_song_ids[:3])}...")
            logger.info(f"第 {batch_num + 1} 批次位置範圍: {start_idx+1}-{end_idx}")
            
            params = {
                "userId": user_id,
                "ids": ",".join(batch_song_ids)
            }
            
            result = await self._make_request("POST", f"Playlists/{playlist_id}/Items", params)
            
            if result:
                successful_batches += 1
                logger.info(f"第 {batch_num + 1} 批次添加成功")
                
                # 在批次間加入小延遲以確保順序穩定（除了最後一批）
                if batch_num < total_batches - 1:
                    await asyncio.sleep(5)
                    logger.info(f"批次間延遲完成，準備處理下一批")
            else:
                logger.error(f"第 {batch_num + 1} 批次添加失敗")
                # 繼續處理下一批次，不立即返回 False
        
        # 檢查是否所有批次都成功
        if successful_batches == total_batches:
            logger.info(f"成功添加所有 {len(song_ids)} 首歌曲到播放清單: {playlist_id}")
            return True
        else:
            logger.error(f"只有 {successful_batches}/{total_batches} 批次成功，添加歌曲到播放清單部分失敗: {playlist_id}")
            return False
    
    async def remove_songs_from_playlist(self, playlist_id: str, playlist_item_ids: List[str]) -> bool:
        """從播放清單移除歌曲（支援批次處理以避免 URL 過長）
        
        Args:
            playlist_id: 播放清單 ID
            playlist_item_ids: 要移除的 PlaylistItemId 列表
            
        Returns:
            操作是否成功
        """
        logger.info(f"從播放清單移除 {len(playlist_item_ids)} 首歌曲: {playlist_id}")
        
        # 過濾掉無效的 ID
        valid_ids = [str(id).strip() for id in playlist_item_ids if id is not None and str(id).strip() != '']
        
        if not valid_ids:
            logger.warning("沒有有效的 PlaylistItemIds，跳過移除操作")
            return True
        
        # 取得認證標頭
        auth_headers = await get_auth_headers()
        if not auth_headers:
            logger.error("無法取得認證標頭")
            return False
        
        # 批次處理以避免 URL 過長（HTTP 414 錯誤）
        batch_size = 50  # 每批最多50個項目
        total_batches = (len(valid_ids) + batch_size - 1) // batch_size
        successful_batches = 0
        
        logger.info(f"將 {len(valid_ids)} 個項目分成 {total_batches} 批次移除")
        
        for batch_num in range(total_batches):
            start_idx = batch_num * batch_size
            end_idx = min(start_idx + batch_size, len(valid_ids))
            batch_ids = valid_ids[start_idx:end_idx]
            
            logger.info(f"處理第 {batch_num + 1}/{total_batches} 批次，包含 {len(batch_ids)} 個項目")
            
            # 批次移除項目（使用逗號分隔的 EntryIds）
            entry_ids_param = ",".join(batch_ids)
            params = {
                "EntryIds": entry_ids_param
            }
            
            logger.info(f"DEBUG: 第 {batch_num + 1} 批次移除項目: {entry_ids_param}")
            
            # 使用正確的 DELETE API
            delete_url = f"{self.host}/Playlists/{playlist_id}/Items"
            url_with_params = f"{delete_url}?{urlencode(params)}"
            
            logger.info(f"DEBUG: DELETE URL: {url_with_params}")
            
            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    response = await client.delete(url_with_params, headers=auth_headers)
                    logger.info(f"DEBUG: 第 {batch_num + 1} 批次 DELETE 回應狀態碼: {response.status_code}")
                    
                    if response.status_code == 204:
                        successful_batches += 1
                        logger.info(f"第 {batch_num + 1} 批次移除成功，移除了 {len(batch_ids)} 個項目")
                    else:
                        logger.error(f"第 {batch_num + 1} 批次 DELETE 失敗: {response.status_code} - {response.text}")
                        # 繼續處理下一批次，不立即返回 False
            except Exception as e:
                logger.error(f"第 {batch_num + 1} 批次 DELETE 請求異常: {str(e)}")
                # 繼續處理下一批次，不立即返回 False
        
        # 檢查是否所有批次都成功
        if successful_batches == total_batches:
            logger.info(f"成功移除所有 {len(valid_ids)} 個項目")
            return True
        else:
            logger.error(f"只有 {successful_batches}/{total_batches} 批次成功，移除項目部分失敗")
            return False
    
    async def clear_playlist(self, playlist_id: str) -> bool:
        """清空播放清單中的所有項目
        
        使用正確的流程：
        1. 透過 GET /Playlists/{playlist_id}/Items 取得所有 PlaylistItemId
        2. 透過 DELETE /Playlists/{playlist_id}/Items?EntryIds={PlaylistItemIds} 一次性刪除
        
        Args:
            playlist_id: 播放清單 ID
            
        Returns:
            操作是否成功
        """
        logger.info(f"清空播放清單: {playlist_id}")
        
        try:
            # 步驟1: 取得播放清單中所有項目的 PlaylistItemId
            playlist_items = await self.get_playlist_items(playlist_id)
            
            if not playlist_items:
                logger.info(f"播放清單 {playlist_id} 已經是空的")
                return True
            
            # 收集所有 PlaylistItemId
            playlist_item_ids = []
            for item in playlist_items:
                playlist_item_id = item.get('PlaylistItemId')
                if playlist_item_id:
                    playlist_item_ids.append(str(playlist_item_id))
            
            if not playlist_item_ids:
                logger.warning(f"播放清單 {playlist_id} 中沒有找到有效的 PlaylistItemId")
                return True
            
            logger.info(f"找到 {len(playlist_item_ids)} 個 PlaylistItemId: {playlist_item_ids}")
            
            # 步驟2: 使用 remove_songs_from_playlist 方法批次刪除
            return await self.remove_songs_from_playlist(playlist_id, playlist_item_ids)
                    
        except Exception as e:
            logger.error(f"清空播放清單時發生異常: {str(e)}")
            return False
    
    async def update_playlist(self, playlist_id: str, name: str = None, description: str = None) -> bool:
        """更新播放清單資訊
        
        Args:
            playlist_id: 播放清單 ID
            name: 新的播放清單名稱（可選）
            description: 新的播放清單描述（可選）
            
        Returns:
            操作是否成功
        """
        logger.info(f"更新播放清單: {playlist_id}")
        
        # 取得用戶 ID
        user_id = await get_authenticated_user_id()
        if not user_id:
            logger.error("無法取得用戶 ID")
            return False
        
        # 先取得現有的播放清單資訊
        current_playlist = await self.get_playlist_by_id(playlist_id)
        if not current_playlist:
            logger.error(f"無法取得播放清單資訊進行更新: {playlist_id}")
            return False
        
        data = {
            "Id": playlist_id,
            "Name": name if name is not None else current_playlist.get("Name"),
            "Overview": description if description is not None else current_playlist.get("Overview", ""),
            "UserId": user_id
        }
        
        result = await self._make_request("POST", f"Items/{playlist_id}", data=data)
        
        if result:
            logger.info(f"成功更新播放清單: {playlist_id}")
            return True
        
        logger.error(f"更新播放清單失敗: {playlist_id}")
        return False
    
    async def delete_playlist(self, playlist_id: str) -> bool:
        """刪除播放清單
        
        Args:
            playlist_id: 播放清單 ID
            
        Returns:
            操作是否成功
        """
        logger.info(f"刪除播放清單: {playlist_id}")
        
        result = await self._make_request("DELETE", f"Items/{playlist_id}")
        
        if result:
            logger.info(f"成功刪除播放清單: {playlist_id}")
            return True
        
        logger.error(f"刪除播放清單失敗: {playlist_id}")
        return False
    
    async def move_playlist_item(self, playlist_id: str, entry_id: str, new_index: int) -> bool:
        """移動播放清單中項目的位置
        
        Args:
            playlist_id: 播放清單 ID
            entry_id: 播放清單項目 ID
            new_index: 新的位置索引
            
        Returns:
            操作是否成功
        """
        logger.info(f"移動播放清單項目: {playlist_id}, 項目: {entry_id}, 新位置: {new_index}")
        
        # 取得用戶 ID
        user_id = await get_authenticated_user_id()
        if not user_id:
            logger.error("無法取得用戶 ID")
            return False
        
        params = {
            "entryId": entry_id,
            "newIndex": new_index,
            "userId": user_id
        }
        
        result = await self._make_request("POST", f"Playlists/{playlist_id}/Items/{entry_id}/Move/{new_index}", params)
        
        if result:
            logger.info(f"成功移動播放清單項目: {entry_id}")
            return True
        
        logger.error(f"移動播放清單項目失敗: {entry_id}")
        return False
    
    def _format_playlist_info(self, item: Dict) -> Dict:
        """格式化播放清單資訊
        
        Args:
            item: Jellyfin 回傳的項目資訊
            
        Returns:
            格式化後的播放清單資訊
        """
        return {
            "Id": item.get("Id"),
            "Name": item.get("Name"),
            "Overview": item.get("Overview", ""),  # 播放清單描述
            "ChildCount": item.get("RecursiveItemCount", 0),  # 歌曲數量
            "RunTimeTicks": item.get("RunTimeTicks"),  # 總播放時間
            "DateCreated": item.get("DateCreated"),
            "DateLastMediaAdded": item.get("DateLastMediaAdded"),
            "IsFolder": item.get("IsFolder", False),
            "Type": item.get("Type"),
            "CollectionType": item.get("CollectionType"),
            "ImageTags": item.get("ImageTags", {}),
            "BackdropImageTags": item.get("BackdropImageTags", []),
            "ServerId": item.get("ServerId"),
            "CanDelete": item.get("CanDelete", False),
            "CanDownload": item.get("CanDownload", False),
            "UserData": item.get("UserData", {}),
            "PlayAccess": item.get("PlayAccess"),
            "RemoteTrailers": item.get("RemoteTrailers", [])
        }
    
    def _format_song_info(self, item: Dict) -> Dict:
        """格式化歌曲資訊（與 songs.py 中的方法相同）
        
        Args:
            item: Jellyfin 回傳的項目資訊
            
        Returns:
            格式化後的歌曲資訊
        """
        return {
            "Id": item.get("Id"),
            "PlaylistItemId": item.get("PlaylistItemId"),  # 播放清單項目 ID，用於移除時使用
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
            "MediaStreams": item.get("MediaStreams", []),
            "ImageTags": item.get("ImageTags", {}),
            "BackdropImageTags": item.get("BackdropImageTags", []),
            "LocationType": item.get("LocationType")
        }


# 創建全域實例
try:
    jellyfin_playlists = JellyfinPlaylistsClient()
except ValueError as e:
    logger.error(f"初始化 Jellyfin Playlists Client 失敗: {e}")
    jellyfin_playlists = None


# 便捷函數
async def get_playlists() -> List[Dict]:
    """取得播放清單的便捷函數"""
    if not jellyfin_playlists:
        logger.error("Jellyfin Playlists Client 未初始化")
        return []
    return await jellyfin_playlists.get_playlists()


async def search_playlists(query: str, limit: int = 50) -> List[Dict]:
    """搜尋播放清單的便捷函數"""
    if not jellyfin_playlists:
        logger.error("Jellyfin Playlists Client 未初始化")
        return []
    return await jellyfin_playlists.search_playlists(query, limit)


async def get_playlist_by_id(playlist_id: str) -> Optional[Dict]:
    """取得播放清單資訊的便捷函數"""
    if not jellyfin_playlists:
        logger.error("Jellyfin Playlists Client 未初始化")
        return None
    return await jellyfin_playlists.get_playlist_by_id(playlist_id)


async def get_playlist_items(playlist_id: str, limit: int = 1000) -> List[Dict]:
    """取得播放清單歌曲的便捷函數"""
    if not jellyfin_playlists:
        logger.error("Jellyfin Playlists Client 未初始化")
        return []
    return await jellyfin_playlists.get_playlist_items(playlist_id, limit)


async def create_playlist(name: str, description: str = "", song_ids: List[str] = None) -> Optional[str]:
    """建立播放清單的便捷函數"""
    if not jellyfin_playlists:
        logger.error("Jellyfin Playlists Client 未初始化")
        return None
    return await jellyfin_playlists.create_playlist(name, description, song_ids)


async def add_songs_to_playlist(playlist_id: str, song_ids: List[str]) -> bool:
    """添加歌曲到播放清單的便捷函數"""
    if not jellyfin_playlists:
        logger.error("Jellyfin Playlists Client 未初始化")
        return False
    return await jellyfin_playlists.add_songs_to_playlist(playlist_id, song_ids)


async def remove_songs_from_playlist(playlist_id: str, entry_ids: List[str]) -> bool:
    """從播放清單移除歌曲的便捷函數"""
    if not jellyfin_playlists:
        logger.error("Jellyfin Playlists Client 未初始化")
        return False
    return await jellyfin_playlists.remove_songs_from_playlist(playlist_id, entry_ids)


async def clear_playlist(playlist_id: str) -> bool:
    """清空播放清單的便捷函數"""
    if not jellyfin_playlists:
        logger.error("Jellyfin Playlists Client 未初始化")
        return False
    return await jellyfin_playlists.clear_playlist(playlist_id)


async def update_playlist(playlist_id: str, name: str = None, description: str = None) -> bool:
    """更新播放清單的便捷函數"""
    if not jellyfin_playlists:
        logger.error("Jellyfin Playlists Client 未初始化")
        return False
    return await jellyfin_playlists.update_playlist(playlist_id, name, description)


async def delete_playlist(playlist_id: str) -> bool:
    """刪除播放清單的便捷函數"""
    if not jellyfin_playlists:
        logger.error("Jellyfin Playlists Client 未初始化")
        return False
    return await jellyfin_playlists.delete_playlist(playlist_id)
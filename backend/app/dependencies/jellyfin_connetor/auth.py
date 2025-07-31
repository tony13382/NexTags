import httpx
import asyncio
from typing import Dict, Optional, Any
from urllib.parse import urlencode
from datetime import datetime, timedelta

from app.dependencies.logger import logger
from config import JELLYFIN_HOST, JELLYFIN_API_KEY, JELLYFIN_USER_NAME, JELLYFIN_USER_PW


class JellyfinAuthClient:
    """Jellyfin 認證客戶端，負責 Access Token 的取得和管理"""
    
    def __init__(self):
        self.host = JELLYFIN_HOST
        self.api_key = JELLYFIN_API_KEY
        self.username = JELLYFIN_USER_NAME
        self.password = JELLYFIN_USER_PW
        self.base_url = f"{self.host}"  # 不使用 /emby 前綴
        
        # Access Token 相關資訊
        self.access_token: Optional[str] = None
        self.user_id: Optional[str] = None
        self.token_expires_at: Optional[datetime] = None
        
        if not all([self.host, self.api_key, self.username, self.password]):
            raise ValueError("Jellyfin 認證配置不完整：需要 JELLYFIN_HOST, JELLYFIN_API_KEY, JELLYFIN_USER_NAME, JELLYFIN_USER_PW")
    
    async def authenticate(self) -> bool:
        """取得 Access Token
        
        使用 API Key 和使用者帳密進行認證，取得 Access Token
        
        Returns:
            認證是否成功
        """
        logger.info(f"開始認證用戶: {self.username}")
        
        # 建構認證 URL
        auth_url = f"{self.base_url}/Users/AuthenticateByName"
        
        # Authorization header
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'MediaBrowser Client="PlaylistSyncer", Device="shell", DeviceId="abcdef", Version="0.0.1", ApiKey="{self.api_key}"'
        }
        
        # 認證資料
        auth_data = {
            "Username": self.username,
            "Pw": self.password
        }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                logger.info(f"發送認證請求到: {auth_url}")
                logger.info(f"認證標頭: {headers['Authorization']}")
                
                response = await client.post(auth_url, headers=headers, json=auth_data)
                
                logger.info(f"認證回應狀態碼: {response.status_code}")
                logger.info(f"認證回應內容: {response.text}")
                
                response.raise_for_status()
                result = response.json()
                
                # 檢查回應格式
                if "AccessToken" in result and "User" in result:
                    self.access_token = result["AccessToken"]
                    self.user_id = result["User"]["Id"]
                    
                    # 設定 token 過期時間（假設 24 小時）
                    self.token_expires_at = datetime.now() + timedelta(hours=24)
                    
                    logger.info(f"認證成功！用戶 ID: {self.user_id}")
                    logger.info(f"Access Token: {self.access_token[:20]}...")
                    return True
                else:
                    logger.error(f"認證回應格式異常: {result}")
                    return False
                    
        except httpx.HTTPStatusError as e:
            logger.error(f"認證 HTTP 錯誤: {e.response.status_code} - {e.response.text}")
            return False
        except httpx.RequestError as e:
            logger.error(f"認證請求錯誤: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"認證未知錯誤: {str(e)}")
            return False
    
    async def ensure_authenticated(self) -> bool:
        """確保已認證
        
        檢查 Access Token 是否有效，如果沒有或過期則重新認證
        
        Returns:
            是否已成功認證
        """
        # 檢查是否需要重新認證
        if not self.access_token or not self.user_id:
            logger.info("沒有 Access Token，需要重新認證")
            return await self.authenticate()
        
        # 檢查 token 是否過期
        if self.token_expires_at and datetime.now() >= self.token_expires_at:
            logger.info("Access Token 已過期，需要重新認證")
            return await self.authenticate()
        
        logger.info("Access Token 仍然有效")
        return True
    
    def get_auth_headers(self) -> Dict[str, str]:
        """取得認證標頭
        
        Returns:
            包含 Access Token 的認證標頭
        """
        if not self.access_token:
            raise ValueError("尚未取得 Access Token，請先呼叫 ensure_authenticated()")
        
        return {
            'Authorization': f'MediaBrowser Client="PlaylistSyncer", Device="shell", DeviceId="abcdef", Version="0.0.1", Token="{self.access_token}"'
        }
    
    def get_access_token(self) -> Optional[str]:
        """取得 Access Token
        
        Returns:
            Access Token 或 None
        """
        return self.access_token
    
    def get_user_id(self) -> Optional[str]:
        """取得用戶 ID
        
        Returns:
            用戶 ID 或 None
        """
        return self.user_id


# 創建全域認證實例
try:
    jellyfin_auth = JellyfinAuthClient()
except ValueError as e:
    logger.error(f"初始化 Jellyfin Auth Client 失敗: {e}")
    jellyfin_auth = None


# 便捷函數
async def get_access_token() -> Optional[str]:
    """取得 Access Token 的便捷函數"""
    if not jellyfin_auth:
        logger.error("Jellyfin Auth Client 未初始化")
        return None
    
    success = await jellyfin_auth.ensure_authenticated()
    if success:
        return jellyfin_auth.get_access_token()
    return None


async def get_authenticated_user_id() -> Optional[str]:
    """取得已認證用戶 ID 的便捷函數"""
    if not jellyfin_auth:
        logger.error("Jellyfin Auth Client 未初始化")
        return None
    
    success = await jellyfin_auth.ensure_authenticated()
    if success:
        return jellyfin_auth.get_user_id()
    return None


async def get_auth_headers() -> Optional[Dict[str, str]]:
    """取得認證標頭的便捷函數"""
    if not jellyfin_auth:
        logger.error("Jellyfin Auth Client 未初始化")
        return None
    
    success = await jellyfin_auth.ensure_authenticated()
    if success:
        return jellyfin_auth.get_auth_headers()
    return None
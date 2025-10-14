from fastapi import APIRouter, HTTPException
from typing import List
from app.router.config import get_config

router = APIRouter(prefix="/tags", tags=["tags"])

@router.get("/tags")
async def get_supported_tags() -> List[str]:
    """獲取支援的標籤清單"""
    try:
        supported_tags = get_config('supported_tags')
        return supported_tags if supported_tags else []
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"讀取標籤清單時發生錯誤: {str(e)}")

@router.get("/languages")
async def get_supported_languages() -> dict:
    """獲取支援的語言清單"""
    try:
        supported_languages = get_config('supported_languages')
        return supported_languages if supported_languages else {}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"讀取語言清單時發生錯誤: {str(e)}")

@router.get("/baseFolders")
async def get_base_folders() -> List[str]:
    """獲取允許的基礎資料夾清單"""
    try:
        allow_folders = get_config('allow_folders')
        return allow_folders if allow_folders else []
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"讀取資料夾清單時發生錯誤: {str(e)}")
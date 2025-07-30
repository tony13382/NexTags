from fastapi import APIRouter, HTTPException
import os
import yaml
from typing import List

router = APIRouter(prefix="/tags", tags=["tags"])

def load_config():
    """載入 config.yaml 設定檔"""
    config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'config.yaml')
    with open(config_path, 'r', encoding='utf-8') as file:
        return yaml.safe_load(file)

@router.get("/tags")
async def get_supported_tags() -> List[str]:
    """獲取支援的標籤清單"""
    try:
        config = load_config()
        supported_tags = config.get('supported_tags', [])
        return supported_tags
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="config.yaml 檔案不存在")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"讀取標籤清單時發生錯誤: {str(e)}")

@router.get("/languages")
async def get_supported_languages() -> List[str]:
    """獲取支援的語言清單"""
    try:
        config = load_config()
        supported_languages = config.get('supported_languages', {})
        # 回傳語言代碼清單 (key)
        return list(supported_languages.keys())
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="config.yaml 檔案不存在")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"讀取語言清單時發生錯誤: {str(e)}")
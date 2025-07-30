from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse
import os
import mimetypes

router = APIRouter(prefix="/images", tags=["images"])

@router.get("/cover")
async def get_cover_image(path: str = Query(..., description="圖片檔案完整路徑")):
    """獲取封面圖片檔案"""
    try:
        # 檢查檔案是否存在
        if not os.path.exists(path):
            raise HTTPException(status_code=404, detail="圖片檔案不存在")
        
        # 檢查是否為檔案
        if not os.path.isfile(path):
            raise HTTPException(status_code=400, detail="路徑不是檔案")
        
        # 檢查檔案類型
        mime_type, _ = mimetypes.guess_type(path)
        if not mime_type or not mime_type.startswith('image/'):
            raise HTTPException(status_code=400, detail="檔案不是圖片格式")
        
        # 回傳圖片檔案
        return FileResponse(
            path=path,
            media_type=mime_type,
            headers={"Cache-Control": "public, max-age=3600"}  # 快取1小時
        )
        
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=f"讀取圖片時發生錯誤: {str(e)}")
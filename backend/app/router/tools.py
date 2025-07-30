from fastapi import APIRouter, HTTPException
from app.schemas.tools import LyricPressRequest, LyricPressResponse, TextPressRequest, TextPressResponse
from app.dependencies.text_process import convertPinyin
from app.dependencies.lrc_process import lrc_process

router = APIRouter(prefix="/tools", tags=["tools"])

@router.post("/pinyin", response_model=TextPressResponse)
async def pinyin_text(request: TextPressRequest):
    """獲取音訊檔案的標籤信息"""
    try:
        return TextPressResponse(
            pure_text= request.text,
            result=convertPinyin(request.text)
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"轉換拼音發生錯誤: {str(e)}")
    

@router.post("/lyric", response_model=LyricPressResponse)
async def lyric_tools(req: LyricPressRequest):
    try:
        return LyricPressResponse(
            result=lrc_process(req.lyric)
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"轉換歌詞發生錯誤: {str(e)}")
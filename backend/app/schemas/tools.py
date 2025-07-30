from pydantic import BaseModel


class TextPressRequest(BaseModel):
    text : str


class TextPressResponse(BaseModel):
    pure_text : str
    result : str


class LyricPressRequest(BaseModel):
    lyric : str


class LyricPressResponse(BaseModel):
    result : str
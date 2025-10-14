from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, List, Union

class SmartPlaylist(BaseModel):
    """智慧播放清單資料模型"""
    id: int = Field(..., description="播放清單 ID")
    name: str = Field(..., description="播放清單名稱")
    base_folder: str = Field(..., description="基礎資料夾路徑")
    filter_tags: List[str] = Field(default_factory=list, description="標籤過濾條件")
    filter_language: Optional[str] = Field(None, description="語言過濾條件")
    filter_favorites: Optional[bool] = Field(None, description="我的最愛過濾條件")
    sort_method: str = Field("creation_time", description="排序方式: creation_time 或 title (titlesort)")

    # 新增完整顯示資訊
    filter_tags_display: List[str] = Field(default_factory=list, description="標籤顯示名稱")
    filter_language_display: Optional[str] = Field(None, description="語言顯示名稱")
    filter_favorites_display: Optional[str] = Field(None, description="我的最愛顯示名稱")
    sort_method_display: str = Field("檔案建立時間", description="排序方式顯示名稱")

class SmartPlaylistCreate(BaseModel):
    """創建智慧播放清單請求模型"""
    name: str = Field(..., min_length=1, max_length=100, description="播放清單名稱")
    base_folder: str = Field(..., min_length=1, description="基礎資料夾路徑")
    filter_tags: List[str] = Field(default_factory=list, description="標籤過濾條件")
    filter_language: Optional[str] = Field(None, description="語言過濾條件 (例如: chi, eng, kor)")
    filter_favorites: Optional[bool] = Field(None, description="我的最愛過濾條件")
    sort_method: str = Field("creation_time", description="排序方式: creation_time 或 title (titlesort)")

class SmartPlaylistUpdate(BaseModel):
    """更新智慧播放清單請求模型"""
    name: Optional[str] = Field(None, min_length=1, max_length=100, description="播放清單名稱")
    base_folder: Optional[str] = Field(None, min_length=1, description="基礎資料夾路徑")
    filter_tags: Optional[List[str]] = Field(None, description="標籤過濾條件")
    filter_language: Optional[str] = Field(None, description="語言過濾條件 (例如: chi, eng, kor)")
    filter_favorites: Optional[bool] = Field(None, description="我的最愛過濾條件")
    sort_method: Optional[str] = Field(None, description="排序方式: creation_time 或 title (titlesort)")

class SmartPlaylistResponse(BaseModel):
    """智慧播放清單響應模型"""
    success: bool = Field(..., description="操作是否成功")
    message: str = Field(..., description="響應訊息")
    data: Optional[Union[List[SmartPlaylist], SmartPlaylist]] = Field(None, description="播放清單資料")
    total_count: Optional[int] = Field(None, description="總數量")

class PlaylistSongsResponse(BaseModel):
    """播放清單歌曲清單響應模型"""
    success: bool = Field(..., description="操作是否成功")
    message: str = Field(..., description="響應訊息")
    playlist_name: str = Field(..., description="播放清單名稱")
    playlist_index: int = Field(..., description="播放清單索引")
    filter_summary: Dict[str, Any] = Field(..., description="過濾條件摘要")
    songs: List[str] = Field(..., description="符合條件的歌曲路徑清單")
    total_count: int = Field(..., description="歌曲總數")

class ErrorResponse(BaseModel):
    """錯誤響應模型"""
    success: bool = Field(False, description="操作是否成功")
    message: str = Field(..., description="錯誤訊息")
    error_code: Optional[str] = Field(None, description="錯誤代碼")
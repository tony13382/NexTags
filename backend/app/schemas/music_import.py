from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from enum import Enum

class ImportStatus(str, Enum):
    UPLOADED = "uploaded"
    CONVERTED = "converted" 
    TAGS_EXTRACTED = "tags_extracted"
    TAGS_EDITED = "tags_edited"
    ARTIST_READY = "artist_ready"
    ALBUM_READY = "album_ready"
    READY_TO_MOVE = "ready_to_move"
    COMPLETED = "completed"
    FAILED = "failed"

class AudioFormat(str, Enum):
    M4A = "m4a"
    MP3 = "mp3"
    FLAC = "flac"
    OGG = "ogg"

class FileUploadRequest(BaseModel):
    base_folder: str  # 目標 basefolder (純音樂/人聲/民歌)

class FileUploadResponse(BaseModel):
    success: bool
    message: str
    file_id: str  # 用於追蹤檔案的唯一ID
    original_filename: str
    temp_path: str
    format: AudioFormat
    needs_conversion: bool

class ConvertFileRequest(BaseModel):
    file_id: str

class ConvertFileResponse(BaseModel):
    success: bool
    message: str
    converted_path: str
    original_format: AudioFormat
    target_format: AudioFormat

class ExtractTagsRequest(BaseModel):
    file_id: str

class ExtractTagsResponse(BaseModel):
    success: bool
    message: str
    tags: Dict[str, Any]
    suggested_filename: str  # 建議的檔案名稱

class UpdateTagsRequest(BaseModel):
    file_id: str
    tags: Dict[str, Any]

class UpdateTagsResponse(BaseModel):
    success: bool
    message: str
    updated_tags: Dict[str, Any]

class CheckArtistRequest(BaseModel):
    file_id: str
    artist_name: str

class ArtistCheckResult(BaseModel):
    artist_name: str
    artist_exists: bool
    artist_folder_path: str
    needs_artist_image: bool

class CheckArtistResponse(BaseModel):
    success: bool
    artists: List[ArtistCheckResult]
    message: str

class UploadArtistImageRequest(BaseModel):
    file_id: str
    artist_name: str

class UploadArtistImageResponse(BaseModel):
    success: bool
    message: str
    artist_image_path: str

class ProcessAlbumRequest(BaseModel):
    file_id: str
    artist_name: str
    album_name: str

class ProcessAlbumResponse(BaseModel):
    success: bool
    message: str
    album_folder_path: str
    cover_extracted: bool
    cover_path: str

class FinalizeFileRequest(BaseModel):
    file_id: str
    final_filename: str  # 最終檔案名稱 (如: "01 - Song.flac")

class FinalizeFileResponse(BaseModel):
    success: bool
    message: str
    temp_file_path: str  # WaitImport 中的路徑
    preview_final_path: str  # 預覽最終路徑

class ConfirmMoveRequest(BaseModel):
    file_id: str

class ConfirmMoveResponse(BaseModel):
    success: bool
    message: str
    final_path: str

class ImportStatusRequest(BaseModel):
    file_id: str

class ImportStatusResponse(BaseModel):
    success: bool
    file_id: str
    status: ImportStatus
    current_step: str
    next_action: Optional[str]
    file_info: Dict[str, Any]
    errors: List[str]

class ListPendingImportsResponse(BaseModel):
    success: bool
    pending_imports: List[Dict[str, Any]]
    count: int

class DeleteImportRequest(BaseModel):
    file_id: str

class DeleteImportResponse(BaseModel):
    success: bool
    message: str

class GenerateReplayGainRequest(BaseModel):
    file_id: str

class GenerateReplayGainResponse(BaseModel):
    success: bool
    message: str
    replaygain_applied: bool
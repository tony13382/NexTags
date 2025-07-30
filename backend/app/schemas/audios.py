from pydantic import BaseModel
from typing import Dict, Any, Optional, List

class AudioTagsRequest(BaseModel):
    path: str

class AudioTagsResponse(BaseModel):
    tags: Dict[str, Any]
    success: bool
    message: Optional[str] = None
    path: Optional[str] = None
    folder: Optional[str] = None

class AudioUpdateRequest(BaseModel):
    path: str
    tags: List[Dict[str, Any]]

class AudioUpdateResponse(BaseModel):
    success: bool
    message: Optional[str] = None
    updated_tags: Optional[Dict[str, Any]] = None
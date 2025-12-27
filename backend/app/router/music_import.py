import os
import uuid
import shutil
from datetime import datetime
from typing import Dict, Any, List
from pathlib import Path

from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from fastapi.responses import FileResponse

from app.schemas.music_import import (
    FileUploadRequest, FileUploadResponse, ConvertFileRequest, ConvertFileResponse,
    ExtractTagsRequest, ExtractTagsResponse, UpdateTagsRequest, UpdateTagsResponse,
    CheckArtistRequest, CheckArtistResponse, ArtistCheckResult, UploadArtistImageRequest, UploadArtistImageResponse,
    ProcessAlbumRequest, ProcessAlbumResponse, FinalizeFileRequest, FinalizeFileResponse,
    ConfirmMoveRequest, ConfirmMoveResponse, ImportStatusRequest, ImportStatusResponse,
    ListPendingImportsResponse, DeleteImportRequest, DeleteImportResponse,
    GenerateReplayGainRequest, GenerateReplayGainResponse,
    ImportStatus, AudioFormat
)
from app.dependencies.mp3tag_reader import read_audio_tags
from app.dependencies.mp3tag_writer import write_tags
from app.dependencies.utils.audio_converter import convert_to_flac
from app.dependencies.utils.cover_art import save_cover_art, extract_cover_from_audio
from app.dependencies.utils.replaygain import generate_replaygain
from app.dependencies.logger import logger

router = APIRouter(prefix="/music-import", tags=["music-import"])

# 全局變數來追蹤匯入狀態
import_sessions: Dict[str, Dict[str, Any]] = {}

def get_music_base_path() -> str:
    """取得音樂根目錄路徑"""
    return os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), 'Music')

def get_wait_import_path() -> str:
    """取得 WaitImport 目錄路徑"""
    wait_import_path = os.path.join(get_music_base_path(), 'WaitImport')
    os.makedirs(wait_import_path, exist_ok=True)
    return wait_import_path

def get_supported_formats() -> List[str]:
    """取得支援的音訊格式"""
    return ['.mp3', '.flac', '.ogg', '.m4a']

def needs_conversion(file_extension: str) -> bool:
    """判斷檔案是否需要轉換"""
    return file_extension.lower() == '.m4a'

def generate_file_id() -> str:
    """產生檔案追蹤ID"""
    return str(uuid.uuid4())

def get_file_format(filename: str) -> AudioFormat:
    """根據檔案名稱判斷音訊格式"""
    extension = os.path.splitext(filename)[1].lower()
    if extension == '.m4a':
        return AudioFormat.M4A
    elif extension == '.mp3':
        return AudioFormat.MP3
    elif extension == '.flac':
        return AudioFormat.FLAC
    elif extension == '.ogg':
        return AudioFormat.OGG
    else:
        raise ValueError(f"不支援的音訊格式: {extension}")

def update_import_status(file_id: str, status: ImportStatus, **kwargs):
    """更新匯入狀態"""
    if file_id not in import_sessions:
        import_sessions[file_id] = {
            'created_at': datetime.now(),
            'status': status,
            'errors': []
        }
    else:
        import_sessions[file_id]['status'] = status
    
    # 更新額外資訊
    for key, value in kwargs.items():
        import_sessions[file_id][key] = value
    
    import_sessions[file_id]['updated_at'] = datetime.now()

@router.post("/upload", response_model=FileUploadResponse)
async def upload_music_file(
    file: UploadFile = File(...),
    base_folder: str = Form(...)
):
    """上傳音樂檔案到 WaitImport 資料夾"""
    try:
        # 驗證檔案格式
        if not file.filename:
            raise HTTPException(status_code=400, detail="檔案名稱不能為空")
        
        file_extension = os.path.splitext(file.filename)[1]
        if file_extension.lower() not in get_supported_formats():
            raise HTTPException(
                status_code=400, 
                detail=f"不支援的檔案格式: {file_extension}。支援格式: {', '.join(get_supported_formats())}"
            )
        
        # 驗證 base_folder
        from app.router.config import get_config
        allow_folders = get_config('allow_folders') or []

        if base_folder not in allow_folders:
            raise HTTPException(status_code=400, detail=f"不支援的目標資料夾: {base_folder}")
        
        # 產生檔案ID和暫存路徑
        file_id = generate_file_id()
        wait_import_path = get_wait_import_path()
        temp_filename = f"{file_id}_{file.filename}"
        temp_file_path = os.path.join(wait_import_path, temp_filename)
        
        # 儲存檔案到 WaitImport
        with open(temp_file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
        
        # 判斷檔案格式和是否需要轉換
        audio_format = get_file_format(file.filename)
        needs_conv = needs_conversion(file_extension)
        
        # 更新匯入狀態
        update_import_status(
            file_id,
            ImportStatus.UPLOADED,
            original_filename=file.filename,
            temp_path=temp_file_path,
            base_folder=base_folder,
            format=audio_format.value,
            needs_conversion=needs_conv,
            file_size=len(content)
        )
        
        logger.info(f"檔案上傳成功: {file.filename} -> {temp_file_path}")
        
        return FileUploadResponse(
            success=True,
            message="檔案上傳成功",
            file_id=file_id,
            original_filename=file.filename,
            temp_path=temp_file_path,
            format=audio_format,
            needs_conversion=needs_conv
        )
        
    except Exception as e:
        logger.error(f"檔案上傳失敗: {str(e)}")
        raise HTTPException(status_code=500, detail=f"檔案上傳失敗: {str(e)}")

@router.post("/convert", response_model=ConvertFileResponse)
async def convert_audio_file(request: ConvertFileRequest):
    """轉換音訊檔案格式 (.m4a -> .flac)"""
    try:
        if request.file_id not in import_sessions:
            raise HTTPException(status_code=404, detail="找不到檔案ID")
        
        session = import_sessions[request.file_id]
        temp_path = session.get('temp_path')
        
        if not temp_path or not os.path.exists(temp_path):
            raise HTTPException(status_code=404, detail="暫存檔案不存在")
        
        # 檢查是否需要轉換
        if not session.get('needs_conversion', False):
            raise HTTPException(status_code=400, detail="此檔案不需要轉換")
        
        # 產生轉換後的檔案路徑
        original_format = AudioFormat(session.get('format'))
        if original_format != AudioFormat.M4A:
            raise HTTPException(status_code=400, detail="只支援 .m4a 轉換為 .flac")
        
        converted_filename = os.path.splitext(os.path.basename(temp_path))[0] + '.flac'
        converted_path = os.path.join(os.path.dirname(temp_path), converted_filename)
        
        # 先讀取原始檔案的標籤
        original_tags = read_audio_tags(temp_path)
        
        # 轉換檔案
        success = convert_to_flac(temp_path, converted_path, original_tags)
        
        if not success:
            raise HTTPException(status_code=500, detail="音訊轉換失敗")
        
        # 刪除原始檔案
        os.remove(temp_path)
        
        # 更新匯入狀態
        update_import_status(
            request.file_id,
            ImportStatus.CONVERTED,
            temp_path=converted_path,
            format=AudioFormat.FLAC.value,
            needs_conversion=False,
            converted_from=original_format.value
        )
        
        logger.info(f"檔案轉換成功: {temp_path} -> {converted_path}")
        
        return ConvertFileResponse(
            success=True,
            message="檔案轉換成功",
            converted_path=converted_path,
            original_format=original_format,
            target_format=AudioFormat.FLAC
        )
        
    except Exception as e:
        logger.error(f"檔案轉換失敗: {str(e)}")
        if request.file_id in import_sessions:
            import_sessions[request.file_id]['errors'].append(f"轉換失敗: {str(e)}")
        raise HTTPException(status_code=500, detail=f"檔案轉換失敗: {str(e)}")

@router.post("/extract-tags", response_model=ExtractTagsResponse)
async def extract_music_tags(request: ExtractTagsRequest):
    """提取音樂檔案標籤"""
    try:
        if request.file_id not in import_sessions:
            raise HTTPException(status_code=404, detail="找不到檔案ID")

        session = import_sessions[request.file_id]
        temp_path = session.get('temp_path')

        if not temp_path or not os.path.exists(temp_path):
            raise HTTPException(status_code=404, detail="暫存檔案不存在")

        # 讀取標籤
        tags = read_audio_tags(temp_path)

        if not tags:
            raise HTTPException(status_code=500, detail="無法讀取檔案標籤")

        # 自動生成 ReplayGain
        try:
            logger.info(f"自動生成 ReplayGain: {temp_path}")
            success, message = generate_replaygain(temp_path)
            if success:
                logger.info(f"ReplayGain 生成成功: {message}")
                # 重新讀取標籤以獲取 ReplayGain 值
                tags = read_audio_tags(temp_path)
                import_sessions[request.file_id]['replaygain_applied'] = True
            else:
                logger.warning(f"ReplayGain 生成失敗（非致命錯誤）: {message}")
                import_sessions[request.file_id]['replaygain_applied'] = False
        except Exception as rg_error:
            logger.warning(f"ReplayGain 生成失敗（非致命錯誤）: {str(rg_error)}")
            import_sessions[request.file_id]['replaygain_applied'] = False

        # 生成建議的檔案名稱
        track_num = tags.get('tracknumber', '1')
        title = tags.get('title', '未知標題')

        # 格式化軌道編號
        if isinstance(track_num, list):
            track_num = track_num[0] if track_num else '1'
        track_num = str(track_num).split('/')[0].zfill(2)  # 取得軌道編號並補零

        suggested_filename = f"{track_num} - {title}.{session.get('format', 'flac')}"

        # 更新匯入狀態
        update_import_status(
            request.file_id,
            ImportStatus.TAGS_EXTRACTED,
            extracted_tags=tags,
            suggested_filename=suggested_filename
        )

        logger.info(f"標籤提取成功: {temp_path}")

        return ExtractTagsResponse(
            success=True,
            message="標籤提取成功",
            tags=tags,
            suggested_filename=suggested_filename
        )

    except Exception as e:
        logger.error(f"標籤提取失敗: {str(e)}")
        if request.file_id in import_sessions:
            import_sessions[request.file_id]['errors'].append(f"標籤提取失敗: {str(e)}")
        raise HTTPException(status_code=500, detail=f"標籤提取失敗: {str(e)}")

@router.post("/update-tags", response_model=UpdateTagsResponse)
async def update_music_tags(request: UpdateTagsRequest):
    """更新音樂檔案標籤"""
    try:
        if request.file_id not in import_sessions:
            raise HTTPException(status_code=404, detail="找不到檔案ID")
        
        session = import_sessions[request.file_id]
        temp_path = session.get('temp_path')
        
        if not temp_path or not os.path.exists(temp_path):
            raise HTTPException(status_code=404, detail="暫存檔案不存在")
        
        # 寫入標籤
        success = write_tags(temp_path, request.tags)
        
        if not success:
            raise HTTPException(status_code=500, detail="標籤更新失敗")
        
        # 更新匯入狀態
        update_import_status(
            request.file_id,
            ImportStatus.TAGS_EDITED,
            updated_tags=request.tags
        )
        
        logger.info(f"標籤更新成功: {temp_path}")
        
        return UpdateTagsResponse(
            success=True,
            message="標籤更新成功",
            updated_tags=request.tags
        )
        
    except Exception as e:
        logger.error(f"標籤更新失敗: {str(e)}")
        if request.file_id in import_sessions:
            import_sessions[request.file_id]['errors'].append(f"標籤更新失敗: {str(e)}")
        raise HTTPException(status_code=500, detail=f"標籤更新失敗: {str(e)}")

@router.get("/status", response_model=ImportStatusResponse)
async def get_import_status(file_id: str):
    """取得匯入狀態"""
    try:
        if file_id not in import_sessions:
            raise HTTPException(status_code=404, detail="找不到檔案ID")
        
        session = import_sessions[file_id]
        
        # 判斷下一步動作
        status = session.get('status')
        next_action = None
        
        if status == ImportStatus.UPLOADED:
            if session.get('needs_conversion'):
                next_action = "convert"
            else:
                next_action = "extract-tags"
        elif status == ImportStatus.CONVERTED:
            next_action = "extract-tags"
        elif status == ImportStatus.TAGS_EXTRACTED:
            next_action = "update-tags"
        elif status == ImportStatus.TAGS_EDITED:
            next_action = "check-artist"
        
        return ImportStatusResponse(
            success=True,
            file_id=file_id,
            status=status,
            current_step=status.value,
            next_action=next_action,
            file_info=session,
            errors=session.get('errors', [])
        )
        
    except Exception as e:
        logger.error(f"取得匯入狀態失敗: {str(e)}")
        raise HTTPException(status_code=500, detail=f"取得匯入狀態失敗: {str(e)}")

@router.get("/pending", response_model=ListPendingImportsResponse)
async def list_pending_imports():
    """列出 WaitImport 資料夾中的實際檔案"""
    try:
        pending_imports = []
        wait_import_path = get_wait_import_path()

        # 列出 WaitImport 資料夾中的所有檔案
        if os.path.exists(wait_import_path):
            for filename in os.listdir(wait_import_path):
                file_path = os.path.join(wait_import_path, filename)

                # 跳過目錄
                if os.path.isdir(file_path):
                    continue

                # 獲取檔案資訊
                file_stat = os.stat(file_path)
                created_at = datetime.fromtimestamp(file_stat.st_ctime)
                modified_at = datetime.fromtimestamp(file_stat.st_mtime)

                # 嘗試從檔案名稱提取 file_id 和 original_filename
                # 格式: {file_id}_{original_filename}
                file_id = None
                original_filename = filename
                status = 'unknown'
                base_folder = ''
                errors = []

                if '_' in filename:
                    parts = filename.split('_', 1)
                    potential_id = parts[0]
                    # 檢查是否為 UUID 格式
                    if len(potential_id) == 36 and potential_id.count('-') == 4:
                        file_id = potential_id
                        original_filename = parts[1]

                        # 嘗試從 import_sessions 獲取額外資訊
                        if file_id in import_sessions:
                            session = import_sessions[file_id]
                            status = session.get('status', 'unknown')
                            base_folder = session.get('base_folder', '')
                            errors = session.get('errors', [])
                        else:
                            status = 'orphaned'  # 檔案存在但沒有對應的會話
                else:
                    # 沒有 file_id 的檔案
                    file_id = filename  # 使用檔案名作為 ID
                    status = 'unknown'

                pending_imports.append({
                    'file_id': file_id or filename,
                    'original_filename': original_filename,
                    'status': status,
                    'created_at': created_at,
                    'updated_at': modified_at,
                    'base_folder': base_folder,
                    'errors': errors
                })

        # 按建立時間排序（最新的在前）
        pending_imports.sort(key=lambda x: x['created_at'], reverse=True)

        return ListPendingImportsResponse(
            success=True,
            pending_imports=pending_imports,
            count=len(pending_imports)
        )

    except Exception as e:
        logger.error(f"列出待處理匯入失敗: {str(e)}")
        raise HTTPException(status_code=500, detail=f"列出待處理匯入失敗: {str(e)}")

@router.delete("/delete", response_model=DeleteImportResponse)
async def delete_import(request: DeleteImportRequest):
    """刪除匯入任務和暫存檔案"""
    try:
        wait_import_path = get_wait_import_path()
        file_deleted = False

        # 方法1: 嘗試從 import_sessions 中查找
        if request.file_id in import_sessions:
            session = import_sessions[request.file_id]
            temp_path = session.get('temp_path')

            # 刪除暫存檔案
            if temp_path and os.path.exists(temp_path):
                os.remove(temp_path)
                file_deleted = True

            # 刪除匯入會話
            del import_sessions[request.file_id]
            logger.info(f"匯入任務刪除成功: {request.file_id}")
        else:
            # 方法2: 直接在 WaitImport 資料夾中搜尋檔案
            # 嘗試兩種模式: {file_id}_{filename} 或直接 {file_id}
            for filename in os.listdir(wait_import_path):
                file_path = os.path.join(wait_import_path, filename)

                # 跳過目錄
                if os.path.isdir(file_path):
                    continue

                # 檢查檔案名稱是否匹配
                if filename.startswith(request.file_id + '_') or filename == request.file_id:
                    os.remove(file_path)
                    file_deleted = True
                    logger.info(f"刪除 WaitImport 檔案: {filename}")
                    break

        if not file_deleted:
            raise HTTPException(status_code=404, detail="找不到要刪除的檔案")

        return DeleteImportResponse(
            success=True,
            message="檔案已刪除"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"刪除匯入任務失敗: {str(e)}")
        raise HTTPException(status_code=500, detail=f"刪除匯入任務失敗: {str(e)}")

@router.post("/check-artist", response_model=CheckArtistResponse)
async def check_artist_folder(request: CheckArtistRequest):
    """檢查歌手資料夾是否存在，支援多歌手"""
    try:
        if request.file_id not in import_sessions:
            raise HTTPException(status_code=404, detail="找不到檔案ID")

        session = import_sessions[request.file_id]
        base_folder = session.get('base_folder')

        if not base_folder:
            raise HTTPException(status_code=400, detail="找不到目標資料夾")

        # 解析多歌手（分號分隔）
        artist_names = [name.strip() for name in request.artist_name.split(';') if name.strip()]

        if not artist_names:
            raise HTTPException(status_code=400, detail="歌手名稱不能為空")

        music_base_path = get_music_base_path()
        artist_results = []
        overall_needs_artist_image = False

        # 檢查每個歌手
        for artist_name in artist_names:
            # 建構歌手資料夾路徑 (/Music/basefolder/Music/Artist)
            artist_folder_path = os.path.join(music_base_path, base_folder, "Music", artist_name)
            artist_exists = os.path.exists(artist_folder_path)
            needs_artist_image = False

            if artist_exists:
                # 檢查是否有歌手圖片 (artist.jpg, artist.png 等)
                artist_image_files = ['artist.jpg', 'artist.jpeg', 'artist.png']
                has_artist_image = any(
                    os.path.exists(os.path.join(artist_folder_path, img_file))
                    for img_file in artist_image_files
                )
                needs_artist_image = not has_artist_image
            else:
                needs_artist_image = True

            # 如果任何一個歌手需要圖片，則整體需要
            if needs_artist_image:
                overall_needs_artist_image = True

            artist_results.append(ArtistCheckResult(
                artist_name=artist_name,
                artist_exists=artist_exists,
                artist_folder_path=artist_folder_path,
                needs_artist_image=needs_artist_image
            ))

            logger.info(f"歌手資料夾檢查: {artist_name} - 存在: {artist_exists}, 需要圖片: {needs_artist_image}")

        # 更新匯入狀態（使用第一個歌手作為主要歌手）
        primary_artist = artist_results[0]
        update_import_status(
            request.file_id,
            ImportStatus.ARTIST_READY,
            artist_name=request.artist_name,  # 保存完整的歌手名稱（包含分隔符）
            primary_artist_name=primary_artist.artist_name,
            artist_folder_path=primary_artist.artist_folder_path,
            artist_exists=primary_artist.artist_exists,
            needs_artist_image=overall_needs_artist_image,
            all_artists=artist_results
        )

        # 生成訊息
        existing_count = sum(1 for result in artist_results if result.artist_exists)
        total_count = len(artist_results)

        if existing_count == total_count:
            message = f"所有 {total_count} 個歌手資料夾都已存在"
        elif existing_count == 0:
            message = f"需要建立 {total_count} 個歌手資料夾"
        else:
            message = f"{existing_count}/{total_count} 個歌手資料夾已存在"

        if overall_needs_artist_image:
            missing_image_count = sum(1 for result in artist_results if result.needs_artist_image)
            message += f"，需要為 {missing_image_count} 個歌手上傳圖片"

        logger.info(f"多歌手檢查完成: {message}")

        return CheckArtistResponse(
            success=True,
            artists=artist_results,
            message=message
        )

    except Exception as e:
        logger.error(f"檢查歌手資料夾失敗: {str(e)}")
        if request.file_id in import_sessions:
            import_sessions[request.file_id]['errors'].append(f"檢查歌手資料夾失敗: {str(e)}")
        raise HTTPException(status_code=500, detail=f"檢查歌手資料夾失敗: {str(e)}")

@router.post("/upload-artist-image", response_model=UploadArtistImageResponse)
async def upload_artist_image(
    file_id: str = Form(...),
    artist_name: str = Form(...),
    image: UploadFile = File(...)
):
    """上傳歌手圖片"""
    try:
        if file_id not in import_sessions:
            raise HTTPException(status_code=404, detail="找不到檔案ID")
        
        session = import_sessions[file_id]
        base_folder = session.get('base_folder')
        
        if not base_folder:
            raise HTTPException(status_code=400, detail="找不到目標資料夾")
        
        # 驗證圖片格式
        if not image.filename:
            raise HTTPException(status_code=400, detail="圖片檔案名稱不能為空")
        
        allowed_extensions = ['.jpg', '.jpeg', '.png']
        file_extension = os.path.splitext(image.filename)[1].lower()
        
        if file_extension not in allowed_extensions:
            raise HTTPException(
                status_code=400,
                detail=f"不支援的圖片格式: {file_extension}。支援格式: {', '.join(allowed_extensions)}"
            )
        
        # 建立歌手資料夾 (/Music/basefolder/Music/Artist)
        music_base_path = get_music_base_path()
        artist_folder_path = os.path.join(music_base_path, base_folder, "Music", artist_name)
        os.makedirs(artist_folder_path, exist_ok=True)
        
        # 儲存圖片為 artist.jpg
        artist_image_path = os.path.join(artist_folder_path, "artist.jpg")
        
        with open(artist_image_path, "wb") as buffer:
            content = await image.read()
            buffer.write(content)
        
        # 更新匯入狀態
        update_import_status(
            file_id,
            ImportStatus.ARTIST_READY,
            artist_image_path=artist_image_path,
            needs_artist_image=False
        )
        
        logger.info(f"歌手圖片上傳成功: {artist_image_path}")
        
        return UploadArtistImageResponse(
            success=True,
            message="歌手圖片上傳成功",
            artist_image_path=artist_image_path
        )
        
    except Exception as e:
        logger.error(f"歌手圖片上傳失敗: {str(e)}")
        if file_id in import_sessions:
            import_sessions[file_id]['errors'].append(f"歌手圖片上傳失敗: {str(e)}")
        raise HTTPException(status_code=500, detail=f"歌手圖片上傳失敗: {str(e)}")

@router.post("/process-album", response_model=ProcessAlbumResponse)
async def process_album_folder(request: ProcessAlbumRequest):
    """處理專輯資料夾和封面提取"""
    try:
        if request.file_id not in import_sessions:
            raise HTTPException(status_code=404, detail="找不到檔案ID")
        
        session = import_sessions[request.file_id]
        base_folder = session.get('base_folder')
        temp_path = session.get('temp_path')
        
        if not base_folder or not temp_path:
            raise HTTPException(status_code=400, detail="找不到必要資訊")
        
        if not os.path.exists(temp_path):
            raise HTTPException(status_code=404, detail="暫存檔案不存在")
        
        # 處理多歌手情況
        artist_names = [name.strip() for name in request.artist_name.split(';') if name.strip()]
        primary_artist = artist_names[0] if artist_names else request.artist_name

        # 建構專輯資料夾路徑 (使用主要歌手: /Music/basefolder/Music/PrimaryArtist/Album)
        music_base_path = get_music_base_path()
        album_folder_path = os.path.join(music_base_path, base_folder, "Music", primary_artist, request.album_name)

        # 建立主要歌手的專輯資料夾
        os.makedirs(album_folder_path, exist_ok=True)

        # 為多歌手創建各自的資料夾（如果不存在）
        created_artist_folders = []
        for artist_name in artist_names:
            artist_folder_path = os.path.join(music_base_path, base_folder, "Music", artist_name)
            if not os.path.exists(artist_folder_path):
                os.makedirs(artist_folder_path, exist_ok=True)
                created_artist_folders.append(artist_name)
                logger.info(f"建立歌手資料夾: {artist_folder_path}")

        if created_artist_folders:
            logger.info(f"為多歌手建立了資料夾: {created_artist_folders}")
        
        # 嘗試提取封面圖
        cover_extracted = False
        cover_path = ""
        
        try:
            # 使用新的封面提取功能
            cover_extracted, cover_path = extract_cover_from_audio(temp_path, album_folder_path)
        except Exception as cover_error:
            logger.warning(f"封面提取失敗: {str(cover_error)}")
            # 封面提取失敗不會影響整個流程
        
        # 更新匯入狀態
        update_import_status(
            request.file_id,
            ImportStatus.ALBUM_READY,
            album_name=request.album_name,
            album_folder_path=album_folder_path,
            cover_extracted=cover_extracted,
            cover_path=cover_path
        )
        
        message = f"專輯資料夾已建立: {album_folder_path}"
        if cover_extracted:
            message += f"，封面已提取: {cover_path}"
        else:
            message += "，未找到封面圖"
        
        logger.info(f"專輯處理完成: {message}")
        
        return ProcessAlbumResponse(
            success=True,
            message=message,
            album_folder_path=album_folder_path,
            cover_extracted=cover_extracted,
            cover_path=cover_path
        )
        
    except Exception as e:
        logger.error(f"專輯處理失敗: {str(e)}")
        if request.file_id in import_sessions:
            import_sessions[request.file_id]['errors'].append(f"專輯處理失敗: {str(e)}")
        raise HTTPException(status_code=500, detail=f"專輯處理失敗: {str(e)}")

@router.post("/finalize", response_model=FinalizeFileResponse)
async def finalize_file_preparation(request: FinalizeFileRequest):
    """準備檔案的最終命名和路徑"""
    try:
        if request.file_id not in import_sessions:
            raise HTTPException(status_code=404, detail="找不到檔案ID")
        
        session = import_sessions[request.file_id]
        temp_path = session.get('temp_path')
        base_folder = session.get('base_folder')
        artist_name = session.get('artist_name')
        album_name = session.get('album_name')
        
        if not all([temp_path, base_folder, artist_name, album_name]):
            raise HTTPException(status_code=400, detail="缺少必要的檔案資訊")
        
        if not os.path.exists(temp_path):
            raise HTTPException(status_code=404, detail="暫存檔案不存在")
        
        # 建構預覽的最終路徑 (/Music/basefolder/Music/Artist/Album/filename)
        music_base_path = get_music_base_path()
        preview_final_path = os.path.join(
            music_base_path, base_folder, "Music", artist_name, album_name, request.final_filename
        )
        
        # 更新匯入狀態
        update_import_status(
            request.file_id,
            ImportStatus.READY_TO_MOVE,
            final_filename=request.final_filename,
            preview_final_path=preview_final_path
        )
        
        logger.info(f"檔案已準備完成: {request.final_filename}")
        
        return FinalizeFileResponse(
            success=True,
            message="檔案已準備完成，可以確認移動",
            temp_file_path=temp_path,
            preview_final_path=preview_final_path
        )
        
    except Exception as e:
        logger.error(f"檔案準備失敗: {str(e)}")
        if request.file_id in import_sessions:
            import_sessions[request.file_id]['errors'].append(f"檔案準備失敗: {str(e)}")
        raise HTTPException(status_code=500, detail=f"檔案準備失敗: {str(e)}")

@router.post("/confirm-move", response_model=ConfirmMoveResponse)
async def confirm_file_move(request: ConfirmMoveRequest):
    """確認並執行檔案移動到最終位置"""
    try:
        if request.file_id not in import_sessions:
            raise HTTPException(status_code=404, detail="找不到檔案ID")
        
        session = import_sessions[request.file_id]
        temp_path = session.get('temp_path')
        preview_final_path = session.get('preview_final_path')
        
        if not temp_path or not preview_final_path:
            raise HTTPException(status_code=400, detail="缺少檔案路徑資訊")
        
        if not os.path.exists(temp_path):
            raise HTTPException(status_code=404, detail="暫存檔案不存在")
        
        # 確保目標目錄存在
        os.makedirs(os.path.dirname(preview_final_path), exist_ok=True)
        
        # 移動檔案
        shutil.move(temp_path, preview_final_path)
        
        # 更新匯入狀態
        update_import_status(
            request.file_id,
            ImportStatus.COMPLETED,
            final_path=preview_final_path,
            completed_at=datetime.now()
        )
        
        logger.info(f"檔案移動完成: {temp_path} -> {preview_final_path}")
        
        return ConfirmMoveResponse(
            success=True,
            message="檔案已成功移動到最終位置",
            final_path=preview_final_path
        )
        
    except Exception as e:
        logger.error(f"檔案移動失敗: {str(e)}")
        if request.file_id in import_sessions:
            import_sessions[request.file_id]['errors'].append(f"檔案移動失敗: {str(e)}")
        raise HTTPException(status_code=500, detail=f"檔案移動失敗: {str(e)}")

@router.post("/generate-replaygain", response_model=GenerateReplayGainResponse)
async def generate_replaygain_tags(request: GenerateReplayGainRequest):
    """為音訊檔案生成 ReplayGain 標籤"""
    try:
        if request.file_id not in import_sessions:
            raise HTTPException(status_code=404, detail="找不到檔案ID")

        session = import_sessions[request.file_id]
        temp_path = session.get('temp_path')

        if not temp_path or not os.path.exists(temp_path):
            raise HTTPException(status_code=404, detail="暫存檔案不存在")

        # 呼叫 r128gain 生成 ReplayGain
        success, message = generate_replaygain(temp_path)

        if success:
            # 更新匯入狀態
            import_sessions[request.file_id]['replaygain_applied'] = True
            logger.info(f"ReplayGain 生成成功: {temp_path}")

            return GenerateReplayGainResponse(
                success=True,
                message=message,
                replaygain_applied=True
            )
        else:
            raise HTTPException(status_code=500, detail=message)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"ReplayGain 生成失敗: {str(e)}")
        if request.file_id in import_sessions:
            import_sessions[request.file_id]['errors'].append(f"ReplayGain 生成失敗: {str(e)}")
        raise HTTPException(status_code=500, detail=f"ReplayGain 生成失敗: {str(e)}")
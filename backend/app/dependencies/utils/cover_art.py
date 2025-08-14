import os
from mutagen import File as MutagenFile
from mutagen.mp4 import MP4, MP4Cover
from mutagen.flac import FLAC, Picture
from mutagen.mp3 import MP3
from mutagen.id3 import APIC
from mutagen.oggvorbis import OggVorbis


def extract_cover_from_audio(file_path, output_dir):
    """從音訊檔案提取封面圖並保存為 cover.jpg 或 cover.png"""
    try:
        # 確保輸出目錄存在
        os.makedirs(output_dir, exist_ok=True)
        
        # 使用 mutagen 讀取音訊檔案
        audio_file = MutagenFile(file_path)
        
        if audio_file is None:
            return False, ""
        
        cover_data = None
        mime_type = None
        
        if isinstance(audio_file, MP4):
            # MP4/M4A 檔案
            if "covr" in audio_file.tags:
                artwork = audio_file.tags["covr"][0]
                cover_data = bytes(artwork)
                mime_type = "image/jpeg" if artwork.imageformat == MP4Cover.FORMAT_JPEG else "image/png"
                
        elif isinstance(audio_file, FLAC):
            # FLAC 檔案
            if audio_file.pictures:
                picture = audio_file.pictures[0]
                cover_data = picture.data
                mime_type = picture.mime
                
        elif isinstance(audio_file, MP3):
            # MP3 檔案
            if audio_file.tags:
                for tag in audio_file.tags.values():
                    if isinstance(tag, APIC):
                        cover_data = tag.data
                        mime_type = tag.mime
                        break
                        
        elif isinstance(audio_file, OggVorbis):
            # OGG Vorbis 檔案
            # OGG 使用 FLAC-style 圖片存儲
            if hasattr(audio_file, 'get') and audio_file.get('METADATA_BLOCK_PICTURE'):
                import base64
                try:
                    # 解碼 base64 編碼的圖片數據
                    picture_data = base64.b64decode(audio_file['METADATA_BLOCK_PICTURE'][0])
                    # 這裡需要解析 FLAC picture block，簡化處理
                    # 通常前面有一些元數據，實際圖片數據在後面
                    if len(picture_data) > 32:  # 基本的sanity check
                        # 嘗試找到 JPEG 或 PNG 頭部
                        jpeg_start = picture_data.find(b'\xff\xd8\xff')
                        png_start = picture_data.find(b'\x89PNG')
                        
                        if jpeg_start != -1:
                            cover_data = picture_data[jpeg_start:]
                            mime_type = "image/jpeg"
                        elif png_start != -1:
                            cover_data = picture_data[png_start:]
                            mime_type = "image/png"
                except Exception:
                    pass
        
        # 如果成功提取到封面數據
        if cover_data and mime_type:
            # 決定檔案副檔名
            if mime_type == "image/jpeg":
                extension = ".jpg"
            elif mime_type == "image/png":
                extension = ".png"
            else:
                extension = ".jpg"  # 默認使用 jpg
            
            cover_path = os.path.join(output_dir, "cover" + extension)
            
            # 寫入封面圖檔
            with open(cover_path, "wb") as f:
                f.write(cover_data)
            
            return True, cover_path
            
    except Exception as e:
        print(f"提取封面圖檔時發生錯誤: {str(e)}")
    
    return False, ""


def save_cover_art(mp4_file, output_dir):
    """儲存 MP4 封面圖檔（保持向後兼容）"""
    try:
        # 取得 MP4 檔案中的封面圖檔
        if "covr" in mp4_file.tags:
            artwork = mp4_file.tags["covr"][0]
            # 根據封面圖檔的格式決定副檔名
            extension = (
                ".jpg" if artwork.imageformat == MP4Cover.FORMAT_JPEG else ".png"
            )
            cover_path = os.path.join(output_dir, "cover" + extension)

            # 確保輸出目錄存在
            os.makedirs(os.path.dirname(cover_path), exist_ok=True)

            # 寫入封面圖檔
            with open(cover_path, "wb") as f:
                f.write(artwork)
            return True
    except Exception as e:
        print(f"儲存封面圖檔時發生錯誤: {str(e)}")
    return False
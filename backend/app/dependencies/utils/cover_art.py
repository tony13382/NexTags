import os
from mutagen.mp4 import MP4Cover


def save_cover_art(mp4_file, output_dir):
    """儲存封面圖檔"""
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
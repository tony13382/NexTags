import os
import subprocess
from mutagen.flac import FLAC


def ensure_output_directory(output_file):
    """確保輸出目錄存在"""
    os.makedirs(os.path.dirname(output_file), exist_ok=True)


def convert_audio_to_flac(input_file, output_file):
    """使用 FFmpeg 將音訊檔案轉換為 FLAC 格式"""
    command = ["ffmpeg", "-i", input_file, "-c:a", "flac", output_file, "-y"]
    subprocess.run(command, check=True, capture_output=True)


def set_flac_tags(output_file, tags):
    """設定 FLAC 檔案的標籤"""
    flac_file = FLAC(output_file)
    
    # 安全地獲取標籤值，如果不存在則使用空白字符串
    def get_tag_value(key, mp4_key=None):
        # 先嘗試標準鍵名
        if key in tags:
            value = tags[key]
            if isinstance(value, list) and value:
                return value[0] if value[0] else ""
            return str(value) if value else ""
        
        # 如果有MP4鍵名，嘗試MP4格式的鍵名
        if mp4_key and mp4_key in tags:
            value = tags[mp4_key]
            if isinstance(value, list) and value:
                return value[0] if value[0] else ""
            return str(value) if value else ""
        
        return ""
    
    flac_file["artist"] = get_tag_value("artist", "\xa9ART")
    flac_file["album"] = get_tag_value("album", "\xa9alb")
    flac_file["title"] = get_tag_value("title", "\xa9nam")
    flac_file["albumartist"] = get_tag_value("albumartist", "aART")
    flac_file["composer"] = get_tag_value("composer", "\xa9wrt")
    flac_file["artistsort"] = get_tag_value("artistsort", "soar")
    flac_file["albumsort"] = get_tag_value("albumsort", "soal")
    flac_file["titlesort"] = get_tag_value("titlesort", "sonm")
    flac_file["albumartistsort"] = get_tag_value("albumartistsort", "soaa")
    flac_file["composersort"] = get_tag_value("composersort", "soco")
    
    flac_file.save()


def convert_to_flac(input_file, output_file, tags):
    """將音訊檔案轉換為 FLAC 並設定標籤"""
    try:
        ensure_output_directory(output_file)
        convert_audio_to_flac(input_file, output_file)
        set_flac_tags(output_file, tags)
        return True

    except subprocess.CalledProcessError as e:
        print(f"轉換失敗: {str(e)}")
        return False
    except Exception as e:
        print(f"發生錯誤: {str(e)}")
        return False
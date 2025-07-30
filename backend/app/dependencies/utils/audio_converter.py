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
    
    flac_file["artist"] = tags["artist"]
    flac_file["album"] = tags["album"]
    flac_file["title"] = tags["title"]
    flac_file["artistsort"] = tags["artistsort"]
    flac_file["albumsort"] = tags["albumsort"]
    flac_file["titlesort"] = tags["titlesort"]
    
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
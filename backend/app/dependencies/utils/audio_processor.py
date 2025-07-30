import os
from mutagen.mp4 import MP4

from ..text_process import convertPinyin
from .cover_art import save_cover_art
from .audio_converter import convert_to_flac
from .tag_reader import extract_mp4_tags


def create_output_directory(file_path, artist, album):
    """建立輸出目錄路徑"""
    return os.path.join(os.path.dirname(file_path), "out", artist, album)


def create_tags_with_pinyin(tag_info):
    """建立包含拼音排序的標籤字典"""
    artist = tag_info["artist"]
    album = tag_info["album"]
    title = tag_info["title"]
    
    return {
        "artist": [artist],
        "album": [album],
        "title": [title],
        "artistsort": [convertPinyin(artist)],
        "albumsort": [convertPinyin(album)],
        "titlesort": [convertPinyin(title)],
    }


def create_output_filename(file_path, output_dir):
    """建立輸出檔案路徑"""
    original_filename = os.path.basename(file_path)
    new_filename = os.path.splitext(original_filename)[0] + ".flac"
    return os.path.join(output_dir, new_filename)


def process_single_file(file_path):
    """處理單一音訊檔案"""
    try:
        audio = MP4(file_path)
        
        tag_info = extract_mp4_tags(audio)
        if tag_info is None:
            print(f"無法提取檔案標籤: {file_path}")
            return

        print(f"處理檔案: {file_path}")

        tags = create_tags_with_pinyin(tag_info)
        output_dir = create_output_directory(file_path, tag_info["artist"], tag_info["album"])
        
        if save_cover_art(audio, output_dir):
            print("成功儲存封面圖檔")
        else:
            print("無法儲存封面圖檔或檔案不含封面")

        flac_file = create_output_filename(file_path, output_dir)

        if convert_to_flac(file_path, flac_file, tags):
            print(f"成功轉換到: {flac_file}")
        else:
            print(f"轉換失敗: {file_path}")

        print("--------------------------------")

    except Exception as e:
        print(f"處理檔案 {file_path} 時發生錯誤: {str(e)}")


def validate_input_path(input_path):
    """驗證輸入路徑是否存在"""
    if not os.path.exists(input_path):
        print(f"路徑 {input_path} 不存在")
        return False
    return True


def find_m4a_files(input_path):
    """尋找指定路徑下的所有 m4a 檔案"""
    m4a_files = []
    for root, dirs, files in os.walk(input_path):
        for file in files:
            if file.endswith(".m4a"):
                file_path = os.path.join(root, file)
                m4a_files.append(file_path)
    return m4a_files


def process_audio_files(input_path):
    """處理音訊檔案的主要函數"""
    print(f"正在處理路徑: {input_path}")

    if not validate_input_path(input_path):
        return

    m4a_files = find_m4a_files(input_path)
    for file_path in m4a_files:
        process_single_file(file_path)
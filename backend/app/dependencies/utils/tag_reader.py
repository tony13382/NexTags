import mutagen
from mutagen.mp4 import MP4
from mutagen.flac import FLAC
from mutagen.mp3 import MP3
from mutagen.id3 import ID3


def read_audio_tags(file_path):
    """讀取音訊檔案的所有標籤"""
    try:
        # 先用 mutagen 自動判斷檔案類型
        audio = mutagen.File(file_path)

        if audio is None:
            print(f"無法讀取檔案: {file_path}")
            return

        print(f"檔案: {file_path}")
        print("標籤列表:")

        # 根據不同的檔案類型處理標籤
        if isinstance(audio, MP4):
            for key, value in audio.tags.items():
                print(f"{key}: {value}")

        elif isinstance(audio, FLAC):
            for key, value in audio.tags.items():
                print(f"{key}: {value}")

        elif isinstance(audio, MP3):
            # 使用 ID3 來讀取 MP3 標籤
            id3 = ID3(file_path)
            for key, value in id3.items():
                print(f"{key}: {value}")

        else:
            # 其他格式的通用處理方法
            for key, value in audio.tags.items():
                print(f"{key}: {value}")

    except Exception as e:
        print(f"處理檔案時發生錯誤: {str(e)}")


def extract_mp4_tags(audio_file):
    """從MP4音訊檔案中提取基本標籤信息"""
    try:
        artist = audio_file.tags["\xa9ART"][0]
        album = audio_file.tags["\xa9alb"][0]
        title = audio_file.tags["\xa9nam"][0]
        
        return {
            "artist": artist,
            "album": album,
            "title": title
        }
    except KeyError as e:
        print(f"缺少必要的標籤: {str(e)}")
        return None
    except Exception as e:
        print(f"提取標籤時發生錯誤: {str(e)}")
        return None
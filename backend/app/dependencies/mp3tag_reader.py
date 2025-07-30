import mutagen
from mutagen.mp4 import MP4
from mutagen.flac import FLAC
from mutagen.mp3 import MP3
from mutagen.oggvorbis import OggVorbis
from mutagen.id3 import ID3

from app.dependencies.logger import logger


def read_audio_tags(file_path) -> dict:
    """讀取音訊檔案的所有標籤"""
    try:
        logger.info(f"開始讀取音訊檔案標籤: {file_path}")
        
        # 先用 mutagen 自動判斷檔案類型
        audio = mutagen.File(file_path)

        if audio is None:
            logger.error(f"無法讀取檔案: {file_path}")
            return {}

        return_dict = {}

        # 根據不同的檔案類型處理標籤
        if isinstance(audio, MP4):
            logger.info(f"檔案類型: MP4 - {file_path}")
            for key, value in audio.tags.items():
                return_dict[key] = value

        elif isinstance(audio, FLAC):
            logger.info(f"檔案類型: FLAC - {file_path}")
            for key, value in audio.tags.items():
                return_dict[key] = value

        elif isinstance(audio, MP3):
            logger.info(f"檔案類型: MP3 - {file_path}")
            # 使用 ID3 來讀取 MP3 標籤
            id3 = ID3(file_path)
            for key, value in id3.items():
                return_dict[key] = value

        elif isinstance(audio, OggVorbis):
            logger.info(f"檔案類型: OGG - {file_path}")
            for key, value in audio.tags.items():
                return_dict[key] = value

        else:
            logger.info(f"檔案類型: 其他格式 - {file_path}")
            # 其他格式的通用處理方法
            if hasattr(audio, 'tags') and audio.tags:
                for key, value in audio.tags.items():
                    return_dict[key] = value

        logger.info(f"成功讀取 {len(return_dict)} 個標籤 - {file_path}")
        return return_dict

    except Exception as e:
        logger.error(f"處理檔案時發生錯誤: {file_path} - {str(e)}")
        return {}
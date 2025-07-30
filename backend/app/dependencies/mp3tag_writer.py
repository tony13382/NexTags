import mutagen
from mutagen.mp4 import MP4
from mutagen.flac import FLAC
from mutagen.mp3 import MP3
from mutagen.oggvorbis import OggVorbis
from mutagen.id3 import TIT2, TPE1, TALB, TPE2, TDRC, TRCK, TPOS, TSOT, TSOP, TSOA

from app.dependencies.logger import logger


def write_mp4_tags(audio, tags_dict):
    """寫入 MP4 格式的標籤"""
    tag_mapping = {
        'title': '\xa9nam',
        'artist': '\xa9ART', 
        'album': '\xa9alb',
        'albumartist': 'aART',
        'date': '\xa9day',
        'year': '\xa9day',
        'track': 'trkn',
        'disc': 'disk',
        'genre': '\xa9gen',
        'comment': '\xa9cmt',
        'titlesort': 'sonm',
        'artistsort': 'soar',
        'albumsort': 'soal'
    }
    
    for key, value in tags_dict.items():
        if key in tag_mapping:
            mp4_key = tag_mapping[key]
            if key in ['track', 'disc']:
                if isinstance(value, str) and '/' in value:
                    current, total = value.split('/', 1)
                    audio[mp4_key] = [(int(current), int(total))]
                else:
                    audio[mp4_key] = [(int(value), 0)]
            else:
                audio[mp4_key] = [str(value)]


def write_flac_tags(audio, tags_dict):
    """寫入 FLAC 格式的標籤"""
    for key, value in tags_dict.items():
        audio[key.upper()] = [str(value)]


def write_ogg_tags(audio, tags_dict):
    """寫入 OGG 格式的標籤"""
    for key, value in tags_dict.items():
        audio[key.upper()] = [str(value)]


def write_mp3_tags(audio, tags_dict):
    """寫入 MP3 格式的標籤"""
    tag_mapping = {
        'title': TIT2,
        'artist': TPE1,
        'album': TALB,
        'albumartist': TPE2,
        'date': TDRC,
        'year': TDRC,
        'track': TRCK,
        'disc': TPOS,
        'titlesort': TSOT,
        'artistsort': TSOP,
        'albumsort': TSOA
    }
    
    for key, value in tags_dict.items():
        if key in tag_mapping:
            tag_class = tag_mapping[key]
            audio.tags[tag_class.__name__] = tag_class(encoding=3, text=str(value))


def write_tags(audio_path, tags_dict) -> bool:
    """修改音訊檔案的標籤
    
    Args:
        audio_path (str): 音訊檔案路徑
        tags_dict (dict): 要寫入的標籤字典
        
    Returns:
        bool: 是否成功寫入標籤
    """
    try:
        logger.info(f"開始寫入音訊檔案標籤: {audio_path}")
        
        audio = mutagen.File(audio_path)
        
        if audio is None:
            logger.error(f"無法讀取檔案: {audio_path}")
            return False
            
        if isinstance(audio, MP4):
            logger.info(f"檔案類型: MP4 - {audio_path}")
            write_mp4_tags(audio, tags_dict)
            
        elif isinstance(audio, FLAC):
            logger.info(f"檔案類型: FLAC - {audio_path}")
            write_flac_tags(audio, tags_dict)
            
        elif isinstance(audio, MP3):
            logger.info(f"檔案類型: MP3 - {audio_path}")
            if audio.tags is None:
                audio.add_tags()
            write_mp3_tags(audio, tags_dict)
            
        elif isinstance(audio, OggVorbis):
            logger.info(f"檔案類型: OGG - {audio_path}")
            write_ogg_tags(audio, tags_dict)
            
        else:
            logger.warning(f"不支援的檔案格式: {audio_path}")
            return False
            
        audio.save()
        logger.info(f"成功寫入標籤: {audio_path}")
        return True
        
    except Exception as e:
        logger.error(f"寫入標籤時發生錯誤: {audio_path} - {str(e)}")
        return False
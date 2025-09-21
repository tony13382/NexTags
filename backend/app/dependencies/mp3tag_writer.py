import mutagen
from mutagen.mp4 import MP4
from mutagen.flac import FLAC
from mutagen.mp3 import MP3
from mutagen.oggvorbis import OggVorbis
from mutagen.id3 import TIT2, TPE1, TALB, TPE2, TCOM, TDRC, TRCK, TPOS, TSOT, TSOP, TSOA, TSO2, TSOC, COMM, USLT
import yaml
import os

from app.dependencies.logger import logger


def load_supported_genres():
    """從 config.yaml 載入支援的流派"""
    try:
        config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '..', 'config.yaml')
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
            return config.get('supported_tags', [])
    except Exception as e:
        logger.error(f"載入 config.yaml 失敗: {str(e)}")
        return []


def validate_genres(genres):
    """驗證流派是否在支援清單中"""
    supported_genres = load_supported_genres()
    if not supported_genres:
        return genres
    
    if isinstance(genres, list):
        return [genre for genre in genres if genre in supported_genres]
    elif isinstance(genres, str):
        return genres if genres in supported_genres else None
    
    return None


def write_mp4_tags(audio, tags_dict):
    """寫入 MP4 格式的標籤"""
    tag_mapping = {
        'title': '\xa9nam',
        'artist': '\xa9ART',
        'album': '\xa9alb',
        'albumartist': 'aART',
        'composer': '\xa9wrt',
        'date': '\xa9day',
        'year': '\xa9day',
        'track': 'trkn',
        'disc': 'disk',
        'genre': '\xa9gen',
        'comment': '\xa9cmt',
        'lyrics': '\xa9lyr',
        'titlesort': 'sonm',
        'artistsort': 'soar',
        'albumsort': 'soal',
        'albumartistsort': 'soaa',
        'composersort': 'soco',
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
            elif key == 'genre':
                # 處理流派列表格式並驗證
                validated_genres = validate_genres(value)
                if validated_genres is not None:
                    if isinstance(validated_genres, list):
                        if validated_genres:  # 只有非空列表才寫入
                            audio[mp4_key] = [str(v) for v in validated_genres]
                    else:
                        audio[mp4_key] = [str(validated_genres)]
                else:
                    logger.warning(f"流派 '{value}' 不在支援清單中，跳過寫入")
            elif key in ['artist', 'artistsort', 'albumartist', 'albumartistsort', 'composer', 'composersort']:
                # 處理多歌手格式（反斜線分隔）
                if isinstance(value, str) and '\\' in value:
                    artists = [artist.strip() for artist in value.split('\\') if artist.strip()]
                    audio[mp4_key] = artists
                elif isinstance(value, list):
                    audio[mp4_key] = [str(v) for v in value if v]
                else:
                    audio[mp4_key] = [str(value)]
            else:
                audio[mp4_key] = [str(value)]


def write_flac_tags(audio, tags_dict):
    """寫入 FLAC 格式的標籤"""
    for key, value in tags_dict.items():
        if key == 'genre':
            # 處理流派列表格式並驗證
            validated_genres = validate_genres(value)
            if validated_genres is not None:
                if isinstance(validated_genres, list):
                    if validated_genres:  # 只有非空列表才寫入
                        audio[key.upper()] = [str(v) for v in validated_genres]
                else:
                    audio[key.upper()] = [str(validated_genres)]
            else:
                logger.warning(f"流派 '{value}' 不在支援清單中，跳過寫入")
        elif key in ['artist', 'artistsort', 'albumartist', 'albumartistsort', 'composer', 'composersort']:
            # 處理多歌手格式（反斜線分隔）
            if isinstance(value, str) and '\\' in value:
                artists = [artist.strip() for artist in value.split('\\') if artist.strip()]
                audio[key.upper()] = artists
            elif isinstance(value, list):
                audio[key.upper()] = [str(v) for v in value if v]
            else:
                audio[key.upper()] = [str(value)]
        else:
            audio[key.upper()] = [str(value)]


def write_ogg_tags(audio, tags_dict):
    """寫入 OGG 格式的標籤"""
    for key, value in tags_dict.items():
        if key == 'genre':
            # 處理流派列表格式並驗證
            validated_genres = validate_genres(value)
            if validated_genres is not None:
                if isinstance(validated_genres, list):
                    if validated_genres:  # 只有非空列表才寫入
                        audio[key.upper()] = [str(v) for v in validated_genres]
                else:
                    audio[key.upper()] = [str(validated_genres)]
            else:
                logger.warning(f"流派 '{value}' 不在支援清單中，跳過寫入")
        elif key in ['artist', 'artistsort', 'albumartist', 'albumartistsort', 'composer', 'composersort']:
            # 處理多歌手格式（反斜線分隔）
            if isinstance(value, str) and '\\' in value:
                artists = [artist.strip() for artist in value.split('\\') if artist.strip()]
                audio[key.upper()] = artists
            elif isinstance(value, list):
                audio[key.upper()] = [str(v) for v in value if v]
            else:
                audio[key.upper()] = [str(value)]
        else:
            audio[key.upper()] = [str(value)]


def write_mp3_tags(audio, tags_dict):
    """寫入 MP3 格式的標籤"""
    from mutagen.id3 import TCON
    
    tag_mapping = {
        'title': TIT2,
        'artist': TPE1,
        'album': TALB,
        'albumartist': TPE2,
        'composer': TCOM,
        'date': TDRC,
        'year': TDRC,
        'track': TRCK,
        'disc': TPOS,
        'titlesort': TSOT,
        'artistsort': TSOP,
        'albumsort': TSOA,
        'albumartistsort': TSO2,
        'composersort': TSOC,
        'genre': TCON,
    }
    
    for key, value in tags_dict.items():
        if key == 'comment':
            # 對於評論，使用 COMM 框架
            audio.tags['COMM::eng'] = COMM(encoding=3, lang='eng', desc='', text=str(value))
        elif key == 'lyrics':
            # 對於歌詞，使用 USLT 框架
            audio.tags['USLT::eng'] = USLT(encoding=3, lang='eng', desc='', text=str(value))
        elif key == 'genre':
            # 處理流派列表格式並驗證
            validated_genres = validate_genres(value)
            if validated_genres is not None:
                if isinstance(validated_genres, list):
                    if validated_genres:  # 只有非空列表才寫入
                        audio.tags['TCON'] = TCON(encoding=3, text=[str(v) for v in validated_genres])
                else:
                    audio.tags['TCON'] = TCON(encoding=3, text=[str(validated_genres)])
            else:
                logger.warning(f"流派 '{value}' 不在支援清單中，跳過寫入")
        elif key in ['artist', 'artistsort', 'albumartist', 'albumartistsort', 'composer', 'composersort']:
            # 處理多歌手格式（反斜線分隔）
            tag_class = tag_mapping[key]
            if isinstance(value, str) and '\\' in value:
                artists = [artist.strip() for artist in value.split('\\') if artist.strip()]
                audio.tags[tag_class.__name__] = tag_class(encoding=3, text=artists)
            elif isinstance(value, list):
                audio.tags[tag_class.__name__] = tag_class(encoding=3, text=[str(v) for v in value if v])
            else:
                audio.tags[tag_class.__name__] = tag_class(encoding=3, text=[str(value)])
        elif key in tag_mapping and tag_mapping[key] is not None:
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
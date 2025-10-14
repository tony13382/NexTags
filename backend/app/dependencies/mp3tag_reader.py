import mutagen
from mutagen.mp4 import MP4
from mutagen.flac import FLAC
from mutagen.mp3 import MP3
from mutagen.oggvorbis import OggVorbis
from mutagen.id3 import ID3

from app.dependencies.logger import logger


def normalize_tag_keys(raw_tags: dict) -> dict:
    """標準化標籤鍵名，將不同格式的標籤統一為標準名稱"""
    normalized = {}
    
    # 標籤映射表，將不同格式的標籤鍵名統一
    tag_mappings = {
        # Comment 相關
        'comment': ['comment', 'COMM::eng', '\xa9cmt', 'COMMENT'],
        # Lyrics 相關
        'lyrics': ['lyrics', 'USLT::eng', '\xa9lyr', 'LYRICS', 'UNSYNCEDLYRICS'],
        # 其他常用標籤
        'title': ['title', 'TIT2', '\xa9nam', 'TITLE'],
        'artist': ['artist', 'TPE1', '\xa9ART', 'ARTIST'],
        'album': ['album', 'TALB', '\xa9alb', 'ALBUM'],
        'albumartist': ['albumartist', 'TPE2', 'aART', 'ALBUMARTIST'],
        'composer': ['composer', 'TCOM', '\xa9wrt', 'COMPOSER'],
        'titlesort': ['titlesort', 'TSOT', 'sonm', 'TITLESORT'],
        'artistsort': ['artistsort', 'TSOP', 'soar', 'ARTISTSORT'],
        'albumsort': ['albumsort', 'TSOA', 'soal', 'ALBUMSORT'],
        'albumartistsort': ['albumartistsort', 'TSO2', 'soaa', 'ALBUMARTISTSORT', 'TXXX:ALBUMARTISTSORT'],
        'composersort': ['composersort', 'TSOC', 'soco', 'COMPOSERSORT', 'TXXX:COMPOSERSORT'],
        'genre': ['genre', 'TCON', '\xa9gen', 'GENRE'],
        'language': ['language', 'TLAN', 'LANGUAGE'],
        'favorite': ['favorite', 'FAVORITE', 'Favorite', 'TXXX:FAVORITE', 'TXXX:Favorite'],
        # ReplayGain 相關標籤（只保留 Track Gain 和 Track Peak）
        'replaygain_track_gain': [
            'replaygain_track_gain',  # FLAC/Vorbis (小寫)
            'REPLAYGAIN_TRACK_GAIN',  # FLAC/Vorbis (大寫)
            'TXXX:REPLAYGAIN_TRACK_GAIN',  # MP3 (ID3v2) - 大寫
            'TXXX:replaygain_track_gain',  # MP3 (ID3v2) - 小寫
            '----:com.apple.iTunes:replaygain_track_gain',  # MP4
        ],
        'replaygain_track_peak': [
            'replaygain_track_peak',  # FLAC/Vorbis (小寫)
            'REPLAYGAIN_TRACK_PEAK',  # FLAC/Vorbis (大寫)
            'TXXX:REPLAYGAIN_TRACK_PEAK',  # MP3 (ID3v2) - 大寫
            'TXXX:replaygain_track_peak',  # MP3 (ID3v2) - 小寫
            '----:com.apple.iTunes:replaygain_track_peak',  # MP4
        ],
    }
    
    # 直接複製所有原始標籤
    for key, value in raw_tags.items():
        normalized[key] = value
    
    # 標準化特定標籤
    for standard_key, possible_keys in tag_mappings.items():
        for possible_key in possible_keys:
            if possible_key in raw_tags:
                # 提取文字內容
                raw_value = raw_tags[possible_key]
                if hasattr(raw_value, 'text'):
                    # ID3 標籤有 text 屬性
                    text_value = raw_value.text
                    if standard_key == 'genre':
                        # 流派標籤保持為列表格式
                        if isinstance(text_value, list):
                            normalized[standard_key] = [str(t) for t in text_value if t] if text_value else []
                        else:
                            normalized[standard_key] = [str(text_value)] if text_value else []
                    elif standard_key in ['artist', 'artistsort', 'albumartist', 'albumartistsort', 'composer', 'composersort']:
                        # Artist 相關標籤使用反斜線分隔
                        if isinstance(text_value, list):
                            normalized[standard_key] = '\\'.join(str(t) for t in text_value) if text_value else ''
                        else:
                            normalized[standard_key] = str(text_value) if text_value else ''
                    else:
                        # 其他標籤轉換為字符串
                        if isinstance(text_value, list):
                            normalized[standard_key] = ' '.join(str(t) for t in text_value) if text_value else ''
                        else:
                            normalized[standard_key] = str(text_value) if text_value else ''
                elif isinstance(raw_value, list):
                    if standard_key == 'genre':
                        # 流派標籤保持為列表格式
                        normalized[standard_key] = [str(v) for v in raw_value if v] if raw_value else []
                    elif standard_key in ['artist', 'artistsort', 'albumartist', 'albumartistsort', 'composer', 'composersort']:
                        # Artist 相關標籤使用反斜線分隔
                        normalized[standard_key] = '\\'.join(str(v) for v in raw_value) if raw_value else ''
                    elif standard_key.startswith('replaygain_'):
                        # ReplayGain 標籤取第一個值
                        normalized[standard_key] = str(raw_value[0]) if raw_value else ''
                    else:
                        # 其他標籤轉換為字符串
                        normalized[standard_key] = ' '.join(str(v) for v in raw_value) if raw_value else ''
                else:
                    if standard_key == 'genre':
                        # 流派標籤保持為列表格式
                        normalized[standard_key] = [str(raw_value)] if raw_value else []
                    else:
                        # 其他標籤轉換為字符串
                        normalized[standard_key] = str(raw_value) if raw_value else ''
                break
    
    return normalized


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

        # 標準化標籤鍵名
        normalized_tags = normalize_tag_keys(return_dict)
        
        logger.info(f"成功讀取 {len(return_dict)} 個標籤 - {file_path}")
        return normalized_tags

    except Exception as e:
        logger.error(f"處理檔案時發生錯誤: {file_path} - {str(e)}")
        return {}
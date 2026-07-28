import mutagen
from mutagen.mp4 import MP4
from mutagen.flac import FLAC
from mutagen.mp3 import MP3
from mutagen.oggvorbis import OggVorbis
from mutagen.id3 import ID3

from app.dependencies.logger import logger


# number/total 成對的標籤：主欄位 -> 總數欄位
PAIR_NUMBER_KEYS = {
    'discnumber': 'disctotal',
    'tracknumber': 'tracktotal',
}


def clean_number_token(value) -> str:
    """把 number/total 類標籤值收斂成乾淨字串。

    需要容錯歷史資料：早期寫入路徑會把 Python list 直接 str() 塞進標籤，
    在檔案裡留下 "['3/11']" 這種值（外層有中括號與引號），必須剝掉外殼
    才能正確解析，否則會拆出 "['3" 這類垃圾。
    """
    if isinstance(value, (list, tuple)):
        value = value[0] if value else ''

    text = str(value).strip() if value is not None else ''

    # 剝除 str(list) 留下的外殼，例如 "['3/11']" -> "3/11"
    while len(text) >= 2 and text[0] in '[(' and text[-1] in ')]':
        text = text[1:-1].strip()

    return text.strip('\'"').strip()


def _assign_number_pair(normalized: dict, standard_key: str, value) -> None:
    """把 (1, 2) 元組、"1/2" 字串或 "1" 單值拆成主欄位與總數欄位。

    disc 與 track 在 ID3(TPOS/TRCK)、MP4(disk/trkn)、Vorbis 三種容器裡的格式完全一致，
    因此共用同一份拆解邏輯。
    """
    total_key = PAIR_NUMBER_KEYS[standard_key]

    # MP4 的 (num, total) 是正規結構，優先處理，不可先被當成字串清理
    if isinstance(value, tuple) and len(value) >= 1:
        normalized[standard_key] = str(value[0]) if value[0] else ''
        if len(value) >= 2 and value[1]:
            normalized[total_key] = str(value[1])
        return

    text = clean_number_token(value)
    if '/' in text:
        number, _, total = text.partition('/')
        normalized[standard_key] = clean_number_token(number)
        total = clean_number_token(total)
        if total:
            normalized[total_key] = total
    else:
        normalized[standard_key] = text


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
        'performer': ['performer', 'TPE3', '\xa9prf', 'PERFORMER'],
        'titlesort': ['titlesort', 'TSOT', 'sonm', 'TITLESORT'],
        'artistsort': ['artistsort', 'TSOP', 'soar', 'ARTISTSORT'],
        'albumsort': ['albumsort', 'TSOA', 'soal', 'ALBUMSORT'],
        'albumartistsort': ['albumartistsort', 'TSO2', 'soaa', 'ALBUMARTISTSORT', 'TXXX:ALBUMARTISTSORT'],
        'composersort': ['composersort', 'TSOC', 'soco', 'COMPOSERSORT', 'TXXX:COMPOSERSORT'],
        'performersort': ['performersort', 'TSOP3', 'sope', 'PERFORMERSORT', 'TXXX:PERFORMERSORT'],
        'discnumber': ['discnumber', 'TPOS', 'disk', 'DISCNUMBER', 'DISC'],
        # Vorbis comment 的 key 由 mutagen 回傳小寫，ID3/MP4 則是原樣，因此兩種大小寫都要列
        'disctotal': ['disctotal', 'DISCTOTAL', 'totaldiscs', 'TOTALDISCS'],
        'tracknumber': ['tracknumber', 'TRCK', 'trkn', 'TRACKNUMBER', 'TRACK'],
        'tracktotal': ['tracktotal', 'TRACKTOTAL', 'totaltracks', 'TOTALTRACKS'],
        'genre': ['genre', 'TCON', '\xa9gen', 'GENRE'],
        'language': ['language', 'TLAN', 'LANGUAGE', 'TXXX:LANGUAGE', '----:com.apple.iTunes:LANGUAGE'],
        'favorite': ['favorite', 'FAVORITE', 'Favorite', 'TXXX:FAVORITE', 'TXXX:Favorite', '----:com.apple.iTunes:FAVORITE'],
        # ReplayGain 相關標籤
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
        'replaygain_album_gain': [
            'replaygain_album_gain',  # FLAC/Vorbis (小寫)
            'REPLAYGAIN_ALBUM_GAIN',  # FLAC/Vorbis (大寫)
            'TXXX:REPLAYGAIN_ALBUM_GAIN',  # MP3 (ID3v2) - 大寫
            'TXXX:replaygain_album_gain',  # MP3 (ID3v2) - 小寫
            '----:com.apple.iTunes:replaygain_album_gain',  # MP4
        ],
        'replaygain_album_peak': [
            'replaygain_album_peak',  # FLAC/Vorbis (小寫)
            'REPLAYGAIN_ALBUM_PEAK',  # FLAC/Vorbis (大寫)
            'TXXX:REPLAYGAIN_ALBUM_PEAK',  # MP3 (ID3v2) - 大寫
            'TXXX:replaygain_album_peak',  # MP3 (ID3v2) - 小寫
            '----:com.apple.iTunes:replaygain_album_peak',  # MP4
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
                    elif standard_key in ['artist', 'artistsort', 'albumartist', 'albumartistsort', 'composer', 'composersort', 'performer', 'performersort']:
                        # Artist 相關標籤使用分號分隔
                        if isinstance(text_value, list):
                            normalized[standard_key] = ';'.join(str(t) for t in text_value) if text_value else ''
                        else:
                            normalized[standard_key] = str(text_value) if text_value else ''
                    elif standard_key in PAIR_NUMBER_KEYS:
                        # disc/track 可能是 (1, 2) 元組格式或 "1/2" 字符串格式
                        if isinstance(text_value, list) and len(text_value) > 0:
                            _assign_number_pair(normalized, standard_key, text_value[0])
                        else:
                            _assign_number_pair(normalized, standard_key, text_value)
                    elif standard_key in ['language', 'favorite', 'replaygain_track_gain', 'replaygain_track_peak', 'replaygain_album_gain', 'replaygain_album_peak']:
                        # Language、Favorite 和 ReplayGain 標籤為單值欄位
                        if isinstance(text_value, list):
                            normalized[standard_key] = str(text_value[0]) if text_value else ''
                        else:
                            normalized[standard_key] = str(text_value) if text_value else ''
                    else:
                        # 其他標籤轉換為字符串
                        if isinstance(text_value, list):
                            normalized[standard_key] = ' '.join(str(t) for t in text_value) if text_value else ''
                        else:
                            normalized[standard_key] = str(text_value) if text_value else ''
                elif isinstance(raw_value, list):
                    # 處理 MP4FreeForm (bytes) - 需要解碼
                    decoded_value = []
                    for v in raw_value:
                        if isinstance(v, bytes):
                            try:
                                decoded_value.append(v.decode('utf-8'))
                            except:
                                decoded_value.append(str(v))
                        else:
                            decoded_value.append(v)

                    if standard_key == 'genre':
                        # 流派標籤保持為列表格式
                        normalized[standard_key] = [str(v) for v in decoded_value if v] if decoded_value else []
                    elif standard_key in ['artist', 'artistsort', 'albumartist', 'albumartistsort', 'composer', 'composersort', 'performer', 'performersort']:
                        # Artist 相關標籤使用分號分隔
                        normalized[standard_key] = ';'.join(str(v) for v in decoded_value) if decoded_value else ''
                    elif standard_key in PAIR_NUMBER_KEYS:
                        # disc/track 可能是 [(1, 2)] 格式或 ["1/2"] 格式
                        if len(decoded_value) > 0:
                            _assign_number_pair(normalized, standard_key, decoded_value[0])
                    elif standard_key.startswith('replaygain_') or standard_key in ['language', 'favorite']:
                        # ReplayGain、Language 和 Favorite 標籤取第一個值（單值欄位）
                        normalized[standard_key] = str(decoded_value[0]) if decoded_value else ''
                    else:
                        # 其他標籤轉換為字符串
                        normalized[standard_key] = ' '.join(str(v) for v in decoded_value) if decoded_value else ''
                else:
                    if standard_key == 'genre':
                        # 流派標籤保持為列表格式
                        normalized[standard_key] = [str(raw_value)] if raw_value else []
                    elif standard_key in PAIR_NUMBER_KEYS:
                        # 純量值也可能是 "1/2" 格式
                        _assign_number_pair(normalized, standard_key, raw_value)
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
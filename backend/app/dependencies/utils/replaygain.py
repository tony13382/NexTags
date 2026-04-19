import os
import re
import subprocess
from typing import Tuple
from ..logger import logger


def _get_ffmpeg_path() -> str:
    """取得 ffmpeg 執行檔路徑"""
    for path in ['/usr/bin/ffmpeg', 'ffmpeg']:
        try:
            result = subprocess.run(
                [path, '-version'],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                return path
        except (FileNotFoundError, subprocess.TimeoutExpired):
            continue
    return ''


def _parse_replaygain_output(stderr: str) -> Tuple[str, str]:
    """從 ffmpeg stderr 中解析 ReplayGain 值"""
    gain_match = re.search(r'track_gain\s*=\s*([-\d.]+)\s*dB', stderr)
    peak_match = re.search(r'track_peak\s*=\s*([\d.]+)', stderr)

    track_gain = f"{gain_match.group(1)} dB" if gain_match else ''
    track_peak = peak_match.group(1) if peak_match else ''

    return track_gain, track_peak


def _write_replaygain_tags(file_path: str, track_gain: str, track_peak: str) -> Tuple[bool, str]:
    """使用 mutagen 將 ReplayGain 標籤寫入檔案"""
    try:
        from mutagen import File as MutagenFile
        from mutagen.flac import FLAC
        from mutagen.mp3 import MP3
        from mutagen.mp4 import MP4
        from mutagen.id3 import TXXX

        audio = MutagenFile(file_path)
        if audio is None:
            return False, "無法識別音訊格式"

        if isinstance(audio, FLAC):
            audio['REPLAYGAIN_TRACK_GAIN'] = track_gain
            audio['REPLAYGAIN_TRACK_PEAK'] = track_peak
        elif isinstance(audio, MP3):
            if audio.tags is None:
                audio.add_tags()
            audio.tags.add(TXXX(encoding=3, desc='REPLAYGAIN_TRACK_GAIN', text=[track_gain]))
            audio.tags.add(TXXX(encoding=3, desc='REPLAYGAIN_TRACK_PEAK', text=[track_peak]))
        elif isinstance(audio, MP4):
            audio['----:com.apple.iTunes:replaygain_track_gain'] = track_gain.encode('utf-8')
            audio['----:com.apple.iTunes:replaygain_track_peak'] = track_peak.encode('utf-8')
        else:
            return False, f"不支援的音訊格式: {type(audio).__name__}"

        audio.save()
        return True, "標籤寫入成功"

    except Exception as e:
        return False, f"寫入標籤失敗: {str(e)}"


def generate_replaygain(file_path: str) -> Tuple[bool, str]:
    """
    使用 ffmpeg replaygain filter 計算並寫入 ReplayGain 標籤

    Args:
        file_path: 音訊檔案路徑

    Returns:
        Tuple[bool, str]: (成功與否, 訊息)
    """
    try:
        if not os.path.exists(file_path):
            return False, f"檔案不存在: {file_path}"

        ffmpeg_cmd = _get_ffmpeg_path()
        if not ffmpeg_cmd:
            return False, "ffmpeg 未安裝"

        logger.info(f"開始為檔案生成 ReplayGain: {file_path}")

        # 使用簡單的 replaygain filter，避免 ffmpeg 7.x 的 asplit+ebur128 assert bug
        result = subprocess.run(
            [ffmpeg_cmd, '-i', file_path, '-af', 'replaygain', '-f', 'null', '/dev/null',
             '-hide_banner', '-nostats'],
            capture_output=True,
            text=True,
            timeout=120
        )

        stderr = result.stderr or ''

        # ffmpeg 即使計算成功也可能因 assert 失敗而非零退出，所以優先看輸出
        track_gain, track_peak = _parse_replaygain_output(stderr)

        if not track_gain or not track_peak:
            logger.error(f"ReplayGain 無法從 ffmpeg 輸出解析結果: {stderr}")
            return False, "無法計算 ReplayGain 值"

        logger.info(f"ReplayGain 計算結果: gain={track_gain}, peak={track_peak}")

        # 寫入標籤
        success, message = _write_replaygain_tags(file_path, track_gain, track_peak)
        if not success:
            logger.error(f"ReplayGain 標籤寫入失敗: {message}")
            return False, message

        # 清除快取
        try:
            from ..redis_cache import redis_cache
            if redis_cache:
                redis_cache.invalidate_cache(file_path)
                logger.info(f"已從快取中移除: {file_path}")
        except Exception:
            pass

        logger.info(f"ReplayGain 生成成功: {file_path}")
        return True, f"ReplayGain: {track_gain}, Peak: {track_peak}"

    except subprocess.TimeoutExpired:
        logger.error(f"ReplayGain 生成超時: {file_path}")
        return False, "ReplayGain 生成超時 (超過120秒)"
    except Exception as e:
        logger.error(f"ReplayGain 生成異常: {str(e)}")
        return False, f"ReplayGain 生成異常: {str(e)}"



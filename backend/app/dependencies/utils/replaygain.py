import os
import subprocess
from typing import Tuple
from ..logger import logger


def get_r128gain_path() -> str:
    """取得 r128gain 執行檔路徑"""
    # 嘗試多個可能的路徑
    possible_paths = [
        '/app/.venv/bin/r128gain',  # uv venv 路徑（優先）
        'r128gain',  # 系統 PATH
        '/home/appuser/.local/bin/r128gain',  # Docker 容器中的用戶安裝路徑
        '/usr/local/bin/r128gain',  # 全局安裝路徑
    ]

    for path in possible_paths:
        try:
            logger.debug(f"嘗試 r128gain 路徑: {path}")
            # r128gain 不支援 --version，使用 -h 檢查（會返回 0）
            result = subprocess.run(
                [path, '-h'],
                capture_output=True,
                text=True,
                timeout=5
            )
            # -h 會返回 0 並輸出幫助訊息
            if result.returncode == 0 and 'r128gain' in result.stdout.lower():
                logger.info(f"找到 r128gain: {path}")
                return path
            else:
                logger.debug(f"路徑 {path} returncode: {result.returncode}, stdout: {result.stdout[:100]}")
        except FileNotFoundError as e:
            logger.debug(f"路徑 {path} 找不到: {e}")
            continue
        except subprocess.TimeoutExpired:
            logger.debug(f"路徑 {path} 超時")
            continue
        except Exception as e:
            logger.error(f"路徑 {path} 錯誤: {e}")
            continue

    logger.error("找不到任何可用的 r128gain 路徑")
    return ''

def check_r128gain_installed() -> bool:
    """檢查 r128gain 是否已安裝"""
    return bool(get_r128gain_path())


def generate_replaygain(file_path: str) -> Tuple[bool, str]:
    """
    使用 r128gain 為音訊檔案生成 ReplayGain 標籤

    Args:
        file_path: 音訊檔案路徑

    Returns:
        Tuple[bool, str]: (成功與否, 訊息)
    """
    try:
        # 檢查檔案是否存在
        if not os.path.exists(file_path):
            return False, f"檔案不存在: {file_path}"

        # 取得 r128gain 路徑
        r128gain_cmd = get_r128gain_path()
        if not r128gain_cmd:
            return False, "r128gain 未安裝，請先安裝 r128gain"

        logger.info(f"開始為檔案生成 ReplayGain: {file_path}")

        # 執行 r128gain
        # 只計算 track gain 和 track peak，不使用 -a (album mode)
        result = subprocess.run(
            [r128gain_cmd, file_path],
            capture_output=True,
            text=True,
            timeout=60  # 60秒超時
        )

        if result.returncode == 0:
            logger.info(f"ReplayGain 生成成功: {file_path}")
            return True, "ReplayGain 標籤已成功添加"
        else:
            error_msg = result.stderr or result.stdout or "未知錯誤"
            logger.error(f"ReplayGain 生成失敗: {error_msg}")
            return False, f"ReplayGain 生成失敗: {error_msg}"

    except subprocess.TimeoutExpired:
        logger.error(f"ReplayGain 生成超時: {file_path}")
        return False, "ReplayGain 生成超時 (超過60秒)"
    except Exception as e:
        logger.error(f"ReplayGain 生成異常: {str(e)}")
        return False, f"ReplayGain 生成異常: {str(e)}"


def generate_replaygain_for_album(album_path: str) -> Tuple[bool, str]:
    """
    為整個專輯資料夾生成 ReplayGain 標籤

    Args:
        album_path: 專輯資料夾路徑

    Returns:
        Tuple[bool, str]: (成功與否, 訊息)
    """
    try:
        # 檢查資料夾是否存在
        if not os.path.exists(album_path):
            return False, f"資料夾不存在: {album_path}"

        if not os.path.isdir(album_path):
            return False, f"路徑不是資料夾: {album_path}"

        # 取得 r128gain 路徑
        r128gain_cmd = get_r128gain_path()
        if not r128gain_cmd:
            return False, "r128gain 未安裝，請先安裝 r128gain"

        logger.info(f"開始為專輯資料夾生成 ReplayGain: {album_path}")

        # 執行 r128gain
        # -a: album mode
        # -r: 遞迴處理
        result = subprocess.run(
            [r128gain_cmd, '-a', '-r', album_path],
            capture_output=True,
            text=True,
            timeout=300  # 5分鐘超時（整個專輯可能較大）
        )

        if result.returncode == 0:
            logger.info(f"專輯 ReplayGain 生成成功: {album_path}")
            return True, "專輯 ReplayGain 標籤已成功添加"
        else:
            error_msg = result.stderr or result.stdout or "未知錯誤"
            logger.error(f"專輯 ReplayGain 生成失敗: {error_msg}")
            return False, f"專輯 ReplayGain 生成失敗: {error_msg}"

    except subprocess.TimeoutExpired:
        logger.error(f"專輯 ReplayGain 生成超時: {album_path}")
        return False, "專輯 ReplayGain 生成超時 (超過5分鐘)"
    except Exception as e:
        logger.error(f"專輯 ReplayGain 生成異常: {str(e)}")
        return False, f"專輯 ReplayGain 生成異常: {str(e)}"

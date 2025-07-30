import logging
import os
from logging.handlers import TimedRotatingFileHandler

log_dir = os.path.join(os.path.dirname(__file__), "logs")
log_dir = "logs"
os.makedirs(log_dir, exist_ok=True)

log_file_path = os.path.join(log_dir, "app.log")

handler = TimedRotatingFileHandler(
    filename=log_file_path,
    when="midnight",  # 每天午夜新檔
    interval=1,  # 每天
    backupCount=31,  # 保留 天數
    encoding="utf-8",
    utc=False,  # 台灣時間用 False
)

# 設定 logger 格式 https://docs.python.org/3/library/logging.html#logrecord-attributes
formatter = logging.Formatter(
    "%(asctime)s - %(levelname)s - %(pathname)s . %(funcName)s\n%(message)s"
)
handler.setFormatter(formatter)

# logger 不支援 async function，所以不使用 async function
logger = logging.getLogger("main")
logger.setLevel(logging.DEBUG)
logger.addHandler(handler)
logger.addHandler(logging.StreamHandler())  # 控制台同步顯示

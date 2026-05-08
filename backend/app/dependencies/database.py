import os
import json
import sqlite3
from contextlib import contextmanager
from app.dependencies.logger import logger


def serialize_list(value):
    """將 Python list 序列化為 JSON 字串，供 SQLite TEXT 欄位儲存"""
    if value is None or value == []:
        return None
    return json.dumps(value, ensure_ascii=False)


def deserialize_list(value):
    """將 SQLite TEXT 欄位的 JSON 字串反序列化為 Python list"""
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return json.loads(value)


class Database:
    def __init__(self):
        self.db_path = os.getenv('SQLITE_DB_PATH', '/app/data/musicmanager.db')
        self._initialize_db()

    def _initialize_db(self):
        """初始化 SQLite 資料庫"""
        try:
            os.makedirs(os.path.dirname(self.db_path), exist_ok=True)

            # 初始化 WAL 模式與外鍵支援
            conn = sqlite3.connect(self.db_path)
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.execute("PRAGMA foreign_keys=ON;")
            conn.close()

            logger.info(f"成功連接到 SQLite: {self.db_path}")
            self._create_tables()
        except Exception as e:
            logger.error(f"無法連接到 SQLite: {str(e)}")
            raise

    def _column_exists(self, cursor, table, column):
        """檢查資料表中是否存在指定欄位"""
        cursor.execute(f"PRAGMA table_info({table})")
        columns = [row[1] for row in cursor.fetchall()]
        return column in columns

    def _create_tables(self):
        """建立資料表"""
        with self.get_connection() as conn:
            cur = conn.cursor()

            # 建立 SmartPlaylists 資料表
            cur.execute("""
                CREATE TABLE IF NOT EXISTS SmartPlaylists (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    base_folder TEXT NOT NULL,
                    filter_language TEXT,
                    filter_tags TEXT,
                    exclude_tags TEXT,
                    sort_by TEXT DEFAULT 'file_creation_time',
                    is_system_level INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # 為現有表添加欄位（如果不存在）
            if not self._column_exists(cur, 'SmartPlaylists', 'is_system_level'):
                cur.execute("ALTER TABLE SmartPlaylists ADD COLUMN is_system_level INTEGER DEFAULT 0")
                logger.info("已新增 is_system_level 欄位")

            if not self._column_exists(cur, 'SmartPlaylists', 'filter_favorites'):
                cur.execute("ALTER TABLE SmartPlaylists ADD COLUMN filter_favorites INTEGER")
                logger.info("已新增 filter_favorites 欄位")

            if not self._column_exists(cur, 'SmartPlaylists', 'exclude_language'):
                cur.execute("ALTER TABLE SmartPlaylists ADD COLUMN exclude_language TEXT")
                logger.info("已新增 exclude_language 欄位")

            # 建立索引
            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_smartplaylists_name
                ON SmartPlaylists(name)
            """)

            # 建立 Config 資料表
            cur.execute("""
                CREATE TABLE IF NOT EXISTS Config (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    config_key TEXT UNIQUE NOT NULL,
                    config_value TEXT NOT NULL,
                    description TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # 建立索引
            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_config_key
                ON Config(config_key)
            """)

            conn.commit()
            logger.info("SmartPlaylists 資料表已建立")
            logger.info("Config 資料表已建立")

    @contextmanager
    def get_connection(self):
        """取得資料庫連接的 context manager"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def get_cursor(self, conn):
        """取得 cursor（相容原有介面）"""
        return conn.cursor()

    def close(self):
        """關閉資料庫（SQLite 無需連接池管理）"""
        logger.info("SQLite 資料庫已關閉")


# 建立全域資料庫實例
try:
    db = Database()
except Exception as e:
    logger.error(f"無法初始化資料庫: {str(e)}")
    db = None

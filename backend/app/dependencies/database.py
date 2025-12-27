import os
import psycopg2
from psycopg2.extras import RealDictCursor
from psycopg2.pool import SimpleConnectionPool
from contextlib import contextmanager
from app.dependencies.logger import logger


class Database:
    def __init__(self):
        self.pool = None
        self._initialize_pool()

    def _initialize_pool(self):
        """初始化資料庫連接池"""
        try:
            self.pool = SimpleConnectionPool(
                minconn=1,
                maxconn=10,
                host=os.getenv('POSTGRES_HOST', 'localhost'),
                port=int(os.getenv('POSTGRES_PORT', 5432)),
                database=os.getenv('POSTGRES_DB', 'musicmanager'),
                user=os.getenv('POSTGRES_USER', 'musicuser'),
                password=os.getenv('POSTGRES_PASSWORD', 'musicpass')
            )
            logger.info(f"成功連接到 PostgreSQL: {os.getenv('POSTGRES_HOST', 'localhost')}")
            self._create_tables()
        except Exception as e:
            logger.error(f"無法連接到 PostgreSQL: {str(e)}")
            raise

    def _create_tables(self):
        """建立資料表"""
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                # 建立 SmartPlaylists 資料表
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS SmartPlaylists (
                        id SERIAL PRIMARY KEY,
                        name VARCHAR(255) NOT NULL,
                        base_folder VARCHAR(255) NOT NULL,
                        filter_language VARCHAR(50),
                        filter_tags TEXT[],
                        exclude_tags TEXT[],
                        sort_by VARCHAR(50) DEFAULT 'file_creation_time',
                        is_system_level BOOLEAN DEFAULT FALSE,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)

                # 為現有表添加 is_system_level 欄位（如果不存在）
                cur.execute("""
                    DO $$
                    BEGIN
                        IF NOT EXISTS (
                            SELECT 1 FROM information_schema.columns
                            WHERE table_name='smartplaylists' AND column_name='is_system_level'
                        ) THEN
                            ALTER TABLE SmartPlaylists ADD COLUMN is_system_level BOOLEAN DEFAULT FALSE;
                        END IF;
                    END $$;
                """)

                # 建立索引
                cur.execute("""
                    CREATE INDEX IF NOT EXISTS idx_smartplaylists_name
                    ON SmartPlaylists(name)
                """)

                # 建立 Config 資料表
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS Config (
                        id SERIAL PRIMARY KEY,
                        config_key VARCHAR(100) UNIQUE NOT NULL,
                        config_value JSONB NOT NULL,
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
        conn = self.pool.getconn()
        try:
            yield conn
        finally:
            self.pool.putconn(conn)

    def get_cursor(self, conn):
        """取得 cursor (返回字典格式)"""
        return conn.cursor(cursor_factory=RealDictCursor)

    def close(self):
        """關閉連接池"""
        if self.pool:
            self.pool.closeall()
            logger.info("PostgreSQL 連接池已關閉")


# 建立全域資料庫實例
try:
    db = Database()
except Exception as e:
    logger.error(f"無法初始化資料庫: {str(e)}")
    db = None

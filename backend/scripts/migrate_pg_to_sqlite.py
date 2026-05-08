#!/usr/bin/env python3
"""
PostgreSQL to SQLite 一次性資料遷移腳本

使用方式:
    pip install psycopg2-binary  # 如果已移除，需要臨時安裝
    python migrate_pg_to_sqlite.py

環境變數:
    POSTGRES_HOST, POSTGRES_PORT, POSTGRES_DB, POSTGRES_USER, POSTGRES_PASSWORD
    SQLITE_DB_PATH (預設: /app/data/musicmanager.db)
"""

import os
import sys
import json
import sqlite3

try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
except ImportError:
    print("錯誤: 需要 psycopg2-binary 套件。請執行: pip install psycopg2-binary")
    sys.exit(1)


def connect_postgres():
    """連接到 PostgreSQL"""
    conn = psycopg2.connect(
        host=os.getenv('POSTGRES_HOST', 'localhost'),
        port=int(os.getenv('POSTGRES_PORT', 5432)),
        database=os.getenv('POSTGRES_DB', 'musicmanager'),
        user=os.getenv('POSTGRES_USER', 'musicuser'),
        password=os.getenv('POSTGRES_PASSWORD', 'musicpass')
    )
    return conn


def connect_sqlite():
    """連接到 SQLite"""
    db_path = os.getenv('SQLITE_DB_PATH', '/app/data/musicmanager.db')
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    return conn


def create_sqlite_tables(sqlite_conn):
    """在 SQLite 中建立資料表"""
    cur = sqlite_conn.cursor()

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
            filter_favorites INTEGER,
            exclude_language TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

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

    cur.execute("CREATE INDEX IF NOT EXISTS idx_smartplaylists_name ON SmartPlaylists(name)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_config_key ON Config(config_key)")

    sqlite_conn.commit()


def serialize_pg_array(value):
    """將 PostgreSQL 陣列轉為 JSON 字串"""
    if value is None or value == []:
        return None
    return json.dumps(value, ensure_ascii=False)


def migrate_playlists(pg_conn, sqlite_conn):
    """遷移 SmartPlaylists 資料"""
    pg_cur = pg_conn.cursor(cursor_factory=RealDictCursor)
    pg_cur.execute("""
        SELECT name, base_folder, filter_language, exclude_language,
               filter_tags, exclude_tags, sort_by, is_system_level,
               filter_favorites, created_at, updated_at
        FROM SmartPlaylists ORDER BY id
    """)
    rows = pg_cur.fetchall()

    sqlite_cur = sqlite_conn.cursor()
    count = 0

    for row in rows:
        sqlite_cur.execute("""
            INSERT INTO SmartPlaylists
            (name, base_folder, filter_language, exclude_language, filter_tags, exclude_tags,
             sort_by, is_system_level, filter_favorites, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            row['name'],
            row['base_folder'],
            serialize_pg_array(row.get('filter_language')),
            serialize_pg_array(row.get('exclude_language')),
            serialize_pg_array(row.get('filter_tags')),
            serialize_pg_array(row.get('exclude_tags')),
            row.get('sort_by', 'file_creation_time'),
            1 if row.get('is_system_level') else 0,
            1 if row.get('filter_favorites') else (0 if row.get('filter_favorites') is False else None),
            str(row['created_at']) if row.get('created_at') else None,
            str(row['updated_at']) if row.get('updated_at') else None,
        ))
        count += 1

    sqlite_conn.commit()
    return count


def migrate_config(pg_conn, sqlite_conn):
    """遷移 Config 資料"""
    pg_cur = pg_conn.cursor(cursor_factory=RealDictCursor)
    pg_cur.execute("SELECT config_key, config_value, description, created_at, updated_at FROM Config ORDER BY id")
    rows = pg_cur.fetchall()

    sqlite_cur = sqlite_conn.cursor()
    count = 0

    for row in rows:
        # PostgreSQL JSONB 已自動解析為 Python 物件，需轉回 JSON 字串
        config_value = json.dumps(row['config_value'], ensure_ascii=False)

        sqlite_cur.execute("""
            INSERT INTO Config (config_key, config_value, description, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?)
        """, (
            row['config_key'],
            config_value,
            row.get('description'),
            str(row['created_at']) if row.get('created_at') else None,
            str(row['updated_at']) if row.get('updated_at') else None,
        ))
        count += 1

    sqlite_conn.commit()
    return count


def main():
    print("=" * 50)
    print("PostgreSQL → SQLite 資料遷移工具")
    print("=" * 50)

    # 連接 PostgreSQL
    print("\n連接 PostgreSQL...")
    try:
        pg_conn = connect_postgres()
        print(f"  成功連接到 PostgreSQL: {os.getenv('POSTGRES_HOST', 'localhost')}")
    except Exception as e:
        print(f"  連接 PostgreSQL 失敗: {e}")
        sys.exit(1)

    # 連接 SQLite
    sqlite_db_path = os.getenv('SQLITE_DB_PATH', '/app/data/musicmanager.db')
    print(f"\n連接 SQLite: {sqlite_db_path}")
    try:
        sqlite_conn = connect_sqlite()
        print("  成功連接到 SQLite")
    except Exception as e:
        print(f"  連接 SQLite 失敗: {e}")
        pg_conn.close()
        sys.exit(1)

    # 建立資料表
    print("\n建立 SQLite 資料表...")
    create_sqlite_tables(sqlite_conn)
    print("  資料表建立完成")

    # 遷移資料
    print("\n開始遷移資料...")

    playlist_count = migrate_playlists(pg_conn, sqlite_conn)
    print(f"  SmartPlaylists: 遷移 {playlist_count} 筆資料")

    config_count = migrate_config(pg_conn, sqlite_conn)
    print(f"  Config: 遷移 {config_count} 筆資料")

    # 關閉連接
    pg_conn.close()
    sqlite_conn.close()

    print("\n" + "=" * 50)
    print(f"遷移完成！共遷移 {playlist_count + config_count} 筆資料")
    print(f"SQLite 資料庫: {sqlite_db_path}")
    print("=" * 50)


if __name__ == "__main__":
    main()

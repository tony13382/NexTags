from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, List, Any
from app.dependencies.database import db
from app.dependencies.logger import logger
import json

router = APIRouter(prefix="/config", tags=["config"])


class ConfigUpdate(BaseModel):
    config_key: str
    config_value: Any
    description: str = None


def get_config(config_key: str) -> Any:
    """從資料庫取得設定值"""
    if db is None:
        raise HTTPException(status_code=500, detail="資料庫未初始化")

    with db.get_connection() as conn:
        with db.get_cursor(conn) as cur:
            cur.execute(
                "SELECT config_value FROM Config WHERE config_key = %s",
                (config_key,)
            )
            result = cur.fetchone()
            if result:
                return result['config_value']
            return None


def set_config(config_key: str, config_value: Any, description: str = None):
    """設定或更新設定值"""
    if db is None:
        raise HTTPException(status_code=500, detail="資料庫未初始化")

    with db.get_connection() as conn:
        with db.get_cursor(conn) as cur:
            # 使用 UPSERT (INSERT ... ON CONFLICT)
            cur.execute("""
                INSERT INTO Config (config_key, config_value, description, updated_at)
                VALUES (%s, %s, %s, CURRENT_TIMESTAMP)
                ON CONFLICT (config_key)
                DO UPDATE SET
                    config_value = EXCLUDED.config_value,
                    description = EXCLUDED.description,
                    updated_at = CURRENT_TIMESTAMP
            """, (config_key, json.dumps(config_value), description))
            conn.commit()


@router.get("")
@router.get("/")
async def get_all_configs():
    """取得所有設定"""
    try:
        if db is None:
            raise HTTPException(status_code=500, detail="資料庫未初始化")

        with db.get_connection() as conn:
            with db.get_cursor(conn) as cur:
                cur.execute("SELECT config_key, config_value, description FROM Config ORDER BY config_key")
                results = cur.fetchall()

                configs = {}
                for row in results:
                    configs[row['config_key']] = row['config_value']

                return {
                    "success": True,
                    "message": "成功取得設定",
                    "data": configs
                }

    except Exception as e:
        error_msg = f"取得設定失敗: {str(e)}"
        logger.error(error_msg)
        raise HTTPException(status_code=500, detail=error_msg)


@router.get("/{config_key}")
async def get_config_by_key(config_key: str):
    """取得指定的設定"""
    try:
        config_value = get_config(config_key)
        if config_value is None:
            raise HTTPException(
                status_code=404,
                detail=f"設定 '{config_key}' 不存在"
            )

        return {
            "success": True,
            "message": f"成功取得設定 '{config_key}'",
            "data": {
                config_key: config_value
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        error_msg = f"取得設定失敗: {str(e)}"
        logger.error(error_msg)
        raise HTTPException(status_code=500, detail=error_msg)


@router.put("/{config_key}")
async def update_config(config_key: str, update: ConfigUpdate):
    """更新設定"""
    try:
        set_config(config_key, update.config_value, update.description)

        return {
            "success": True,
            "message": f"成功更新設定 '{config_key}'",
            "data": {
                config_key: update.config_value
            }
        }

    except Exception as e:
        error_msg = f"更新設定失敗: {str(e)}"
        logger.error(error_msg)
        raise HTTPException(status_code=500, detail=error_msg)


@router.post("")
@router.post("/")
async def create_or_update_config(update: ConfigUpdate):
    """建立或更新設定"""
    try:
        set_config(update.config_key, update.config_value, update.description)

        return {
            "success": True,
            "message": f"成功設定 '{update.config_key}'",
            "data": {
                update.config_key: update.config_value
            }
        }

    except Exception as e:
        error_msg = f"設定失敗: {str(e)}"
        logger.error(error_msg)
        raise HTTPException(status_code=500, detail=error_msg)


@router.delete("/{config_key}")
async def delete_config(config_key: str):
    """刪除設定"""
    try:
        if db is None:
            raise HTTPException(status_code=500, detail="資料庫未初始化")

        with db.get_connection() as conn:
            with db.get_cursor(conn) as cur:
                cur.execute(
                    "DELETE FROM Config WHERE config_key = %s RETURNING config_key",
                    (config_key,)
                )
                result = cur.fetchone()
                if not result:
                    raise HTTPException(
                        status_code=404,
                        detail=f"設定 '{config_key}' 不存在"
                    )
                conn.commit()

        return {
            "success": True,
            "message": f"成功刪除設定 '{config_key}'"
        }

    except HTTPException:
        raise
    except Exception as e:
        error_msg = f"刪除設定失敗: {str(e)}"
        logger.error(error_msg)
        raise HTTPException(status_code=500, detail=error_msg)

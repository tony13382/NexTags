from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List, Dict, Any
from app.services.task_manager import task_manager
from app.dependencies.logger import logger

router = APIRouter(prefix="/tasks", tags=["tasks"])

@router.get("/{task_id}")
async def get_task_status(task_id: str) -> Dict[str, Any]:
    """獲取任務狀態"""
    try:
        logger.info(f"查詢任務狀態: {task_id}")
        
        task_info = task_manager.get_task_status(task_id)
        
        if not task_info:
            raise HTTPException(
                status_code=404,
                detail=f"找不到任務 ID: {task_id}"
            )
        
        return {
            "success": True,
            "task": task_info
        }
        
    except HTTPException:
        raise
    except Exception as e:
        error_msg = f"查詢任務狀態失敗: {str(e)}"
        logger.error(error_msg)
        raise HTTPException(status_code=500, detail=error_msg)

@router.get("")
@router.get("/")
async def get_all_tasks(
    limit: int = Query(50, ge=1, le=200, description="返回結果數量限制"),
    task_type: Optional[str] = Query(None, description="按任務類型篩選")
) -> Dict[str, Any]:
    """獲取所有任務列表"""
    try:
        logger.info(f"查詢任務列表 - 限制: {limit}, 類型: {task_type}")
        
        all_tasks = task_manager.get_all_tasks(limit=limit)
        
        # 按任務類型篩選
        if task_type:
            filtered_tasks = [
                task for task in all_tasks 
                if task.get('task_type') == task_type
            ]
        else:
            filtered_tasks = all_tasks
        
        return {
            "success": True,
            "total_count": len(filtered_tasks),
            "tasks": filtered_tasks,
            "filter": {
                "limit": limit,
                "task_type": task_type
            }
        }
        
    except Exception as e:
        error_msg = f"查詢任務列表失敗: {str(e)}"
        logger.error(error_msg)
        raise HTTPException(status_code=500, detail=error_msg)

@router.delete("/{task_id}")
async def delete_task(task_id: str) -> Dict[str, Any]:
    """刪除任務記錄（僅限已完成或失敗的任務）"""
    try:
        logger.info(f"刪除任務: {task_id}")
        
        task_info = task_manager.get_task_status(task_id)
        
        if not task_info:
            raise HTTPException(
                status_code=404,
                detail=f"找不到任務 ID: {task_id}"
            )
        
        # 檢查任務狀態，只允許刪除已完成或失敗的任務
        if task_info['status'] in ['running', 'pending']:
            raise HTTPException(
                status_code=400,
                detail=f"無法刪除正在執行或等待中的任務"
            )
        
        # 從存儲中移除任務
        tasks = task_manager._load_tasks()
        if task_id in tasks:
            del tasks[task_id]
            task_manager._save_tasks(tasks)
        
        return {
            "success": True,
            "message": f"成功刪除任務: {task_id}",
            "deleted_task": task_info
        }
        
    except HTTPException:
        raise
    except Exception as e:
        error_msg = f"刪除任務失敗: {str(e)}"
        logger.error(error_msg)
        raise HTTPException(status_code=500, detail=error_msg)

@router.post("/cleanup")
async def cleanup_completed_tasks(
    max_age_hours: int = Query(24, ge=1, le=168, description="清理多少小時前的任務")
) -> Dict[str, Any]:
    """清理舊的已完成任務"""
    try:
        from datetime import datetime, timedelta
        
        logger.info(f"清理 {max_age_hours} 小時前的已完成任務")
        
        tasks = task_manager._load_tasks()
        cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
        
        tasks_to_delete = []
        for task_id, task_info in tasks.items():
            try:
                # 檢查任務是否已完成或失敗
                if task_info['status'] not in ['completed', 'failed']:
                    continue
                
                # 檢查任務創建時間
                created_at = datetime.fromisoformat(task_info['created_at'])
                if created_at < cutoff_time:
                    tasks_to_delete.append(task_id)
                    
            except Exception as e:
                logger.warning(f"處理任務 {task_id} 時發生錯誤: {e}")
                continue
        
        # 刪除舊任務
        for task_id in tasks_to_delete:
            del tasks[task_id]
        
        if tasks_to_delete:
            task_manager._save_tasks(tasks)
        
        return {
            "success": True,
            "message": f"成功清理 {len(tasks_to_delete)} 個舊任務",
            "cleaned_task_count": len(tasks_to_delete),
            "cutoff_hours": max_age_hours
        }
        
    except Exception as e:
        error_msg = f"清理任務失敗: {str(e)}"
        logger.error(error_msg)
        raise HTTPException(status_code=500, detail=error_msg)

@router.get("/stats/summary")
async def get_task_stats() -> Dict[str, Any]:
    """獲取任務統計摘要"""
    try:
        logger.info("查詢任務統計摘要")
        
        all_tasks = task_manager.get_all_tasks(limit=1000)  # 獲取更多任務進行統計
        
        # 統計各狀態的任務數量
        stats = {
            "pending": 0,
            "running": 0,
            "completed": 0,
            "failed": 0
        }
        
        task_types = {}
        
        for task in all_tasks:
            status = task.get('status', 'unknown')
            task_type = task.get('task_type', 'unknown')
            
            if status in stats:
                stats[status] += 1
            
            if task_type not in task_types:
                task_types[task_type] = {
                    "total": 0,
                    "completed": 0,
                    "failed": 0
                }
            
            task_types[task_type]["total"] += 1
            if status == "completed":
                task_types[task_type]["completed"] += 1
            elif status == "failed":
                task_types[task_type]["failed"] += 1
        
        return {
            "success": True,
            "summary": {
                "total_tasks": len(all_tasks),
                "status_counts": stats,
                "task_types": task_types,
                "active_tasks": stats["pending"] + stats["running"]
            }
        }
        
    except Exception as e:
        error_msg = f"查詢任務統計失敗: {str(e)}"
        logger.error(error_msg)
        raise HTTPException(status_code=500, detail=error_msg)
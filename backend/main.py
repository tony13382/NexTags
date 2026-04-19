from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.router.audio import router as audios_router
from app.router.tools import router as tools_router
from app.router.tags import router as tags_router
from app.router.images import router as images_router
from app.router.playlists import router as playlists_router
from app.router.cache import router as cache_router
from app.router.music_import import router as music_import_router
from app.router.tasks import router as tasks_router
from app.router.config import router as config_router
from app.dependencies.logger import logger

app = FastAPI(
    title="NexTags API",
    description="Backend API for NexTags",
    version="0.1.0",
    # 禁用自动重定向尾部斜杠，避免与 nginx 代理冲突
    redirect_slashes=False
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 添加 /api 前缀到所有路由
app.include_router(audios_router, prefix="/api")
app.include_router(tools_router, prefix="/api")
app.include_router(tags_router, prefix="/api")
app.include_router(images_router, prefix="/api")
app.include_router(playlists_router, prefix="/api")
app.include_router(cache_router, prefix="/api")
app.include_router(music_import_router, prefix="/api")
app.include_router(tasks_router, prefix="/api")
app.include_router(config_router, prefix="/api")

@app.on_event("startup")
async def startup_event():
    logger.info("=== NexTags API 啟動 ===")
    logger.info("API 版本: 0.1.0")
    
    # 啟動背景任務工作器
    from app.services.task_manager import task_manager
    import asyncio
    asyncio.create_task(task_manager.start_worker())
    logger.info("背景任務工作器已啟動")
    
    logger.info("伺服器已準備就緒，等待請求...")

@app.on_event("shutdown")  
async def shutdown_event():
    logger.info("NexTags API 正在關閉...")
    
    # 停止背景任務工作器
    from app.services.task_manager import task_manager
    task_manager.stop_worker()
    logger.info("背景任務工作器已停止")

@app.get("/")
async def root():
    return {"message": "NexTags API"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

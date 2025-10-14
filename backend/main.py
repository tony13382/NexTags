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
    title="Personal Music Manager API",
    description="Backend API for Personal Music Manager",
    version="0.1.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(audios_router)
app.include_router(tools_router)
app.include_router(tags_router)
app.include_router(images_router)
app.include_router(playlists_router)
app.include_router(cache_router)
app.include_router(music_import_router)
app.include_router(tasks_router)
app.include_router(config_router)

@app.on_event("startup")
async def startup_event():
    logger.info("=== Personal Music Manager API 啟動 ===")
    logger.info("API 版本: 0.1.0")
    
    # 啟動背景任務工作器
    from app.services.task_manager import task_manager
    import asyncio
    asyncio.create_task(task_manager.start_worker())
    logger.info("背景任務工作器已啟動")
    
    logger.info("伺服器已準備就緒，等待請求...")

@app.on_event("shutdown")  
async def shutdown_event():
    logger.info("Personal Music Manager API 正在關閉...")
    
    # 停止背景任務工作器
    from app.services.task_manager import task_manager
    task_manager.stop_worker()
    logger.info("背景任務工作器已停止")

@app.get("/")
async def root():
    return {"message": "Personal Music Manager API"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

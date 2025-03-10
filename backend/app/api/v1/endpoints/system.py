from fastapi import APIRouter, HTTPException, Depends, Query, Path, Body, status
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime

from app.core.db import get_database_stats, get_collection
from app.core.logging import get_logger
from app.core.migrations import migration_manager
from app.tasks.scheduler import scheduler_manager

logger = get_logger("app.api.system")

router = APIRouter()

#--- مدل‌های پاسخ ---

class SystemStatusResponse(BaseModel):
    """مدل وضعیت سیستم"""
    status: str
    version: str
    environment: str
    uptime_seconds: float
    database: Dict[str, Any]
    scheduler: Dict[str, Any]

class SystemStatsResponse(BaseModel):
    """مدل آمار سیستم"""
    database: Dict[str, Any]
    tweets: Dict[str, Any]
    keywords: Dict[str, Any]
    system: Dict[str, Any]
    timestamp: datetime

class ExecutionLogResponse(BaseModel):
    """مدل لاگ اجرا"""
    id: str
    task_name: str
    status: str
    start_time: datetime
    end_time: Optional[datetime]
    duration_seconds: float
    result: Optional[Dict[str, Any]]

class ExecutionLogsResponse(BaseModel):
    """مدل لیست لاگ‌های اجرا"""
    total: int
    logs: List[ExecutionLogResponse]

class MigrationStatusResponse(BaseModel):
    """مدل وضعیت میگریشن‌ها"""
    total: int
    applied: int
    pending: int
    migrations: List[Dict[str, Any]]

class MigrationRunRequest(BaseModel):
    """مدل درخواست اجرای میگریشن"""
    target_version: Optional[str] = None

class MigrationRunResponse(BaseModel):
    """مدل پاسخ اجرای میگریشن"""
    status: str
    applied: List[Dict[str, Any]]
    timestamp: datetime

#--- روت‌های API ---

@router.get("/status", response_model=SystemStatusResponse, summary="Get system status")
async def get_system_status():
    """
    دریافت وضعیت کلی سیستم:
    - وضعیت دیتابیس
    - وضعیت زمان‌بند
    - زمان روشن بودن سیستم
    """
    from app.core.config import settings
    from app.core.db import db
    import time
    
    # زمان شروع (از متغیر محیطی یا زمان فعلی)
    start_time = float(os.environ.get("APP_START_TIME", time.time()))
    uptime = time.time() - start_time
    
    return {
        "status": "ok",
        "version": settings.VERSION,
        "environment": settings.ENVIRONMENT,
        "uptime_seconds": uptime,
        "database": db.get_db_info(),
        "scheduler": scheduler_manager.get_status()
    }

@router.get("/stats", response_model=SystemStatsResponse, summary="Get system statistics")
async def get_system_stats():
    """
    دریافت آمار کلی سیستم:
    - آمار دیتابیس
    - آمار توییت‌ها
    - آمار کلمات کلیدی
    - آمار سیستم
    """
    try:
        # دریافت آمار دیتابیس
        db_stats = await get_database_stats()
        
        # دریافت آمار توییت‌ها
        tweets_collection = get_collection("tweets")
        total_tweets = await tweets_collection.count_documents({})
        
        # آمار توییت‌های امروز
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        tweets_today = await tweets_collection.count_documents({"created_at": {"$gte": today_start}})
        
        # دریافت آمار کلمات کلیدی
        keywords_collection = get_collection("keywords")
        total_keywords = await keywords_collection.count_documents({})
        active_keywords = await keywords_collection.count_documents({"is_active": True})
        
        # دریافت آمار سیستم
        from app.tasks.maintenance_tasks import get_memory_usage, get_cpu_usage
        
        return {
            "database": {
                "size_mb": round(db_stats["database_size"] / (1024 * 1024), 2),
                "storage_mb": round(db_stats["storage_size"] / (1024 * 1024), 2),
                "collections": db_stats["collections"],
                "objects": db_stats["objects"]
            },
            "tweets": {
                "total": total_tweets,
                "today": tweets_today
            },
            "keywords": {
                "total": total_keywords,
                "active": active_keywords
            },
            "system": {
                "memory_mb": get_memory_usage(),
                "cpu_percent": get_cpu_usage()
            },
            "timestamp": datetime.utcnow()
        }
    
    except Exception as e:
        logger.error(f"Error getting system stats: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error getting system stats: {str(e)}"
        )

@router.get("/executions", response_model=ExecutionLogsResponse, summary="Get execution logs")
async def get_execution_logs(
    task_name: Optional[str] = Query(None, description="Filter by task name"),
    status: Optional[str] = Query(None, description="Filter by status"),
    limit: int = Query(10, ge=1, le=100, description="Number of logs to return"),
    skip: int = Query(0, ge=0, description="Number of logs to skip")
):
    """
    دریافت لاگ‌های اجرای کارها با قابلیت فیلتر:
    - نام کار
    - وضعیت اجرا
    """
    try:
        execution_logs = get_collection("execution_logs")
        
        # ساخت کوئری
        query = {}
        if task_name:
            query["task_name"] = task_name
        if status:
            query["status"] = status
        
        # دریافت تعداد کل
        total = await execution_logs.count_documents(query)
        
        # دریافت لاگ‌ها
        cursor = execution_logs.find(query).sort("start_time", -1).skip(skip).limit(limit)
        logs = await cursor.to_list(length=limit)
        
        # تبدیل _id به id
        for log in logs:
            log["id"] = str(log.pop("_id"))
        
        return {
            "total": total,
            "logs": logs
        }
    
    except Exception as e:
        logger.error(f"Error getting execution logs: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error getting execution logs: {str(e)}"
        )

@router.get("/migrations", response_model=MigrationStatusResponse, summary="Get migrations status")
async def get_migrations_status():
    """
    دریافت وضعیت میگریشن‌های دیتابیس:
    - تعداد کل میگریشن‌ها
    - تعداد میگریشن‌های اعمال شده
    - تعداد میگریشن‌های معلق
    - لیست میگریشن‌ها با وضعیت
    """
    try:
        # دریافت وضعیت میگریشن‌ها
        migrations = await migration_manager.get_migrations_status()
        
        # محاسبه آمار
        total = len(migrations)
        applied = sum(1 for m in migrations if m["applied"])
        pending = total - applied
        
        return {
            "total": total,
            "applied": applied,
            "pending": pending,
            "migrations": migrations
        }
    
    except Exception as e:
        logger.error(f"Error getting migrations status: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error getting migrations status: {str(e)}"
        )

@router.post("/migrations/run", response_model=MigrationRunResponse, summary="Run database migrations")
async def run_migrations(
    request: MigrationRunRequest = Body(...)
):
    """
    اجرای میگریشن‌های دیتابیس:
    - اجرای تمام میگریشن‌های معلق
    - یا اجرای میگریشن‌ها تا نسخه مشخص
    """
    try:
        # اجرای میگریشن‌ها
        result = await migration_manager.migrate(request.target_version)
        
        return {
            "status": "success",
            "applied": result,
            "timestamp": datetime.utcnow()
        }
    
    except Exception as e:
        logger.error(f"Error running migrations: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error running migrations: {str(e)}"
        )

import os # برای دریافت زمان شروع برنامه
from app.tasks.scheduler import scheduler_manager

@router.get("/scheduler/jobs", summary="Get scheduler jobs")
async def get_scheduler_jobs():
    """
    دریافت لیست کارهای زمان‌بند:
    - نام کار
    - زمان اجرای بعدی
    - وضعیت کار
    """
    try:
        if not scheduler_manager.is_running():
            return {"status": "scheduler_not_running", "jobs": []}
        
        jobs = scheduler_manager.get_jobs()
        
        return {
            "status": "ok",
            "jobs": jobs
        }
    
    except Exception as e:
        logger.error(f"Error getting scheduler jobs: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error getting scheduler jobs: {str(e)}"
        )

@router.post("/scheduler/jobs/{job_id}/pause", summary="Pause a scheduler job")
async def pause_scheduler_job(
    job_id: str = Path(..., description="Job ID")
):
    """
    متوقف کردن موقت یک کار زمان‌بند
    """
    try:
        if not scheduler_manager.is_running():
            raise HTTPException(
                status_code=400,
                detail="Scheduler is not running"
            )
        
        result = scheduler_manager.pause_job(job_id)
        
        if result:
            return {"status": "success", "message": f"Job {job_id} paused"}
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Failed to pause job {job_id}"
            )
    
    except Exception as e:
        logger.error(f"Error pausing job {job_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error pausing job: {str(e)}"
        )

@router.post("/scheduler/jobs/{job_id}/resume", summary="Resume a scheduler job")
async def resume_scheduler_job(
    job_id: str = Path(..., description="Job ID")
):
    """
    ازسرگیری یک کار زمان‌بند متوقف شده
    """
    try:
        if not scheduler_manager.is_running():
            raise HTTPException(
                status_code=400,
                detail="Scheduler is not running"
            )
        
        result = scheduler_manager.resume_job(job_id)
        
        if result:
            return {"status": "success", "message": f"Job {job_id} resumed"}
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Failed to resume job {job_id}"
            )
    
    except Exception as e:
        logger.error(f"Error resuming job {job_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error resuming job: {str(e)}"
        )

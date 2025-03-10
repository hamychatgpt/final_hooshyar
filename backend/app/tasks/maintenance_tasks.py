from datetime import datetime, timedelta
import json
import os
import asyncio
from typing import Dict, Any, List, Optional
from app.core.db import get_collection, get_database_stats
from app.core.logging import get_logger
from app.core.config import settings

logger = get_logger("app.tasks.maintenance_tasks")

async def cleanup_old_data():
    """پاکسازی داده‌های قدیمی برای مدیریت حجم دیتابیس
    
    این تابع داده‌های قدیمی را که نیاز به نگهداری ندارند حذف می‌کند.
    - توییت‌های قدیمی با اهمیت پایین
    - آمارهای قدیمی سیستم
    - لاگ‌های اجرای قدیمی
    """
    try:
        logger.info("Starting cleanup of old data")
        
        # پاکسازی توییت‌های قدیمی با اهمیت پایین
        await cleanup_old_tweets()
        
        # پاکسازی لاگ‌های قدیمی اجرا
        await cleanup_old_execution_logs()
        
        # فشرده‌سازی کالکشن‌ها
        await compact_collections()
        
        logger.info("Old data cleanup completed successfully")
        
        return {
            "status": "success",
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error during old data cleanup: {e}")
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }

async def cleanup_old_tweets():
    """پاکسازی توییت‌های قدیمی با اهمیت پایین"""
    try:
        tweets_collection = get_collection("tweets")
        
        # تعیین آستانه زمانی برای حذف (مثلاً 90 روز)
        threshold_date = datetime.utcnow() - timedelta(days=90)
        
        # پیدا کردن و حذف توییت‌های قدیمی با اهمیت پایین
        # فقط توییت‌های با اهمیت کمتر از 10 را حذف می‌کنیم
        result = await tweets_collection.delete_many({
            "created_at": {"$lt": threshold_date},
            "importance_score": {"$lt": 10}
        })
        
        logger.info(f"Deleted {result.deleted_count} old tweets with low importance")
        
    except Exception as e:
        logger.error(f"Error cleaning up old tweets: {e}")
        raise

async def cleanup_old_execution_logs():
    """پاکسازی لاگ‌های قدیمی اجرا"""
    try:
        execution_logs_collection = get_collection("execution_logs")
        
        # تعیین آستانه زمانی برای حذف (مثلاً 30 روز)
        threshold_date = datetime.utcnow() - timedelta(days=30)
        
        # حذف لاگ‌های قدیمی
        result = await execution_logs_collection.delete_many({
            "timestamp": {"$lt": threshold_date}
        })
        
        logger.info(f"Deleted {result.deleted_count} old execution logs")
        
    except Exception as e:
        logger.error(f"Error cleaning up old execution logs: {e}")
        # اگر کالکشن وجود نداشته باشد، نادیده می‌گیریم
        if "ns not found" not in str(e):
            raise

async def compact_collections():
    """فشرده‌سازی کالکشن‌ها برای آزادسازی فضا"""
    try:
        # دریافت لیست کالکشن‌ها
        db = get_collection("tweets").database
        collections = await db.list_collection_names()
        
        for collection_name in collections:
            try:
                # اجرای دستور compact
                await db.command({"compact": collection_name})
                logger.info(f"Compacted collection: {collection_name}")
            except Exception as e:
                logger.warning(f"Failed to compact collection {collection_name}: {e}")
                
    except Exception as e:
        logger.error(f"Error during collections compaction: {e}")
        raise

async def update_system_stats():
    """به‌روزرسانی آمار سیستم
    
    این تابع آمار کلی سیستم را جمع‌آوری و در دیتابیس ذخیره می‌کند.
    """
    try:
        logger.info("Updating system statistics")
        
        # دریافت آمار دیتابیس
        db_stats = await get_database_stats()
        
        # دریافت آمار توییت‌ها
        tweets_collection = get_collection("tweets")
        keywords_collection = get_collection("keywords")
        
        total_tweets = await tweets_collection.count_documents({})
        
        # تعداد توییت‌های امروز
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        tweets_today = await tweets_collection.count_documents({"created_at": {"$gte": today_start}})
        
        # تعداد توییت‌های 24 ساعت اخیر
        last_24h = datetime.utcnow() - timedelta(hours=24)
        tweets_last_24h = await tweets_collection.count_documents({"created_at": {"$gte": last_24h}})
        
        # آمار کلمات کلیدی
        total_keywords = await keywords_collection.count_documents({})
        active_keywords = await keywords_collection.count_documents({"is_active": True})
        
        # جمع‌آوری آمار سیستم
        stats = {
            "timestamp": datetime.utcnow(),
            "date": datetime.utcnow().date().isoformat(),
            "database": {
                "size_mb": round(db_stats["database_size"] / (1024 * 1024), 2),
                "storage_mb": round(db_stats["storage_size"] / (1024 * 1024), 2),
                "collections": db_stats["collections"],
                "objects": db_stats["objects"]
            },
            "tweets": {
                "total": total_tweets,
                "today": tweets_today,
                "last_24h": tweets_last_24h
            },
            "keywords": {
                "total": total_keywords,
                "active": active_keywords
            },
            "system": {
                "memory_mb": get_memory_usage(),
                "cpu_percent": get_cpu_usage()
            }
        }
        
        # ذخیره آمار در دیتابیس
        stats_collection = get_collection("system_stats")
        
        # بررسی وجود آمار برای امروز
        today_stats = await stats_collection.find_one({"date": stats["date"]})
        
        if today_stats:
            # به‌روزرسانی آمار امروز
            await stats_collection.update_one(
                {"date": stats["date"]},
                {"$set": stats}
            )
        else:
            # ایجاد آمار جدید
            await stats_collection.insert_one(stats)
        
        logger.info("System statistics updated successfully")
        
        return {
            "status": "success",
            "stats": stats
        }
        
    except Exception as e:
        logger.error(f"Error updating system statistics: {e}")
        return {
            "status": "error",
            "error": str(e)
        }

def get_memory_usage() -> float:
    """دریافت میزان استفاده از حافظه (MB)"""
    try:
        import psutil
        process = psutil.Process(os.getpid())
        memory_info = process.memory_info()
        return round(memory_info.rss / (1024 * 1024), 2)  # تبدیل به مگابایت
    except:
        return 0.0

def get_cpu_usage() -> float:
    """دریافت میزان استفاده از پردازنده (درصد)"""
    try:
        import psutil
        return psutil.cpu_percent(interval=0.1)
    except:
        return 0.0

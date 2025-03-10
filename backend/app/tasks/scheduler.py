import logging
import asyncio
from datetime import datetime, timedelta
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.mongodb import MongoDBJobStore
from apscheduler.executors.pool import ThreadPoolExecutor, ProcessPoolExecutor
from apscheduler.triggers.interval import IntervalTrigger

from app.core.db import db
from app.tasks.twitter_tasks import extract_tweets_for_all_keywords, update_tweet_stats

logger = logging.getLogger(__name__)

# Create scheduler instance
scheduler = AsyncIOScheduler()


async def setup_scheduler():
    """Set up the scheduler with MongoDB job store and default jobs"""
    logger.info("Setting up scheduler...")
    
    # Wait for MongoDB connection
    while db.client is None:
        await asyncio.sleep(1)
    
    # Configure scheduler with MongoDB job store
    jobstores = {
        'default': MongoDBJobStore(
            database=db.db.name, 
            collection='scheduler_jobs',
            client=db.client
        )
    }
    
    executors = {
        'default': ThreadPoolExecutor(20),
        'processpool': ProcessPoolExecutor(5)
    }
    
    job_defaults = {
        'coalesce': False,
        'max_instances': 3,
        'misfire_grace_time': 3600  # 1 hour
    }
    
    scheduler.configure(
        jobstores=jobstores,
        executors=executors,
        job_defaults=job_defaults
    )
    
    # Add default jobs
    scheduler.add_job(
        extract_tweets_for_all_keywords,
        trigger=IntervalTrigger(minutes=15),  # Run every 15 minutes
        id='extract_tweets_job',
        replace_existing=True,
        name='Extract tweets for all active keywords'
    )
    
    scheduler.add_job(
        update_tweet_stats,
        trigger=IntervalTrigger(minutes=60),  # Run every hour
        id='update_tweet_stats_job',
        replace_existing=True,
        name='Update tweet statistics'
    )
    
    # Start scheduler
    scheduler.start()
    logger.info("Scheduler started")


async def shutdown_scheduler():
    """Shutdown the scheduler"""
    logger.info("Shutting down scheduler...")
    if scheduler.running:
        scheduler.shutdown()
        logger.info("Scheduler shut down")


class SchedulerManager:
    """مدیریت زمان‌بند وظایف"""
    
    def __init__(self, scheduler_instance):
        self.scheduler = scheduler_instance
    
    def is_running(self):
        """بررسی وضعیت اجرای زمان‌بند"""
        return self.scheduler.running if self.scheduler else False
    
    def get_jobs(self):
        """دریافت لیست کارهای زمان‌بند"""
        if not self.scheduler or not self.scheduler.running:
            return []
        
        jobs = []
        for job in self.scheduler.get_jobs():
            jobs.append({
                "id": job.id,
                "name": job.name,
                "next_run_time": job.next_run_time.isoformat() if job.next_run_time else None,
                "func": f"{job.func.__module__}.{job.func.__name__}",
                "trigger": str(job.trigger),
                "paused": job.next_run_time is None
            })
        
        return jobs
    
    def get_status(self):
        """دریافت وضعیت زمان‌بند"""
        return {
            "running": self.is_running(),
            "job_count": len(self.get_jobs()) if self.is_running() else 0,
            "scheduler_type": "AsyncIOScheduler"
        }
    
    def pause_job(self, job_id):
        """توقف موقت یک کار"""
        if not self.scheduler or not self.scheduler.running:
            return False
        
        job = self.scheduler.get_job(job_id)
        if not job:
            return False
        
        self.scheduler.pause_job(job_id)
        return True
    
    def resume_job(self, job_id):
        """ازسرگیری یک کار"""
        if not self.scheduler or not self.scheduler.running:
            return False
        
        job = self.scheduler.get_job(job_id)
        if not job:
            return False
        
        self.scheduler.resume_job(job_id)
        return True

# نمونه سینگلتون از مدیر زمان‌بند
scheduler_manager = SchedulerManager(scheduler)
import logging
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

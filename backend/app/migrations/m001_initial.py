from app.core.migrations import Migration
from app.core.db import get_collection, db
from app.core.logging import get_logger

logger = get_logger("app.migrations.m001_initial")

class InitialMigration(Migration):
    """میگریشن اولیه برای ایجاد ساختار دیتابیس"""
    version = "001"
    description = "Initial database structure"
    
    async def up(self):
        """ایجاد ساختار اولیه دیتابیس"""
        logger.info("Running initial migration")
        
        # ایجاد کالکشن توییت‌ها
        tweets_collection = get_collection("tweets")
        await tweets_collection.create_index("tweet_id", unique=True)
        await tweets_collection.create_index("created_at")
        await tweets_collection.create_index("keywords")
        await tweets_collection.create_index("user_id")
        await tweets_collection.create_index("importance_score")
        await tweets_collection.create_index([("text", "text")], default_language="none")
        
        # ایجاد کالکشن کلمات کلیدی
        keywords_collection = get_collection("keywords")
        await keywords_collection.create_index("keyword", unique=True)
        await keywords_collection.create_index("is_active")
        await keywords_collection.create_index("priority")
        await keywords_collection.create_index("last_extracted_at")
        
        # ایجاد کالکشن آمار
        stats_collection = get_collection("stats")
        await stats_collection.create_index("date", unique=True)
        
        # ایجاد کالکشن تنظیمات سیستم
        settings_collection = get_collection("system_settings")
        await settings_collection.create_index("key", unique=True)
        
        # تنظیمات پیش‌فرض سیستم
        default_settings = [
            {"key": "extraction_enabled", "value": True, "description": "Enable automatic tweet extraction"},
            {"key": "max_extraction_per_hour", "value": 5, "description": "Maximum extraction runs per hour"},
            {"key": "default_language", "value": "fa", "description": "Default language for tweet extraction"},
            {"key": "system_initialized", "value": True, "description": "System initialization status"}
        ]
        
        # اضافه کردن تنظیمات پیش‌فرض
        for setting in default_settings:
            await settings_collection.update_one(
                {"key": setting["key"]},
                {"$set": setting},
                upsert=True
            )
        
        logger.info("Initial migration completed successfully")
    
    async def down(self):
        """برگشت میگریشن اولیه - حذف ساختار دیتابیس"""
        logger.info("Rolling back initial migration")
        
        # حذف کالکشن‌ها
        try:
            await db.db.drop_collection("tweets")
            await db.db.drop_collection("keywords")
            await db.db.drop_collection("stats")
            await db.db.drop_collection("system_settings")
            
            logger.info("Initial migration rolled back successfully")
            
        except Exception as e:
            logger.error(f"Error rolling back initial migration: {e}")
            raise

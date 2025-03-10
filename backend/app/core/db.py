import asyncio
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase, AsyncIOMotorCollection
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
from typing import Dict, Any, Optional, List
from app.core.config import settings
from app.core.logging import get_logger, DatabaseError

logger = get_logger("app.core.db")

class MongoDB:
    """کلاس مدیریت اتصال MongoDB"""
    client: AsyncIOMotorClient = None
    db: AsyncIOMotorDatabase = None
    
    # کش برای نگه داشتن کالکشن ها
    _collections: Dict[str, AsyncIOMotorCollection] = {}
    
    # شمارنده تلاش های اتصال
    _connection_attempts: int = 0
    MAX_CONNECTION_ATTEMPTS: int = 5
    
    def get_collection(self, name: str) -> AsyncIOMotorCollection:
        """دریافت کالکشن با کش کردن"""
        if name not in self._collections:
            if not self.db:
                raise DatabaseError("Database connection not initialized")
            self._collections[name] = self.db[name]
        return self._collections[name]
    
    async def ping(self) -> bool:
        """تست اتصال به دیتابیس"""
        try:
            if self.client:
                await self.client.admin.command('ping')
                return True
            return False
        except Exception:
            return False
    
    def get_db_info(self) -> Dict[str, Any]:
        """دریافت اطلاعات دیتابیس برای گزارش وضعیت"""
        info = {
            "connected": self.client is not None,
            "database": settings.MONGODB_DB,
            "collections": list(self._collections.keys()) if self._collections else []
        }
        return info

db = MongoDB()

async def connect_to_mongo() -> None:
    """اتصال به MongoDB با مکانیزم تلاش مجدد"""
    logger.info("Connecting to MongoDB...")
    
    while db._connection_attempts < db.MAX_CONNECTION_ATTEMPTS:
        try:
            # تنظیم تایم اوت کوتاه تر برای تشخیص سریع مشکلات اتصال
            db.client = AsyncIOMotorClient(
                settings.MONGODB_URI, 
                serverSelectionTimeoutMS=5000
            )
            await db.client.admin.command('ping')
            db.db = db.client[settings.MONGODB_DB]
            
            logger.info(f"Connected to MongoDB: {settings.MONGODB_DB}")
            await create_indexes()
            return
        
        except (ConnectionFailure, ServerSelectionTimeoutError) as e:
            db._connection_attempts += 1
            wait_time = min(2 ** db._connection_attempts, 60)  # تاخیر نمایی با حداکثر 60 ثانیه
            
            logger.error(
                f"Could not connect to MongoDB (attempt {db._connection_attempts}/{db.MAX_CONNECTION_ATTEMPTS}): {e}"
            )
            
            if db._connection_attempts >= db.MAX_CONNECTION_ATTEMPTS:
                logger.critical("Max connection attempts reached. Could not connect to MongoDB.")
                raise DatabaseError("Failed to connect to MongoDB after multiple attempts", detail={"error": str(e)})
            
            logger.info(f"Retrying in {wait_time} seconds...")
            await asyncio.sleep(wait_time)
            
        except Exception as e:
            logger.critical(f"Unexpected error connecting to MongoDB: {e}")
            raise DatabaseError("Unexpected error connecting to MongoDB", detail={"error": str(e)})

async def close_mongo_connection() -> None:
    """بستن اتصال MongoDB"""
    logger.info("Closing MongoDB connection...")
    if db.client:
        db.client.close()
        db.client = None
        db._collections = {}
        db._connection_attempts = 0
        logger.info("MongoDB connection closed")

async def create_indexes() -> None:
    """ایجاد ایندکس‌های مورد نیاز"""
    try:
        # ایندکس های توییت ها
        await db.get_collection("tweets").create_index("tweet_id", unique=True)
        await db.get_collection("tweets").create_index("created_at")
        await db.get_collection("tweets").create_index("keywords")
        await db.get_collection("tweets").create_index("user_id")
        await db.get_collection("tweets").create_index("importance_score")
        await db.get_collection("tweets").create_index([("text", "text")], default_language="none") 
        
        # برای بهبود عملکرد جستجوهای رایج
        await db.get_collection("tweets").create_index([
            ("created_at", -1), 
            ("importance_score", -1)
        ])
        
        # ایندکس ترکیبی برای فیلتر کاربر و زمان
        await db.get_collection("tweets").create_index([
            ("user_screen_name", 1), 
            ("created_at", -1)
        ])
        
        # ایندکس های کلمات کلیدی
        await db.get_collection("keywords").create_index("keyword", unique=True)
        await db.get_collection("keywords").create_index("is_active")
        await db.get_collection("keywords").create_index("priority")
        await db.get_collection("keywords").create_index("last_extracted_at")
        
        # ایندکس ترکیبی برای فیلترهای رایج
        await db.get_collection("keywords").create_index([
            ("is_active", 1), 
            ("priority", 1)
        ])
        
        logger.info("All database indexes created successfully")
    except Exception as e:
        logger.error(f"Error creating database indexes: {e}")
        raise DatabaseError("Failed to create database indexes", detail={"error": str(e)})

def get_collection(collection_name: str) -> AsyncIOMotorCollection:
    """دسترسی به کالکشن با بررسی اتصال"""
    if not db.client or not db.db:
        logger.error("Attempting to get collection without database connection")
        raise DatabaseError("Database not connected")
    
    return db.get_collection(collection_name)

async def get_database_stats() -> Dict[str, Any]:
    """دریافت آمار دیتابیس برای مانیتورینگ"""
    if not db.client or not db.db:
        raise DatabaseError("Database not connected")
    
    try:
        # دریافت آمار کلی دیتابیس
        db_stats = await db.db.command("dbStats")
        
        # دریافت اندازه و تعداد اسناد برای هر کالکشن
        collections_stats = {}
        collections = await db.db.list_collection_names()
        
        for collection_name in collections:
            collection_stats = await db.db.command("collStats", collection_name)
            collections_stats[collection_name] = {
                "count": collection_stats.get("count", 0),
                "size": collection_stats.get("size", 0),
                "avg_document_size": collection_stats.get("avgObjSize", 0)
            }
        
        # ترکیب آمار
        stats = {
            "database_size": db_stats.get("dataSize", 0),
            "storage_size": db_stats.get("storageSize", 0),
            "collections": len(collections),
            "objects": db_stats.get("objects", 0),
            "collections_stats": collections_stats
        }
        
        return stats
    
    except Exception as e:
        logger.error(f"Error getting database stats: {e}")
        raise DatabaseError("Failed to get database stats", detail={"error": str(e)})

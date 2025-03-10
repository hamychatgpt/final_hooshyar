import asyncio
import importlib
import os
import pkgutil
import inspect
from datetime import datetime
from typing import List, Dict, Any, Optional, Callable, Awaitable
from app.core.db import get_collection, db
from app.core.logging import get_logger, DatabaseError

logger = get_logger("app.core.migrations")

class Migration:
    """کلاس پایه برای میگریشن های دیتابیس"""
    version: str
    description: str
    
    async def up(self) -> None:
        """اجرای میگریشن"""
        raise NotImplementedError("Migration.up must be implemented")
    
    async def down(self) -> None:
        """برگشت میگریشن"""
        raise NotImplementedError("Migration.down must be implemented")

class MigrationManager:
    """مدیریت میگریشن های دیتابیس"""
    def __init__(self, migrations_package: str = "app.migrations"):
        self.migrations_package = migrations_package
        self.migrations: List[Migration] = []
        self._loaded = False
    
    async def _ensure_migration_collection(self) -> None:
        """اطمینان از وجود کالکشن میگریشن"""
        try:
            # ایجاد کالکشن میگریشن اگر وجود ندارد
            collections = await db.db.list_collection_names()
            if "migrations" not in collections:
                await db.db.create_collection("migrations")
                
                # ایجاد ایندکس یکتا برای نسخه
                await db.get_collection("migrations").create_index("version", unique=True)
        
        except Exception as e:
            logger.error(f"Error creating migrations collection: {e}")
            raise DatabaseError("Failed to create migrations collection", detail={"error": str(e)})
    
    def _load_migrations(self) -> None:
        """بارگیری میگریشن ها از پکیج میگریشن"""
        if self._loaded:
            return
        
        try:
            # بارگیری ماژول میگریشن
            migrations_module = importlib.import_module(self.migrations_package)
            migrations_path = os.path.dirname(migrations_module.__file__)
            
            # پیدا کردن تمام میگریشن ها در پکیج
            for _, name, is_pkg in pkgutil.iter_modules([migrations_path]):
                if not is_pkg:
                    # بارگیری ماژول میگریشن
                    module_name = f"{self.migrations_package}.{name}"
                    migration_module = importlib.import_module(module_name)
                    
                    # پیدا کردن کلاس میگریشن
                    for item_name, item in migration_module.__dict__.items():
                        if (
                            inspect.isclass(item) 
                            and issubclass(item, Migration) 
                            and item != Migration
                        ):
                            # افزودن نمونه از کلاس میگریشن
                            self.migrations.append(item())
            
            # مرتب سازی میگریشن ها بر اساس نسخه
            self.migrations.sort(key=lambda m: m.version)
            self._loaded = True
            
            logger.info(f"Loaded {len(self.migrations)} migrations")
            
        except Exception as e:
            logger.error(f"Error loading migrations: {e}")
            raise DatabaseError("Failed to load migrations", detail={"error": str(e)})
    
    async def get_applied_migrations(self) -> Dict[str, Dict[str, Any]]:
        """دریافت میگریشن های اعمال شده"""
        await self._ensure_migration_collection()
        
        # دریافت میگریشن های اعمال شده از دیتابیس
        migrations_collection = get_collection("migrations")
        cursor = migrations_collection.find().sort("version", 1)
        applied_migrations = {doc["version"]: doc async for doc in cursor}
        
        return applied_migrations
    
    async def get_migrations_status(self) -> List[Dict[str, Any]]:
        """دریافت وضعیت تمام میگریشن ها"""
        self._load_migrations()
        applied_migrations = await self.get_applied_migrations()
        
        # ترکیب وضعیت میگریشن های موجود و اعمال شده
        result = []
        for migration in self.migrations:
            applied = migration.version in applied_migrations
            applied_at = None
            
            if applied:
                applied_at = applied_migrations[migration.version].get("applied_at")
            
            result.append({
                "version": migration.version,
                "description": migration.description,
                "applied": applied,
                "applied_at": applied_at
            })
        
        return result
    
    async def migrate(self, target_version: Optional[str] = None) -> List[Dict[str, Any]]:
        """اجرای میگریشن ها تا نسخه مشخص"""
        self._load_migrations()
        await self._ensure_migration_collection()
        
        applied_migrations = await self.get_applied_migrations()
        migrations_collection = get_collection("migrations")
        result = []
        
        # تعیین میگریشن هدف
        target_index = len(self.migrations)
        if target_version:
            for i, migration in enumerate(self.migrations):
                if migration.version == target_version:
                    target_index = i + 1
                    break
        
        # اجرای میگریشن های معلق
        for i, migration in enumerate(self.migrations[:target_index]):
            if migration.version not in applied_migrations:
                logger.info(f"Applying migration {migration.version}: {migration.description}")
                
                try:
                    # اجرای میگریشن
                    await migration.up()
                    
                    # ثبت میگریشن
                    await migrations_collection.insert_one({
                        "version": migration.version,
                        "description": migration.description,
                        "applied_at": datetime.utcnow()
                    })
                    
                    result.append({
                        "version": migration.version,
                        "description": migration.description,
                        "status": "success"
                    })
                    
                    logger.info(f"Migration {migration.version} applied successfully")
                    
                except Exception as e:
                    logger.error(f"Error applying migration {migration.version}: {e}")
                    result.append({
                        "version": migration.version,
                        "description": migration.description,
                        "status": "error",
                        "error": str(e)
                    })
                    raise DatabaseError(
                        f"Migration {migration.version} failed", 
                        detail={"error": str(e), "migration": migration.version}
                    )
        
        return result
    
    async def rollback(self, target_version: Optional[str] = None) -> List[Dict[str, Any]]:
        """برگشت میگریشن ها تا نسخه مشخص"""
        self._load_migrations()
        await self._ensure_migration_collection()
        
        applied_migrations = await self.get_applied_migrations()
        migrations_collection = get_collection("migrations")
        result = []
        
        # برگرداندن آرایه میگریشن ها برای برگشت از آخر به اول
        migrations_to_revert = list(reversed(self.migrations))
        
        # تعیین میگریشن هدف
        stop_index = len(migrations_to_revert)
        if target_version:
            for i, migration in enumerate(migrations_to_revert):
                if migration.version == target_version:
                    stop_index = i
                    break
        
        # برگشت میگریشن های اعمال شده
        for i, migration in enumerate(migrations_to_revert[:stop_index]):
            if migration.version in applied_migrations:
                logger.info(f"Rolling back migration {migration.version}: {migration.description}")
                
                try:
                    # برگشت میگریشن
                    await migration.down()
                    
                    # حذف رکورد میگریشن
                    await migrations_collection.delete_one({
                        "version": migration.version
                    })
                    
                    result.append({
                        "version": migration.version,
                        "description": migration.description,
                        "status": "success"
                    })
                    
                    logger.info(f"Migration {migration.version} rolled back successfully")
                    
                except Exception as e:
                    logger.error(f"Error rolling back migration {migration.version}: {e}")
                    result.append({
                        "version": migration.version,
                        "description": migration.description,
                        "status": "error",
                        "error": str(e)
                    })
                    raise DatabaseError(
                        f"Rollback of migration {migration.version} failed", 
                        detail={"error": str(e), "migration": migration.version}
                    )
        
        return result

# نمونه سینگلتون برای استفاده در سراسر برنامه
migration_manager = MigrationManager()

async def run_migrations():
    """اجرای تمام میگریشن های معلق"""
    logger.info("Running database migrations")
    try:
        await migration_manager.migrate()
        logger.info("All migrations applied successfully")
    except Exception as e:
        logger.error(f"Error running migrations: {e}")
        raise

import time
import os
from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.openapi.utils import get_openapi
from fastapi.staticfiles import StaticFiles
from typing import Dict, Any, List

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.db import connect_to_mongo, close_mongo_connection, get_database_stats
from app.core.logging import get_logger, AppException
from app.core.migrations import run_migrations
from app.tasks.scheduler import setup_scheduler, shutdown_scheduler

# تنظیم لاگینگ
logger = get_logger("app.main")

# ایجاد برنامه FastAPI
app = FastAPI(
    title=settings.PROJECT_NAME,
    description="""
    سیستم پایش توییتر - API برای استخراج و تحلیل توییت‌ها.
    
    ## قابلیت‌ها
    
    * **توییت‌ها**: استخراج، جستجو و تحلیل توییت‌ها
    * **کلمات کلیدی**: مدیریت کلمات کلیدی برای استخراج توییت
    * **آمار**: دریافت آمار کلی سیستم
    """,
    version=settings.VERSION,
    docs_url=None,  # غیرفعال کردن داکس پیش‌فرض برای پیاده‌سازی سفارشی
    redoc_url=None,  # غیرفعال کردن ReDoc
)

# اضافه کردن CORS
if settings.BACKEND_CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[str(origin) for origin in settings.BACKEND_CORS_ORIGINS],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# میان‌افزار زمان پردازش
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response

# اضافه کردن روترهای API
app.include_router(api_router, prefix=settings.API_V1_STR)

# میان‌افزار مدیریت اسنثناها
@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException):
    """مدیریت خطاهای سفارشی برنامه"""
    logger.error(f"Application exception: {exc.message}", extra={"detail": exc.detail})
    return JSONResponse(
        status_code=exc.status_code,
        content=exc.to_dict()
    )

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """مدیریت سایر خطاها"""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"error": "An unexpected error occurred", "detail": str(exc), "type": type(exc).__name__}
    )

# رویدادها
@app.on_event("startup")
async def startup_event():
    """رویداد راه‌اندازی برنامه"""
    try:
        logger.info(f"Starting {settings.PROJECT_NAME} v{settings.VERSION} in {settings.ENVIRONMENT} mode")
        logger.info(f"Debug mode: {settings.DEBUG}")
        
        # اتصال به MongoDB
        await connect_to_mongo()
        logger.info("Connected to MongoDB")
        
        # بررسی اعتبار تنظیمات توییتر
        if not settings.validate_twitter_config():
            logger.warning(
                f"Invalid Twitter API configuration for service type: {settings.TWITTER_SERVICE_TYPE}. "
                "Please check your .env file."
            )
        
        # اجرای میگریشن‌ها
        await run_migrations()
        
        # راه‌اندازی زمان‌بند
        await setup_scheduler()
        
        logger.info(f"{settings.PROJECT_NAME} startup completed")
    except Exception as e:
        logger.error(f"Error during startup: {e}")
        logger.exception(e)
        raise
    
@app.on_event("shutdown")
async def shutdown_event():
    """اجرا در زمان خاموش شدن برنامه"""
    logger.info("Shutting down application...")
    
    # خاموش کردن زمان‌بند
    await shutdown_scheduler()
    
    # بستن اتصال دیتابیس
    await close_mongo_connection()

# مسیر ریشه
@app.get("/")
async def root():
    """مسیر ریشه برنامه"""
    return {
        "name": settings.PROJECT_NAME, 
        "version": settings.VERSION,
        "docs": "/docs",
        "api": settings.API_V1_STR
    }

# مسیر بررسی سلامت
@app.get("/health")
async def health_check():
    """بررسی سلامت سیستم"""
    from app.core.db import db
    from app.tasks.scheduler import scheduler_manager
    
    # بررسی اتصال به دیتابیس
    db_connected = await db.ping()
    
    if not db_connected:
        return JSONResponse(
            status_code=503,  # Service Unavailable
            content={"status": "error", "message": "Database connection failed"}
        )
    
    # وضعیت کلی سیستم
    status = {
        "status": "ok",
        "version": settings.VERSION,
        "environment": settings.ENVIRONMENT,
        "database": db.get_db_info(),
        "scheduler": scheduler_manager.get_status() if settings.ENVIRONMENT != "test" else {"status": "not_running"}
    }
    
    return status

# مسیرهای داکیومنتیشن سفارشی
@app.get("/docs", include_in_schema=False)
async def custom_swagger_ui_html():
    """صفحه داکیومنتیشن Swagger"""
    return get_swagger_ui_html(
        openapi_url=app.openapi_url,
        title=f"{settings.PROJECT_NAME} - API Documentation",
        oauth2_redirect_url=app.swagger_ui_oauth2_redirect_url,
        swagger_js_url="https://cdn.jsdelivr.net/npm/swagger-ui-dist@4/swagger-ui-bundle.js",
        swagger_css_url="https://cdn.jsdelivr.net/npm/swagger-ui-dist@4/swagger-ui.css",
    )

@app.get("/openapi.json", include_in_schema=False)
async def get_open_api_endpoint():
    """JSON مستندات OpenAPI"""
    return get_openapi(
        title=settings.PROJECT_NAME,
        version=settings.VERSION,
        description="API Documentation for Twitter Monitoring System",
        routes=app.routes,
    )

# اضافه کردن API سیستم
from app.api.v1.endpoints import system

app.include_router(
    system.router,
    prefix=f"{settings.API_V1_STR}/system",
    tags=["system"]
)

# اجرای مستقیم
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app", 
        host="0.0.0.0", 
        port=int(os.environ.get("PORT", 8000)), 
        reload=settings.DEBUG
    )

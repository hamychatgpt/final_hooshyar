import logging
import sys
import os
import json
import traceback
from pydantic import BaseModel
from typing import Dict, Any, Optional
from logging.handlers import RotatingFileHandler
from app.core.config import settings

class LogConfig(BaseModel):
    """پیکربندی لاگر"""
    LOGGER_NAME: str = "twitter_monitor"
    LOG_FORMAT: str = settings.LOG_FORMAT
    LOG_LEVEL: str = settings.LOG_LEVEL
    LOG_FILE: str = settings.LOG_FILE
    
    # داشتن خروجی‌های مختلف
    version: int = 1
    disable_existing_loggers: bool = False
    formatters: Dict[str, Dict[str, str]] = {
        "default": {
            "format": LOG_FORMAT,
        },
        "json": {
            "()": "app.core.logging.JsonFormatter",
        }
    }
    handlers: Dict[str, Dict[str, Any]] = {}
    loggers: Dict[str, Dict[str, Any]] = {}
    
    def __init__(self, **data: Any):
        """تنظیم هندلرها بر اساس تنظیمات"""
        super().__init__(**data)
        
        # هندلر خروجی استاندارد
        self.handlers["default"] = {
            "level": self.LOG_LEVEL,
            "class": "logging.StreamHandler",
            "formatter": "default",
            "stream": "ext://sys.stdout",
        }
        
        # هندلر فایل
        if settings.LOG_ROTATION:
            self.handlers["file"] = {
                "level": self.LOG_LEVEL,
                "class": "logging.handlers.RotatingFileHandler",
                "formatter": "json",
                "filename": self.LOG_FILE,
                "maxBytes": settings.LOG_MAX_BYTES,
                "backupCount": settings.LOG_BACKUP_COUNT,
                "encoding": "utf8"
            }
        else:
            # اطمینان از وجود دایرکتوری لاگ
            log_dir = os.path.dirname(self.LOG_FILE)
            os.makedirs(log_dir, exist_ok=True)
            
            self.handlers["file"] = {
                "level": self.LOG_LEVEL,
                "class": "logging.FileHandler",
                "formatter": "json",
                "filename": self.LOG_FILE,
                "encoding": "utf8"
            }
        
        # تنظیم لاگر اصلی
        self.loggers[self.LOGGER_NAME] = {
            "handlers": ["default", "file"],
            "level": self.LOG_LEVEL,
            "propagate": False
        }

class JsonFormatter(logging.Formatter):
    """فرمتر لاگ JSON برای تحلیل آسان تر"""
    def __init__(self):
        super().__init__()
        self.default_msec_format = '%s.%03d'
    
    def format(self, record):
        """تبدیل رکورد لاگ به فرمت JSON"""
        log_record = {
            "timestamp": self.formatTime(record, self.default_msec_format),
            "name": record.name,
            "level": record.levelname,
            "message": record.getMessage(),
            "module": record.module,
            "filename": record.filename,
            "lineno": record.lineno,
            "funcName": record.funcName,
            "thread": record.thread,
            "threadName": record.threadName,
            "process": record.process
        }
        
        # اضافه کردن اطلاعات اضافی
        if hasattr(record, "extra"):
            log_record.update(record.extra)
            
        # اضافه کردن اطلاعات استثنا
        if record.exc_info:
            log_record["exception"] = {
                "type": record.exc_info[0].__name__,
                "message": str(record.exc_info[1]),
                "traceback": traceback.format_exception(*record.exc_info)
            }
            
        return json.dumps(log_record, ensure_ascii=False)

def setup_logging():
    """تنظیم اولیه سیستم لاگینگ"""
    try:
        # اطمینان از وجود دایرکتوری لاگ
        log_dir = os.path.dirname(settings.LOG_FILE)
        os.makedirs(log_dir, exist_ok=True)
        
        # تنظیم پیکربندی لاگ
        log_config = LogConfig()
        logging.config.dictConfig(log_config.dict())
        
        # تنظیم لاگر ریشه
        root_logger = logging.getLogger()
        root_logger.setLevel(settings.LOG_LEVEL)
        
        # لاگ موفقیت راه‌اندازی
        logger = get_logger("app.core.logging")
        logger.info("Logging system initialized successfully")
        
        return True
    except Exception as e:
        # در صورت خطا، تنظیم لاگر پایه
        print(f"Error setting up logging system: {e}")
        root_logger = logging.getLogger()
        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter(settings.LOG_FORMAT)
        handler.setFormatter(formatter)
        root_logger.addHandler(handler)
        root_logger.setLevel(settings.LOG_LEVEL)
        
        return False

def get_logger(name: str) -> logging.Logger:
    """ایجاد و پیکربندی لاگر"""
    import logging.config
    
    # اطمینان از راه‌اندازی سیستم لاگینگ
    if not hasattr(get_logger, "_initialized"):
        setup_logging()
        get_logger._initialized = True
    
    # ایجاد لاگر
    logger = logging.getLogger(name)
    
    return logger

class AppException(Exception):
    """پایه خطاهای برنامه برای مدیریت بهتر خطاها"""
    def __init__(
        self, 
        message: str, 
        status_code: int = 500, 
        detail: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.status_code = status_code
        self.detail = detail or {}
        super().__init__(self.message)
    
    def to_dict(self) -> Dict[str, Any]:
        """تبدیل استثنا به دیکشنری برای پاسخ API"""
        return {
            "error": self.message,
            "status_code": self.status_code,
            "detail": self.detail
        }

class DatabaseError(AppException):
    """خطاهای مربوط به دیتابیس"""
    def __init__(self, message: str, detail: Optional[Dict[str, Any]] = None):
        super().__init__(message, status_code=500, detail=detail)

class APIError(AppException):
    """خطاهای مربوط به API خارجی"""
    def __init__(self, message: str, status_code: int = 502, detail: Optional[Dict[str, Any]] = None):
        super().__init__(message, status_code=status_code, detail=detail)

class ValidationError(AppException):
    """خطاهای اعتبارسنجی"""
    def __init__(self, message: str, detail: Optional[Dict[str, Any]] = None):
        super().__init__(message, status_code=400, detail=detail)

class ResourceNotFoundError(AppException):
    """خطای عدم وجود منبع"""
    def __init__(self, resource_type: str, resource_id: str):
        super().__init__(
            message=f"{resource_type} with id {resource_id} not found",
            status_code=404,
            detail={"resource_type": resource_type, "resource_id": resource_id}
        )

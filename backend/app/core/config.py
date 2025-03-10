from typing import List, Optional, Dict, Any, Union
from pydantic import BaseSettings, AnyHttpUrl, validator
import json
import os

class Settings(BaseSettings):
    # تنظیمات پایه
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "Twitter Monitoring System"
    VERSION: str = "1.0.0"
    
    # تنظیمات محیط
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    
    # MongoDB
    MONGODB_URI: str
    MONGODB_DB: str = "hooshyar"
    
    # تنظیم نوع سرویس توییتر
    TWITTER_SERVICE_TYPE: str = "twitter_api_io"  # گزینه‌ها: "official" یا "twitter_api_io"
    
    # Twitter API (برای TWITTER_SERVICE_TYPE=official)
    TWITTER_API_KEY: Optional[str] = None
    TWITTER_API_SECRET: Optional[str] = None
    TWITTER_API_BEARER_TOKEN: Optional[str] = None
    
    # TwitterAPI.io (برای TWITTER_SERVICE_TYPE=twitter_api_io)
    TWITTERAPI_IO_API_KEY: Optional[str] = None
    TWITTERAPI_IO_BASE_URL: str = "https://api.twitterapi.io/v1.1"
    
    # تنظیمات استخراج
    DEFAULT_TWEETS_LIMIT: int = 100
    DEFAULT_TWEET_LANG: str = "fa"
    EXTRACTION_BATCH_SIZE: int = 20
    API_RATE_LIMIT_WAIT: int = 5  # seconds
    
    # تنظیمات زمان‌بند
    SCHEDULER_JOBS: Dict[str, Any] = {
        "extract_tweets": {"minutes": 15},
        "update_stats": {"minutes": 60}
    }
    
    # CORS
    BACKEND_CORS_ORIGINS: List[AnyHttpUrl] = []
    
    @validator("BACKEND_CORS_ORIGINS", pre=True)
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> Union[List[str], str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, (list, str)):
            return v
        raise ValueError(v)
    
    # لاگینگ
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    LOG_FILE: str = "logs/app.log"
    LOG_ROTATION: bool = True
    LOG_MAX_BYTES: int = 10485760  # 10MB
    LOG_BACKUP_COUNT: int = 5
    
    class Config:
        case_sensitive = True
        env_file = ".env"
        env_file_encoding = "utf-8"
    
    def dict_for_logging(self) -> Dict[str, Any]:
        """ارائه نسخه امن از تنظیمات برای لاگینگ (بدون اطلاعات حساس)"""
        result = self.dict()
        sensitive_fields = {"TWITTER_API_KEY", "TWITTER_API_SECRET", "TWITTER_API_BEARER_TOKEN", 
                           "TWITTERAPI_IO_API_KEY", "MONGODB_URI"}
        for field in sensitive_fields:
            if field in result and result[field]:
                result[field] = "***"
        return result
    
    def validate_twitter_config(self) -> bool:
        """بررسی اعتبار تنظیمات توییتر"""
        if self.TWITTER_SERVICE_TYPE == "official":
            return bool(self.TWITTER_API_KEY and self.TWITTER_API_SECRET)
        elif self.TWITTER_SERVICE_TYPE == "twitter_api_io":
            return bool(self.TWITTERAPI_IO_API_KEY)
        return False

# تنظیمات سینگلتون
settings = Settings()
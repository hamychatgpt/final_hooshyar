from typing import Dict, Any, Union, Type
from app.core.config import settings
from app.core.logging import get_logger

# واردسازی سرویس‌های توییتر
from app.services.twitter_service import twitter_service  # سرویس رسمی با Tweepy
from app.services.twitter_api_io_service import twitter_api_io_service  # سرویس TwitterAPI.io

logger = get_logger("app.services.factory")

class TwitterServiceFactory:
    """فکتوری برای انتخاب سرویس توییتر براساس تنظیمات"""
    
    @staticmethod
    def get_service():
        """
        دریافت سرویس توییتر مناسب براساس تنظیمات
        
        Returns:
            object: سرویس توییتر
        """
        service_type = settings.TWITTER_SERVICE_TYPE.lower()
        
        if service_type == "twitter_api_io":
            logger.info("Using TwitterAPI.io service")
            return twitter_api_io_service
        elif service_type == "official":
            # استفاده از API رسمی توییتر با Tweepy
            logger.info("Using official Twitter API with Tweepy")
            return twitter_service
        else:
            # در صورت نامعتبر بودن نوع سرویس، از سرویس پیش‌فرض استفاده می‌کنیم
            logger.warning(f"Invalid service type: {service_type}. Using TwitterAPI.io as default")
            return twitter_api_io_service

# نمونه سینگلتون از فکتوری
twitter_service_factory = TwitterServiceFactory()
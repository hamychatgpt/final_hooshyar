import requests
import time
import json
import logging
import streamlit as st
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Union
from urllib.parse import urljoin
import os

# تنظیم لاگر
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("streamlit.api")

class APIClient:
    """کلاس ارتباط با API بک‌اند با قابلیت کش و مدیریت خطا"""
    
    def __init__(self, base_url: Optional[str] = None):
        """مقداردهی اولیه با قابلیت انعطاف بیشتر"""
        self.base_url = base_url or os.environ.get("BACKEND_URL", "http://localhost:8000")
        self.api_path = "/api/v1"
        self.session = requests.Session()
        self.cache = {}
        self.cache_expiry = {}  # ذخیره زمان انقضای کش
        
        # تنظیم پیش‌فرض مدت زمان کش (5 دقیقه)
        self.default_cache_ttl = 300
        
        logger.info(f"API Client initialized with base URL: {self.base_url}")
    
    def _get_url(self, endpoint: str) -> str:
        """تولید URL کامل از نقطه انتهایی"""
        return urljoin(f"{self.base_url}{self.api_path}/", endpoint.lstrip("/"))
    
    def _handle_request(
        self, 
        method: str, 
        endpoint: str, 
        params: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None,
        use_cache: bool = False,
        cache_ttl: Optional[int] = None
    ) -> Dict[str, Any]:
        """انجام درخواست با مدیریت خطا و کش گذاری"""
        url = self._get_url(endpoint)
        cache_key = f"{method}:{url}:{json.dumps(params or {})}:{json.dumps(data or {})}"
        
        # اگر از کش استفاده می‌شود و داده در کش موجود است و منقضی نشده، آن را برگردان
        if use_cache and cache_key in self.cache:
            if time.time() < self.cache_expiry.get(cache_key, 0):
                return self.cache[cache_key]
        
        # تنظیم هدرها
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        
        try:
            # اجرای درخواست با زمان انتظار
            if method.lower() == "get":
                response = self.session.get(url, params=params, headers=headers, timeout=10)
            elif method.lower() == "post":
                response = self.session.post(url, json=data, headers=headers, timeout=10)
            elif method.lower() == "put":
                response = self.session.put(url, json=data, headers=headers, timeout=10)
            elif method.lower() == "delete":
                response = self.session.delete(url, params=params, headers=headers, timeout=10)
            else:
                raise ValueError(f"Unsupported method: {method}")
            
            # بررسی پاسخ
            response.raise_for_status()
            result = response.json()
            
            # ذخیره در کش اگر نیاز است
            if use_cache:
                ttl = cache_ttl or self.default_cache_ttl
                self.cache[cache_key] = result
                self.cache_expiry[cache_key] = time.time() + ttl
            
            return result
            
        except requests.exceptions.RequestException as e:
            logger.error(f"API request failed: {url} - {e}")
            if isinstance(e, requests.exceptions.HTTPError):
                status_code = e.response.status_code
                try:
                    error_message = e.response.json().get("detail", str(e))
                except:
                    error_message = str(e)
                
                # بسته به کد وضعیت خطا، عملیات مناسب انجام می‌دهیم
                if status_code == 404:
                    logger.warning(f"Resource not found: {endpoint}")
                    return {"error": "Resource not found", "detail": error_message}
                elif status_code == 429:
                    logger.warning("Rate limit exceeded. Sleeping and retrying...")
                    time.sleep(5)  # انتظار 5 ثانیه قبل از تلاش مجدد
                    return self._handle_request(method, endpoint, params, data, use_cache, cache_ttl)
                elif status_code >= 500:
                    logger.error(f"Server error: {error_message}")
                    return {"error": "Server error", "detail": error_message}
                else:
                    return {"error": f"HTTP Error {status_code}", "detail": error_message}
            
            return {"error": "Request failed", "detail": str(e)}
        
        except Exception as e:
            logger.error(f"Unexpected error in API request: {url} - {e}")
            return {"error": "Unexpected error", "detail": str(e)}
    
    def clear_cache(self, endpoint: Optional[str] = None):
        """پاک کردن کش، با قابلیت پاک کردن انتخابی"""
        if endpoint:
            url = self._get_url(endpoint)
            keys_to_remove = [k for k in self.cache.keys() if url in k]
            for key in keys_to_remove:
                self.cache.pop(key, None)
                self.cache_expiry.pop(key, None)
            logger.debug(f"Cache cleared for endpoint: {endpoint}")
        else:
            self.cache = {}
            self.cache_expiry = {}
            logger.debug("All cache cleared")
    
    # متدهای دسترسی به API مختلف
    
    # API توییت ها
    def get_tweets(self, **kwargs) -> Dict[str, Any]:
        """دریافت توییت ها با فیلترهای مختلف"""
        # حذف پارامترهای None
        params = {k: v for k, v in kwargs.items() if v is not None}
        return self._handle_request("get", "tweets/", params=params, use_cache=True, cache_ttl=60)
    
    def get_tweet(self, tweet_id: str) -> Dict[str, Any]:
        """دریافت یک توییت با شناسه"""
        return self._handle_request("get", f"tweets/{tweet_id}", use_cache=True)
    
    def extract_tweets(self, keywords: Optional[List[str]] = None, limit: Optional[int] = None, 
                      lang: Optional[str] = None) -> Dict[str, Any]:
        """استخراج توییت های جدید"""
        data = {"keywords": keywords, "limit": limit, "lang": lang}
        # پاکسازی None ها
        data = {k: v for k, v in data.items() if v is not None}
        # پاک کردن کش توییت ها پس از استخراج جدید
        result = self._handle_request("post", "tweets/extract", data=data)
        if "error" not in result:
            self.clear_cache("tweets/")
        return result
    
    def get_tweet_stats(self) -> Dict[str, Any]:
        """دریافت آمار توییت ها"""
        return self._handle_request("get", "tweets/stats", use_cache=True, cache_ttl=300)
    
    # API کلمات کلیدی
    def get_keywords(self, is_active: Optional[bool] = None, tag: Optional[str] = None, 
                   priority: Optional[int] = None) -> Dict[str, Any]:
        """دریافت لیست کلمات کلیدی با فیلتر"""
        params = {}
        if is_active is not None:
            params["is_active"] = is_active
        if tag:
            params["tag"] = tag
        if priority:
            params["priority"] = priority
        
        return self._handle_request("get", "keywords/", params=params, use_cache=True, cache_ttl=300)
    
    def get_keyword(self, keyword_id: str) -> Dict[str, Any]:
        """دریافت جزئیات یک کلمه کلیدی"""
        return self._handle_request("get", f"keywords/{keyword_id}", use_cache=True)
    
    def create_keyword(self, **kwargs) -> Dict[str, Any]:
        """ایجاد کلمه کلیدی جدید"""
        result = self._handle_request("post", "keywords/", data=kwargs)
        if "error" not in result:
            self.clear_cache("keywords/")
        return result
    
    def update_keyword(self, keyword_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """به روزرسانی کلمه کلیدی"""
        result = self._handle_request("put", f"keywords/{keyword_id}", data=data)
        if "error" not in result:
            self.clear_cache("keywords/")
            self.clear_cache(f"keywords/{keyword_id}")
        return result
    
    def delete_keyword(self, keyword_id: str) -> bool:
        """حذف کلمه کلیدی"""
        result = self._handle_request("delete", f"keywords/{keyword_id}")
        if "error" not in result:
            self.clear_cache("keywords/")
        return "error" not in result
    
    def get_keyword_stats(self) -> Dict[str, Any]:
        """دریافت آمار کلمات کلیدی"""
        return self._handle_request("get", "keywords/stats", use_cache=True, cache_ttl=300)
    
    # متد بررسی سلامت
    def check_health(self) -> bool:
        """بررسی سلامت سرور بک‌اند"""
        try:
            response = self.session.get(f"{self.base_url}/health", timeout=5)
            return response.status_code == 200
        except:
            return False
    
    # API سیستم
    def get_system_stats(self) -> Dict[str, Any]:
        """دریافت آمار سیستم"""
        return self._handle_request("get", "system/stats", use_cache=True, cache_ttl=300)
    
    def get_execution_logs(self, task_name: Optional[str] = None, 
                           limit: int = 10) -> Dict[str, Any]:
        """دریافت لاگ‌های اجرا"""
        params = {"limit": limit}
        if task_name:
            params["task_name"] = task_name
        
        return self._handle_request("get", "system/executions", params=params, use_cache=True, cache_ttl=60)
    
    # API زمان‌بند
    def get_scheduler_jobs(self) -> Dict[str, Any]:
        """دریافت کارهای زمان‌بند"""
        return self._handle_request("get", "scheduler/jobs", use_cache=True, cache_ttl=60)
    
    def pause_job(self, job_id: str) -> Dict[str, Any]:
        """توقف موقت یک کار"""
        result = self._handle_request("post", f"scheduler/jobs/{job_id}/pause")
        if "error" not in result:
            self.clear_cache("scheduler/jobs")
        return result
    
    def resume_job(self, job_id: str) -> Dict[str, Any]:
        """ازسرگیری یک کار"""
        result = self._handle_request("post", f"scheduler/jobs/{job_id}/resume")
        if "error" not in result:
            self.clear_cache("scheduler/jobs")
        return result
    
    # API میگریشن
    def get_migrations_status(self) -> Dict[str, Any]:
        """دریافت وضعیت میگریشن‌ها"""
        return self._handle_request("get", "system/migrations", use_cache=True, cache_ttl=300)
    
    def run_migrations(self, target_version: Optional[str] = None) -> Dict[str, Any]:
        """اجرای میگریشن‌ها"""
        data = {}
        if target_version:
            data["target_version"] = target_version
        
        result = self._handle_request("post", "system/migrations/run", data=data)
        if "error" not in result:
            self.clear_cache("system/migrations")
        return result

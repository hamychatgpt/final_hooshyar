import logging
import aiohttp
import asyncio
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple

from app.core.config import settings
from app.core.logging import get_logger, APIError
from app.models.tweet import TweetInDB

logger = get_logger("app.services.twitter_api_io_service")

class TwitterApiIOService:
    """سرویس دسترسی به API توییتر از طریق TwitterAPI.io"""
    
    def __init__(self):
        """مقداردهی اولیه"""
        self.base_url = settings.TWITTERAPI_IO_BASE_URL
        self.api_key = settings.TWITTERAPI_IO_API_KEY
        self.session = None
        
    async def _get_session(self) -> aiohttp.ClientSession:
        """ایجاد یا بازیابی نشست HTTP"""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession(
                headers={"Authorization": f"Bearer {self.api_key}"}
            )
        return self.session
        
    async def close(self):
        """بستن نشست HTTP"""
        if self.session and not self.session.closed:
            await self.session.close()
            
    async def search_tweets(self, query: str, count: int = 100, lang: str = "fa") -> Tuple[List[Dict[str, Any]], Optional[str]]:
        """
        جستجوی توییت‌ها با پارامترهای مشخص
        
        Args:
            query: عبارت جستجو
            count: تعداد توییت‌های درخواستی
            lang: زبان توییت‌ها
            
        Returns:
            tuple: (لیست توییت‌ها، پیام خطا)
        """
        try:
            session = await self._get_session()
            params = {
                "q": query,
                "count": min(count, 100),  # حداکثر 100 توییت در هر درخواست
                "result_type": "recent",
                "tweet_mode": "extended"
            }
            
            if lang:
                params["lang"] = lang
                
            url = f"{self.base_url}/search/tweets.json"
            
            logger.info(f"Searching tweets with query: {query}, count: {count}, lang: {lang}")
            
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    tweets = data.get("statuses", [])
                    logger.info(f"Found {len(tweets)} tweets for query: {query}")
                    return tweets, None
                else:
                    error_text = await response.text()
                    logger.error(f"Error searching tweets: {response.status} - {error_text}")
                    return [], f"API Error: {response.status} - {error_text}"
                    
        except aiohttp.ClientError as e:
            logger.error(f"Connection error in search_tweets: {e}")
            return [], f"Connection error: {e}"
        except Exception as e:
            logger.exception(f"Unexpected error in search_tweets: {e}")
            return [], f"Unexpected error: {e}"
    
    async def get_tweet_by_id(self, tweet_id: str) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        """
        دریافت یک توییت با شناسه
        
        Args:
            tweet_id: شناسه توییت
            
        Returns:
            tuple: (داده توییت، پیام خطا)
        """
        try:
            session = await self._get_session()
            url = f"{self.base_url}/statuses/show.json"
            params = {
                "id": tweet_id,
                "tweet_mode": "extended"
            }
            
            logger.info(f"Getting tweet by ID: {tweet_id}")
            
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    tweet = await response.json()
                    return tweet, None
                else:
                    error_text = await response.text()
                    logger.error(f"Error getting tweet {tweet_id}: {response.status} - {error_text}")
                    return None, f"API Error: {response.status} - {error_text}"
                    
        except aiohttp.ClientError as e:
            logger.error(f"Connection error in get_tweet_by_id: {e}")
            return None, f"Connection error: {e}"
        except Exception as e:
            logger.exception(f"Unexpected error in get_tweet_by_id: {e}")
            return None, f"Unexpected error: {e}"
    
    async def process_tweet(self, tweet_data: Dict[str, Any], keywords: List[str] = None) -> Dict[str, Any]:
        """
        پردازش داده‌های خام توییت و تبدیل به فرمت استاندارد
        
        Args:
            tweet_data: داده‌های خام توییت
            keywords: لیست کلمات کلیدی مرتبط
            
        Returns:
            dict: توییت پردازش شده
        """
        # استخراج اطلاعات کاربر
        user = tweet_data.get("user", {})
        
        # استخراج هشتگ‌ها
        hashtags = []
        entities = tweet_data.get("entities", {})
        for hashtag in entities.get("hashtags", []):
            if "text" in hashtag:
                hashtags.append(hashtag["text"])
        
        # تشخیص نوع توییت (ریتوییت، پاسخ، نقل قول)
        is_retweet = "retweeted_status" in tweet_data
        is_quote = tweet_data.get("is_quote_status", False)
        is_reply = tweet_data.get("in_reply_to_status_id") is not None
        
        # استخراج متن کامل
        if "full_text" in tweet_data:
            text = tweet_data["full_text"]
        else:
            text = tweet_data.get("text", "")
        
        # محاسبه امتیاز اهمیت (الگوریتم ساده)
        importance_score = 0
        importance_score += min(user.get("followers_count", 0) / 1000, 50)  # حداکثر 50 امتیاز برای فالوئرها
        importance_score += min(tweet_data.get("favorite_count", 0) / 10, 30)  # حداکثر 30 امتیاز برای لایک‌ها
        importance_score += min(tweet_data.get("retweet_count", 0) / 5, 20)  # حداکثر 20 امتیاز برای ریتوییت‌ها
        
        # توییت پردازش شده
        processed_tweet = {
            "tweet_id": str(tweet_data.get("id")),
            "text": text,
            "created_at": datetime.strptime(tweet_data.get("created_at"), "%a %b %d %H:%M:%S +0000 %Y"),
            "lang": tweet_data.get("lang", ""),
            "user_id": str(user.get("id", "")),
            "user_screen_name": user.get("screen_name", ""),
            "user_name": user.get("name", ""),
            "user_verified": user.get("verified", False),
            "user_followers_count": user.get("followers_count", 0),
            "user_friends_count": user.get("friends_count", 0),
            "retweet_count": tweet_data.get("retweet_count", 0),
            "favorite_count": tweet_data.get("favorite_count", 0),
            "reply_count": tweet_data.get("reply_count", 0),
            "quote_count": tweet_data.get("quote_count", 0),
            "hashtags": hashtags,
            "is_retweet": is_retweet,
            "is_quote": is_quote,
            "is_reply": is_reply,
            "in_reply_to_status_id": tweet_data.get("in_reply_to_status_id_str"),
            "in_reply_to_user_id": tweet_data.get("in_reply_to_user_id_str"),
            "in_reply_to_screen_name": tweet_data.get("in_reply_to_screen_name"),
            "importance_score": importance_score,
            "keywords": keywords or [],
            "raw_data": tweet_data  # ذخیره داده‌های خام برای استفاده احتمالی در آینده
        }
        
        return processed_tweet
    
    async def save_tweets(self, tweets: List[Dict[str, Any]], keywords: List[str] = None) -> Dict[str, int]:
        """
        ذخیره توییت‌ها در دیتابیس
        
        Args:
            tweets: لیست توییت‌ها
            keywords: لیست کلمات کلیدی مرتبط
            
        Returns:
            dict: نتیجه ذخیره‌سازی (تعداد افزوده‌شده، به‌روزرسانی‌شده و...)
        """
        from app.core.db import get_collection
        
        if not tweets:
            return {
                "total": 0,
                "inserted": 0,
                "updated": 0,
                "skipped": 0
            }
        
        # آماده‌سازی برای ذخیره در دیتابیس
        tweets_collection = get_collection("tweets")
        
        total = len(tweets)
        inserted = 0
        updated = 0
        skipped = 0
        
        for tweet_data in tweets:
            try:
                # پردازش توییت
                processed_tweet = await self.process_tweet(tweet_data, keywords)
                tweet_id = processed_tweet["tweet_id"]
                
                # بررسی وجود توییت در دیتابیس
                existing_tweet = await tweets_collection.find_one({"tweet_id": tweet_id})
                
                if existing_tweet:
                    # به‌روزرسانی کلمات کلیدی و آمار
                    update_data = {
                        "retweet_count": processed_tweet["retweet_count"],
                        "favorite_count": processed_tweet["favorite_count"],
                        "reply_count": processed_tweet["reply_count"],
                        "quote_count": processed_tweet["quote_count"],
                        "updated_in_db": datetime.utcnow()
                    }
                    
                    # اضافه کردن کلمات کلیدی جدید
                    if keywords:
                        existing_keywords = existing_tweet.get("keywords", [])
                        new_keywords = list(set(existing_keywords + keywords))
                        update_data["keywords"] = new_keywords
                    
                    # به‌روزرسانی امتیاز اهمیت
                    update_data["importance_score"] = processed_tweet["importance_score"]
                    
                    await tweets_collection.update_one(
                        {"tweet_id": tweet_id},
                        {"$set": update_data}
                    )
                    updated += 1
                else:
                    # افزودن فیلدهای اضافی
                    processed_tweet["created_in_db"] = datetime.utcnow()
                    processed_tweet["updated_in_db"] = datetime.utcnow()
                    processed_tweet["is_processed"] = False
                    
                    # ذخیره توییت جدید
                    await tweets_collection.insert_one(processed_tweet)
                    inserted += 1
                    
            except Exception as e:
                logger.error(f"Error saving tweet: {e}")
                skipped += 1
        
        return {
            "total": total,
            "inserted": inserted,
            "updated": updated,
            "skipped": skipped
        }
    
    async def extract_tweets_for_keyword(self, keyword: str, count: int = 100, lang: str = "fa") -> Dict[str, Any]:
        """
        استخراج توییت‌ها برای یک کلمه کلیدی
        
        Args:
            keyword: کلمه کلیدی
            count: تعداد توییت‌ها
            lang: زبان توییت‌ها
            
        Returns:
            dict: نتیجه استخراج
        """
        logger.info(f"Extracting tweets for keyword: {keyword}, count: {count}, lang: {lang}")
        
        try:
            # جستجوی توییت‌ها
            tweets, error = await self.search_tweets(keyword, count, lang)
            
            if error:
                logger.error(f"Error searching tweets for keyword '{keyword}': {error}")
                return {
                    "keyword": keyword,
                    "error": error,
                    "total": 0,
                    "inserted": 0,
                    "updated": 0,
                    "skipped": 0
                }
            
            if not tweets:
                logger.info(f"No tweets found for keyword: {keyword}")
                return {
                    "keyword": keyword,
                    "total": 0,
                    "inserted": 0,
                    "updated": 0,
                    "skipped": 0
                }
            
            # ذخیره توییت‌ها
            result = await self.save_tweets(tweets, [keyword])
            result["keyword"] = keyword
            
            logger.info(f"Extraction completed for keyword '{keyword}': {result}")
            return result
            
        except Exception as e:
            logger.exception(f"Unexpected error extracting tweets for keyword '{keyword}': {e}")
            return {
                "keyword": keyword,
                "error": str(e),
                "total": 0,
                "inserted": 0,
                "updated": 0,
                "skipped": 0
            }

# نمونه سینگلتون از سرویس
twitter_api_io_service = TwitterApiIOService()
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import asyncio

from app.core.config import settings
from app.core.logging import get_logger
from app.core.db import get_collection
from app.services.factory import twitter_service_factory

logger = get_logger("app.tasks.twitter_tasks")

async def extract_tweets_for_all_keywords() -> Dict[str, Any]:
    """
    استخراج توییت‌ها برای تمام کلمات کلیدی فعال
    
    Returns:
        dict: نتیجه استخراج
    """
    logger.info("Starting extraction for all active keywords")
    
    try:
        # دریافت سرویس توییتر
        twitter_service = twitter_service_factory.get_service()
        
        # دریافت کلمات کلیدی فعال
        keywords_collection = get_collection("keywords")
        active_keywords = await keywords_collection.find(
            {"is_active": True}
        ).sort("priority", 1).to_list(length=100)
        
        if not active_keywords:
            logger.info("No active keywords found")
            return {"status": "success", "message": "No active keywords found", "results": {}}
        
        logger.info(f"Found {len(active_keywords)} active keywords")
        
        # استخراج توییت‌ها برای هر کلمه کلیدی
        results = {}
        batch_size = settings.EXTRACTION_BATCH_SIZE
        
        # دسته‌بندی کلمات کلیدی براساس اولویت
        priority_groups = {}
        for keyword in active_keywords:
            priority = keyword.get("priority", 5)
            if priority not in priority_groups:
                priority_groups[priority] = []
            priority_groups[priority].append(keyword)
        
        # پردازش هر گروه اولویت به ترتیب
        for priority in sorted(priority_groups.keys()):
            keywords_group = priority_groups[priority]
            logger.info(f"Processing {len(keywords_group)} keywords with priority {priority}")
            
            # پردازش کلمات کلیدی در دسته‌های کوچک برای جلوگیری از فشار بر API
            for i in range(0, len(keywords_group), batch_size):
                batch = keywords_group[i:i+batch_size]
                
                # ایجاد تسک‌های استخراج
                tasks = []
                for keyword_doc in batch:
                    keyword = keyword_doc["keyword"]
                    limit = keyword_doc.get("max_tweets_per_request", settings.DEFAULT_TWEETS_LIMIT)
                    lang = settings.DEFAULT_TWEET_LANG
                    
                    task = twitter_service.extract_tweets_for_keyword(keyword, limit, lang)
                    tasks.append(task)
                
                # اجرای همزمان تسک‌ها
                batch_results = await asyncio.gather(*tasks)
                
                # ذخیره نتایج
                for result in batch_results:
                    keyword = result.get("keyword")
                    if keyword:
                        results[keyword] = result
                        
                        # به‌روزرسانی آمار کلمه کلیدی
                        if "error" not in result:
                            await keywords_collection.update_one(
                                {"keyword": keyword},
                                {
                                    "$set": {"last_extracted_at": datetime.utcnow()},
                                    "$inc": {"total_tweets": result.get("inserted", 0)}
                                }
                            )
                
                # انتظار کوتاه بین دسته‌ها برای جلوگیری از محدودیت نرخ
                if i + batch_size < len(keywords_group):
                    await asyncio.sleep(settings.API_RATE_LIMIT_WAIT)
        
        logger.info(f"Extraction completed for all keywords. Results: {results}")
        return {"status": "success", "results": results}
        
    except Exception as e:
        logger.exception(f"Error in extract_tweets_for_all_keywords: {e}")
        return {"status": "error", "error": str(e)}

async def update_tweet_stats() -> Dict[str, Any]:
    """
    به‌روزرسانی آمار توییت‌های مهم
    
    Returns:
        dict: نتیجه به‌روزرسانی
    """
    logger.info("Starting tweet stats update")
    
    try:
        # دریافت سرویس مناسب
        twitter_service = twitter_service_factory.get_service()
        
        # دریافت کالکشن توییت‌ها
        tweets_collection = get_collection("tweets")
        
        # دریافت توییت‌های مهم برای به‌روزرسانی
        # توییت‌هایی که امتیاز اهمیت بالا دارند و اخیراً به‌روزرسانی نشده‌اند
        cutoff_time = datetime.utcnow() - timedelta(hours=24)
        important_tweets = await tweets_collection.find(
            {
                "importance_score": {"$gt": 50},
                "updated_in_db": {"$lt": cutoff_time}
            }
        ).sort("importance_score", -1).limit(100).to_list(length=100)
        
        if not important_tweets:
            logger.info("No important tweets found for update")
            return {
                "status": "success",
                "message": "No tweets to update",
                "updated": 0,
                "errors": 0
            }
        
        logger.info(f"Found {len(important_tweets)} important tweets to update")
        
        updated_count = 0
        error_count = 0
        
        # به‌روزرسانی هر توییت
        for tweet in important_tweets:
            try:
                tweet_id = tweet["tweet_id"]
                
                # دریافت آمار جدید توییت
                tweet_data, error = await twitter_service.get_tweet_by_id(tweet_id)
                
                if error:
                    logger.error(f"Error fetching tweet {tweet_id}: {error}")
                    error_count += 1
                    continue
                
                if not tweet_data:
                    logger.warning(f"Tweet {tweet_id} not found or deleted")
                    error_count += 1
                    continue
                
                # به‌روزرسانی آمار
                update_data = {
                    "retweet_count": tweet_data.get("retweet_count", tweet.get("retweet_count", 0)),
                    "favorite_count": tweet_data.get("favorite_count", tweet.get("favorite_count", 0)),
                    "reply_count": tweet_data.get("reply_count", tweet.get("reply_count", 0)),
                    "quote_count": tweet_data.get("quote_count", tweet.get("quote_count", 0)),
                    "updated_in_db": datetime.utcnow()
                }
                
                # محاسبه مجدد امتیاز اهمیت
                user = tweet_data.get("user", {})
                importance_score = 0
                importance_score += min(user.get("followers_count", 0) / 1000, 50)
                importance_score += min(tweet_data.get("favorite_count", 0) / 10, 30)
                importance_score += min(tweet_data.get("retweet_count", 0) / 5, 20)
                update_data["importance_score"] = importance_score
                
                # به‌روزرسانی در دیتابیس
                result = await tweets_collection.update_one(
                    {"tweet_id": tweet_id},
                    {"$set": update_data}
                )
                
                if result.modified_count > 0:
                    updated_count += 1
                
                # انتظار کوتاه بین درخواست‌ها
                await asyncio.sleep(0.5)
                
            except Exception as e:
                logger.error(f"Error updating stats for tweet {tweet.get('tweet_id')}: {e}")
                error_count += 1
        
        logger.info(f"Tweet stats update completed. Updated: {updated_count}, errors: {error_count}")
        
        return {
            "status": "success",
            "updated": updated_count,
            "errors": error_count
        }
        
    except Exception as e:
        logger.exception(f"Error in update_tweet_stats: {e}")
        return {
            "status": "error",
            "error": str(e),
            "updated": 0,
            "errors": 0
        }
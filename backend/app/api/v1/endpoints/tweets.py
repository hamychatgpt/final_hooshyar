from fastapi import APIRouter, Depends, HTTPException, Query, Path
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta

from app.core.logging import get_logger
from app.services.factory import twitter_service_factory
from app.core.db import get_collection

logger = get_logger("app.api.tweets")

router = APIRouter()

@router.get("/", summary="Get tweets with filters")
async def get_tweets(
    keyword: Optional[str] = Query(None, description="Filter by keyword"),
    user_screen_name: Optional[str] = Query(None, description="Filter by user screen name"),
    start_date: Optional[datetime] = Query(None, description="Filter by start date"),
    end_date: Optional[datetime] = Query(None, description="Filter by end date"),
    importance_min: Optional[float] = Query(None, description="Minimum importance score"),
    is_verified: Optional[bool] = Query(None, description="Filter by user verification status"),
    search_text: Optional[str] = Query(None, description="Full-text search in tweet content"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page")
):
    """
    جستجوی توییت‌ها با فیلترهای مختلف
    """
    try:
        tweets_collection = get_collection("tweets")
        
        # ساخت کوئری
        query = {}
        
        # اعمال فیلترها
        if keyword:
            query["keywords"] = keyword
        
        if user_screen_name:
            query["user_screen_name"] = user_screen_name
        
        if start_date:
            query["created_at"] = query.get("created_at", {})
            query["created_at"]["$gte"] = start_date
        
        if end_date:
            query["created_at"] = query.get("created_at", {})
            query["created_at"]["$lte"] = end_date
        
        if importance_min is not None:
            query["importance_score"] = {"$gte": importance_min}
        
        if is_verified is not None:
            query["user_verified"] = is_verified
        
        # جستجوی متنی
        if search_text:
            query["$text"] = {"$search": search_text}
        
        # اجرای کوئری با صفحه‌بندی
        total_count = await tweets_collection.count_documents(query)
        
        skip = (page - 1) * page_size
        cursor = tweets_collection.find(query).sort("created_at", -1).skip(skip).limit(page_size)
        
        tweets = []
        async for tweet in cursor:
            # تبدیل ObjectId به رشته
            tweet["id"] = str(tweet.pop("_id"))
            tweets.append(tweet)
        
        return {
            "total": total_count,
            "page": page,
            "page_size": page_size,
            "tweets": tweets
        }
        
    except Exception as e:
        logger.error(f"Error getting tweets: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving tweets: {str(e)}"
        )

@router.get("/{tweet_id}", summary="Get tweet by ID")
async def get_tweet(
    tweet_id: str = Path(..., description="Tweet ID")
):
    """
    دریافت یک توییت با شناسه
    """
    try:
        tweets_collection = get_collection("tweets")
        
        # جستجوی توییت
        tweet = await tweets_collection.find_one({"tweet_id": tweet_id})
        
        if not tweet:
            raise HTTPException(
                status_code=404,
                detail=f"Tweet with ID {tweet_id} not found"
            )
        
        # تبدیل ObjectId به رشته
        tweet["id"] = str(tweet.pop("_id"))
        
        return tweet
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting tweet {tweet_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving tweet: {str(e)}"
        )

@router.post("/extract", status_code=202, summary="Extract tweets for keywords")
async def extract_tweets(
    request: dict
):
    """
    استخراج توییت‌ها برای کلمات کلیدی
    """
    try:
        keywords = request.get("keywords")
        limit = request.get("limit", 100)
        lang = request.get("lang", "fa")
        
        # اگر کلمات کلیدی ارائه نشده باشد، استفاده از همه کلمات کلیدی فعال
        if not keywords:
            keywords_collection = get_collection("keywords")
            active_keywords_cursor = keywords_collection.find({"is_active": True})
            active_keywords = await active_keywords_cursor.to_list(length=100)
            keywords = [k["keyword"] for k in active_keywords]
        
        if not keywords:
            return {
                "status": "warning",
                "message": "No keywords provided or found",
                "results": {}
            }
        
        # دریافت سرویس توییتر
        twitter_service = twitter_service_factory.get_service()
        
        # استخراج توییت‌ها
        results = {}
        for keyword in keywords:
            result = await twitter_service.extract_tweets_for_keyword(keyword, limit, lang)
            results[keyword] = result
        
        return {
            "status": "success",
            "message": f"Extraction started for {len(keywords)} keywords",
            "results": results
        }
        
    except Exception as e:
        logger.error(f"Error extracting tweets: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error extracting tweets: {str(e)}"
        )

@router.get("/stats", summary="Get tweet statistics")
async def get_tweet_stats():
    """
    دریافت آمار توییت‌ها
    """
    try:
        tweets_collection = get_collection("tweets")
        
        # تعداد کل توییت‌ها
        total_tweets = await tweets_collection.count_documents({})
        
        # توییت‌های امروز
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        tweets_today = await tweets_collection.count_documents({"created_at": {"$gte": today_start}})
        
        # توییت‌های 24 ساعت اخیر
        last_24h = datetime.utcnow() - timedelta(hours=24)
        tweets_last_24h = await tweets_collection.count_documents({"created_at": {"$gte": last_24h}})
        
        # توییت‌ها به تفکیک کلمه کلیدی
        pipeline = [
            {"$unwind": "$keywords"},
            {"$group": {"_id": "$keywords", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}},
            {"$limit": 10}
        ]
        tweets_by_keyword_cursor = tweets_collection.aggregate(pipeline)
        tweets_by_keyword = await tweets_by_keyword_cursor.to_list(length=10)
        
        # توییت‌ها به تفکیک زبان
        pipeline = [
            {"$group": {"_id": "$lang", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}},
            {"$limit": 10}
        ]
        tweets_by_language_cursor = tweets_collection.aggregate(pipeline)
        tweets_by_language = await tweets_by_language_cursor.to_list(length=10)
        
        # محدوده زمانی داده‌ها
        oldest_tweet = await tweets_collection.find_one({}, sort=[("created_at", 1)])
        newest_tweet = await tweets_collection.find_one({}, sort=[("created_at", -1)])
        
        oldest_date = oldest_tweet.get("created_at") if oldest_tweet else None
        newest_date = newest_tweet.get("created_at") if newest_tweet else None
        
        return {
            "total_tweets": total_tweets,
            "tweets_today": tweets_today,
            "tweets_last_24h": tweets_last_24h,
            "tweets_by_keyword": tweets_by_keyword,
            "tweets_by_language": tweets_by_language,
            "date_range": {
                "oldest": oldest_date.isoformat() if oldest_date else None,
                "newest": newest_date.isoformat() if newest_date else None
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting tweet stats: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving tweet statistics: {str(e)}"
        )
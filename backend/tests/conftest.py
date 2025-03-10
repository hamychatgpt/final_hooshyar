import pytest
import asyncio
import os
import sys
from motor.motor_asyncio import AsyncIOMotorClient
from fastapi.testclient import TestClient
from typing import Generator, Dict, Any
from datetime import datetime

# اضافه کردن مسیر پروژه به sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.core.config import settings

# تغییر تنظیمات برای محیط تست
settings.MONGODB_DB = settings.MONGODB_DB + "_test"
settings.ENVIRONMENT = "test"

@pytest.fixture(scope="session")
def event_loop():
    """ایجاد و ارائه حلقه رویداد برای تست‌های async"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="session")
async def mongodb_client() -> AsyncIOMotorClient:
    """ایجاد اتصال به MongoDB برای تست"""
    client = AsyncIOMotorClient(settings.MONGODB_URI, serverSelectionTimeoutMS=5000)
    
    # تست اتصال
    await client.admin.command('ping')
    
    yield client
    
    # بستن اتصال پس از تست‌ها
    client.close()

@pytest.fixture(scope="session")
async def mongodb_test_db(mongodb_client: AsyncIOMotorClient):
    """ایجاد دیتابیس تست و پاکسازی آن"""
    db = mongodb_client[settings.MONGODB_DB]
    
    # پاکسازی دیتابیس قبل از شروع تست‌ها
    await mongodb_client.drop_database(settings.MONGODB_DB)
    
    yield db
    
    # پاکسازی دیتابیس پس از اتمام تست‌ها
    await mongodb_client.drop_database(settings.MONGODB_DB)

@pytest.fixture
async def app_client(mongodb_test_db) -> TestClient:
    """ایجاد کلاینت تست FastAPI"""
    from app.main import app
    from app.core.db import db
    
    # جایگزینی دیتابیس تست
    db.client = mongodb_test_db.client
    db.db = mongodb_test_db
    
    # اجرای ایندکس‌ها
    from app.models.tweet import create_tweet_indexes
    from app.models.keyword import create_keyword_indexes
    
    await create_tweet_indexes(db.db)
    await create_keyword_indexes(db.db)
    
    # ایجاد کلاینت تست
    test_client = TestClient(app)
    
    # اطمینان از اتصال به دیتابیس تست
    assert db.db.name == settings.MONGODB_DB
    
    yield test_client

@pytest.fixture
async def sample_keywords(mongodb_test_db) -> Dict[str, Any]:
    """ایجاد کلمات کلیدی نمونه برای تست"""
    keywords_collection = mongodb_test_db.keywords
    
    # کلمات کلیدی نمونه
    test_keywords = [
        {
            "keyword": "test1",
            "is_active": True,
            "description": "Test keyword 1",
            "priority": 1,
            "max_tweets_per_request": 100,
            "tags": ["test", "sample"],
            "extraction_frequency": 60
        },
        {
            "keyword": "test2",
            "is_active": False,
            "description": "Test keyword 2",
            "priority": 2,
            "max_tweets_per_request": 50,
            "tags": ["test"],
            "extraction_frequency": 120
        }
    ]
    
    # افزودن کلمات کلیدی به دیتابیس
    result = {}
    for keyword in test_keywords:
        insert_result = await keywords_collection.insert_one(keyword)
        keyword["_id"] = insert_result.inserted_id
        keyword["id"] = str(insert_result.inserted_id)
        result[keyword["keyword"]] = keyword
    
    yield result
    
    # پاکسازی پس از تست
    await keywords_collection.delete_many({"keyword": {"$in": list(result.keys())}})

@pytest.fixture
async def sample_tweets(mongodb_test_db, sample_keywords) -> Dict[str, Any]:
    """ایجاد توییت‌های نمونه برای تست"""
    tweets_collection = mongodb_test_db.tweets
    
    # توییت‌های نمونه
    from datetime import datetime
    
    test_tweets = [
        {
            "tweet_id": "12345",
            "text": "This is a test tweet with #test hashtag",
            "created_at": datetime.utcnow(),
            "lang": "en",
            "user_id": "user1",
            "user_screen_name": "testuser1",
            "user_name": "Test User 1",
            "user_verified": True,
            "user_followers_count": 100,
            "user_friends_count": 50,
            "retweet_count": 10,
            "favorite_count": 20,
            "hashtags": ["test"],
            "keywords": ["test1"],
            "importance_score": 50.0
        },
        {
            "tweet_id": "67890",
            "text": "Another test tweet with #sample hashtag",
            "created_at": datetime.utcnow(),
            "lang": "en",
            "user_id": "user2",
            "user_screen_name": "testuser2",
            "user_name": "Test User 2",
            "user_verified": False,
            "user_followers_count": 200,
            "user_friends_count": 100,
            "retweet_count": 5,
            "favorite_count": 15,
            "hashtags": ["sample"],
            "keywords": ["test2"],
            "importance_score": 30.0
        }
    ]
    
    # افزودن توییت‌ها به دیتابیس
    result = {}
    for tweet in test_tweets:
        insert_result = await tweets_collection.insert_one(tweet)
        tweet["_id"] = insert_result.inserted_id
        tweet["id"] = str(insert_result.inserted_id)
        result[tweet["tweet_id"]] = tweet
    
    yield result
    
    # پاکسازی پس از تست
    await tweets_collection.delete_many({"tweet_id": {"$in": list(result.keys())}})

@pytest.fixture
def mock_twitter_api_io_service(monkeypatch):
    """
    موک سرویس TwitterAPI.io برای تست
    """
    class MockTwitterApiIOService:
        async def search_tweets(self, keyword, lang=None, limit=None, cursor=None):
            # داده‌های آزمایشی
            tweets = [
                {
                    "tweet_id": "12345",
                    "text": f"This is a test tweet about {keyword}",
                    "created_at": datetime.utcnow(),
                    "lang": lang or "fa",
                    "user_id": "user1",
                    "user_screen_name": "testuser1",
                    "user_name": "Test User 1",
                    "user_verified": True,
                    "user_followers_count": 100,
                    "user_friends_count": 50,
                    "retweet_count": 10,
                    "favorite_count": 20,
                    "hashtags": ["test"],
                    "keywords": [keyword],
                }
            ]
            return tweets, None
        
        async def save_tweets(self, tweets, keywords=None):
            return {
                "total": len(tweets),
                "inserted": len(tweets),
                "updated": 0,
                "skipped": 0
            }
        
        async def get_tweet_by_id(self, tweet_id):
            tweet = {
                "tweet_id": tweet_id,
                "text": "This is a test tweet",
                "created_at": datetime.utcnow(),
                "lang": "fa",
                "user_id": "user1",
                "user_screen_name": "testuser1",
                "user_name": "Test User 1",
                "user_verified": True,
                "user_followers_count": 100,
                "user_friends_count": 50,
                "retweet_count": 10,
                "favorite_count": 20,
                "hashtags": ["test"],
            }
            return tweet, None
    
    # ایجاد نمونه موک و جایگزینی با سرویس اصلی
    mock_service = MockTwitterApiIOService()
    monkeypatch.setattr("app.services.twitter_api_io_service.twitter_api_io_service", mock_service)
    
    return mock_service

@pytest.fixture
def mock_twitter_service_factory(monkeypatch, mock_twitter_api_io_service):
    """
    موک فکتوری سرویس‌های توییتر
    """
    class MockTwitterServiceFactory:
        @staticmethod
        def get_service():
            return mock_twitter_api_io_service
    
    # جایگزینی با فکتوری اصلی
    monkeypatch.setattr("app.services.factory.twitter_service_factory", MockTwitterServiceFactory())

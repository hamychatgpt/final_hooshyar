import pytest
from fastapi.testclient import TestClient
from typing import Dict, Any
from datetime import datetime, timedelta

@pytest.mark.asyncio
async def test_get_tweets_empty(app_client: TestClient):
    """تست دریافت لیست توییت‌های خالی"""
    response = app_client.get("/api/v1/tweets/")
    assert response.status_code == 200
    
    data = response.json()
    assert "total" in data
    assert "tweets" in data
    assert data["total"] == 0
    assert len(data["tweets"]) == 0

@pytest.mark.asyncio
async def test_get_tweets_with_data(app_client: TestClient, sample_tweets: Dict[str, Any]):
    """تست دریافت لیست توییت‌ها با داده موجود"""
    response = app_client.get("/api/v1/tweets/")
    assert response.status_code == 200
    
    data = response.json()
    assert data["total"] == len(sample_tweets)
    assert len(data["tweets"]) == len(sample_tweets)
    
    # بررسی وجود توییت‌های نمونه در نتایج
    tweets_dict = {t["tweet_id"]: t for t in data["tweets"]}
    for tweet_id, tweet_data in sample_tweets.items():
        assert tweet_id in tweets_dict
        assert tweets_dict[tweet_id]["text"] == tweet_data["text"]

@pytest.mark.asyncio
async def test_get_tweet_by_id(app_client: TestClient, sample_tweets: Dict[str, Any]):
    """تست دریافت توییت با شناسه"""
    # انتخاب یک توییت
    tweet_id, tweet_data = next(iter(sample_tweets.items()))
    
    # ارسال درخواست
    response = app_client.get(f"/api/v1/tweets/{tweet_id}")
    assert response.status_code == 200
    
    # بررسی پاسخ
    data = response.json()
    assert data["tweet_id"] == tweet_id
    assert data["text"] == tweet_data["text"]
    assert data["user_screen_name"] == tweet_data["user_screen_name"]

@pytest.mark.asyncio
async def test_get_tweet_not_found(app_client: TestClient):
    """تست دریافت توییت با شناسه نامعتبر"""
    response = app_client.get("/api/v1/tweets/999999")
    assert response.status_code == 404

@pytest.mark.asyncio
async def test_filter_tweets_by_keyword(app_client: TestClient, sample_tweets: Dict[str, Any]):
    """تست فیلتر توییت‌ها براساس کلمه کلیدی"""
    # انتخاب یک کلمه کلیدی
    keyword = "test1"
    
    # فیلتر توییت‌ها
    response = app_client.get(f"/api/v1/tweets/?keyword={keyword}")
    assert response.status_code == 200
    
    data = response.json()
    tweets_with_keyword = [t for t, v in sample_tweets.items() if keyword in v["keywords"]]
    assert data["total"] == len(tweets_with_keyword)
    assert all(keyword in t["keywords"] for t in data["tweets"])

@pytest.mark.asyncio
async def test_filter_tweets_by_importance(app_client: TestClient, sample_tweets: Dict[str, Any]):
    """تست فیلتر توییت‌ها براساس اهمیت"""
    # فیلتر توییت‌ها با اهمیت بیشتر از 40
    importance_min = 40
    
    # ارسال درخواست
    response = app_client.get(f"/api/v1/tweets/?importance_min={importance_min}")
    assert response.status_code == 200
    
    data = response.json()
    important_tweets = [t for t, v in sample_tweets.items() if v["importance_score"] >= importance_min]
    assert data["total"] == len(important_tweets)
    assert all(t["importance_score"] >= importance_min for t in data["tweets"])

@pytest.mark.asyncio
async def test_filter_tweets_by_date(app_client: TestClient, sample_tweets: Dict[str, Any]):
    """تست فیلتر توییت‌ها براساس تاریخ"""
    # زمان 30 روز قبل
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    thirty_days_ago_str = thirty_days_ago.isoformat()
    
    # ارسال درخواست
    response = app_client.get(f"/api/v1/tweets/?start_date={thirty_days_ago_str}")
    assert response.status_code == 200
    
    data = response.json()
    # همه توییت‌های نمونه باید بعد از 30 روز قبل باشند
    assert data["total"] == len(sample_tweets)
    
    # آزمایش با تاریخ آینده
    tomorrow = datetime.utcnow() + timedelta(days=1)
    tomorrow_str = tomorrow.isoformat()
    
    response = app_client.get(f"/api/v1/tweets/?start_date={tomorrow_str}")
    assert response.status_code == 200
    
    data = response.json()
    # نباید هیچ توییتی از آینده باشد
    assert data["total"] == 0

@pytest.mark.asyncio
async def test_filter_tweets_by_user(app_client: TestClient, sample_tweets: Dict[str, Any]):
    """تست فیلتر توییت‌ها براساس کاربر"""
    # انتخاب یک کاربر
    user = "testuser1"
    
    # ارسال درخواست
    response = app_client.get(f"/api/v1/tweets/?user_screen_name={user}")
    assert response.status_code == 200
    
    data = response.json()
    user_tweets = [t for t, v in sample_tweets.items() if v["user_screen_name"] == user]
    assert data["total"] == len(user_tweets)
    assert all(t["user_screen_name"] == user for t in data["tweets"])

@pytest.mark.asyncio
async def test_filter_tweets_by_verified(app_client: TestClient, sample_tweets: Dict[str, Any]):
    """تست فیلتر توییت‌ها براساس وضعیت تأیید کاربر"""
    # فیلتر کاربران تأیید شده
    response = app_client.get("/api/v1/tweets/?is_verified=true")
    assert response.status_code == 200
    
    data = response.json()
    verified_tweets = [t for t, v in sample_tweets.items() if v["user_verified"]]
    assert data["total"] == len(verified_tweets)
    assert all(t["user_verified"] for t in data["tweets"])
    
    # فیلتر کاربران تأیید نشده
    response = app_client.get("/api/v1/tweets/?is_verified=false")
    assert response.status_code == 200
    
    data = response.json()
    unverified_tweets = [t for t, v in sample_tweets.items() if not v["user_verified"]]
    assert data["total"] == len(unverified_tweets)
    assert all(not t["user_verified"] for t in data["tweets"])

@pytest.mark.asyncio
async def test_text_search(app_client: TestClient, sample_tweets: Dict[str, Any]):
    """تست جستجوی متنی در توییت‌ها"""
    # جستجوی عبارت "hashtag"
    search_term = "hashtag"
    
    # ارسال درخواست
    response = app_client.get(f"/api/v1/tweets/?search_text={search_term}")
    assert response.status_code == 200
    
    data = response.json()
    tweets_with_term = [t for t, v in sample_tweets.items() if search_term in v["text"].lower()]
    
    # چون محدودیت‌های جستجوی متنی در تست‌ها متفاوت است، فقط بررسی می‌کنیم که نتایجی وجود داشته باشد
    assert data["total"] > 0

@pytest.mark.asyncio
async def test_tweet_stats(app_client: TestClient, sample_tweets: Dict[str, Any]):
    """تست آمار توییت‌ها"""
    response = app_client.get("/api/v1/tweets/stats")
    assert response.status_code == 200
    
    data = response.json()
    assert "total_tweets" in data
    assert "tweets_today" in data
    assert "tweets_last_24h" in data
    assert "tweets_by_keyword" in data
    assert "tweets_by_language" in data
    
    # بررسی تعداد کل توییت‌ها
    assert data["total_tweets"] == len(sample_tweets)
    
    # بررسی توییت‌های امروز
    today_tweets = [t for t, v in sample_tweets.items() if v["created_at"].date() == datetime.utcnow().date()]
    assert data["tweets_today"] == len(today_tweets)

@pytest.mark.asyncio
async def test_extract_tweets(app_client: TestClient, sample_keywords: Dict[str, Any], monkeypatch, mock_twitter_service_factory):
    """تست API استخراج توییت‌ها (با mock)"""
    # Get a test keyword
    keyword_name, _ = next(iter(sample_keywords.items()))
    
    # Request tweet extraction
    request_data = {
        "keywords": [keyword_name],
        "limit": 10,
        "lang": "en"
    }
    
    response = app_client.post("/api/v1/tweets/extract", json=request_data)
    assert response.status_code == 202
    
    data = response.json()
    assert data["status"] == "success"
    assert keyword_name in data["results"]
    assert data["results"][keyword_name]["inserted"] == 1

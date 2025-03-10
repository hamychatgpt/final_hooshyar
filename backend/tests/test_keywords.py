import pytest
from fastapi.testclient import TestClient
from typing import Dict, Any

@pytest.mark.asyncio
async def test_get_keywords_empty(app_client: TestClient):
    """تست دریافت لیست کلمات کلیدی خالی"""
    response = app_client.get("/api/v1/keywords/")
    assert response.status_code == 200
    
    data = response.json()
    assert "total" in data
    assert "keywords" in data
    assert data["total"] == 0
    assert len(data["keywords"]) == 0

@pytest.mark.asyncio
async def test_create_keyword(app_client: TestClient):
    """تست ایجاد کلمه کلیدی جدید"""
    # داده آزمون
    test_keyword = {
        "keyword": "python",
        "is_active": True,
        "description": "Python programming language",
        "priority": 1,
        "max_tweets_per_request": 100,
        "tags": ["programming", "language"],
        "extraction_frequency": 60
    }
    
    # ارسال درخواست
    response = app_client.post("/api/v1/keywords/", json=test_keyword)
    assert response.status_code == 201
    
    # بررسی پاسخ
    data = response.json()
    assert data["keyword"] == test_keyword["keyword"]
    assert data["is_active"] == test_keyword["is_active"]
    assert data["description"] == test_keyword["description"]
    assert data["priority"] == test_keyword["priority"]
    assert data["max_tweets_per_request"] == test_keyword["max_tweets_per_request"]
    assert set(data["tags"]) == set(test_keyword["tags"])
    assert data["extraction_frequency"] == test_keyword["extraction_frequency"]
    assert "id" in data
    assert "created_at" in data
    assert "updated_at" in data
    assert "total_tweets" in data
    assert data["total_tweets"] == 0

@pytest.mark.asyncio
async def test_get_keywords_with_data(app_client: TestClient, sample_keywords: Dict[str, Any]):
    """تست دریافت لیست کلمات کلیدی با داده موجود"""
    response = app_client.get("/api/v1/keywords/")
    assert response.status_code == 200
    
    data = response.json()
    assert data["total"] == len(sample_keywords)
    assert len(data["keywords"]) == len(sample_keywords)
    
    # بررسی وجود کلمات کلیدی نمونه در نتایج
    keywords_dict = {k["keyword"]: k for k in data["keywords"]}
    for keyword, details in sample_keywords.items():
        assert keyword in keywords_dict
        assert keywords_dict[keyword]["description"] == details["description"]

@pytest.mark.asyncio
async def test_get_keyword_by_id(app_client: TestClient, sample_keywords: Dict[str, Any]):
    """تست دریافت کلمه کلیدی با شناسه"""
    # انتخاب یک کلمه کلیدی
    keyword_name, keyword_data = next(iter(sample_keywords.items()))
    keyword_id = keyword_data["id"]
    
    # ارسال درخواست
    response = app_client.get(f"/api/v1/keywords/{keyword_id}")
    assert response.status_code == 200
    
    # بررسی پاسخ
    data = response.json()
    assert data["id"] == keyword_id
    assert data["keyword"] == keyword_name
    assert data["description"] == keyword_data["description"]

@pytest.mark.asyncio
async def test_get_keyword_not_found(app_client: TestClient):
    """تست دریافت کلمه کلیدی با شناسه نامعتبر"""
    response = app_client.get("/api/v1/keywords/000000000000000000000000")
    assert response.status_code == 404

@pytest.mark.asyncio
async def test_update_keyword(app_client: TestClient, sample_keywords: Dict[str, Any]):
    """تست به‌روزرسانی کلمه کلیدی"""
    # انتخاب یک کلمه کلیدی
    keyword_name, keyword_data = next(iter(sample_keywords.items()))
    keyword_id = keyword_data["id"]
    
    # داده به‌روزرسانی
    update_data = {
        "description": "Updated description",
        "is_active": not keyword_data["is_active"],
        "priority": 3
    }
    
    # ارسال درخواست
    response = app_client.put(f"/api/v1/keywords/{keyword_id}", json=update_data)
    assert response.status_code == 200
    
    # بررسی پاسخ
    data = response.json()
    assert data["id"] == keyword_id
    assert data["keyword"] == keyword_name
    assert data["description"] == update_data["description"]
    assert data["is_active"] == update_data["is_active"]
    assert data["priority"] == update_data["priority"]
    
    # بررسی فیلدهایی که تغییر نکرده‌اند
    assert data["max_tweets_per_request"] == keyword_data["max_tweets_per_request"]
    assert set(data["tags"]) == set(keyword_data["tags"])

@pytest.mark.asyncio
async def test_delete_keyword(app_client: TestClient, sample_keywords: Dict[str, Any]):
    """تست حذف کلمه کلیدی"""
    # انتخاب یک کلمه کلیدی
    keyword_name, keyword_data = next(iter(sample_keywords.items()))
    keyword_id = keyword_data["id"]
    
    # ارسال درخواست
    response = app_client.delete(f"/api/v1/keywords/{keyword_id}")
    assert response.status_code == 204
    
    # بررسی حذف کلمه کلیدی
    response = app_client.get(f"/api/v1/keywords/{keyword_id}")
    assert response.status_code == 404
    
    # بررسی کاهش تعداد کلمات کلیدی
    response = app_client.get("/api/v1/keywords/")
    data = response.json()
    assert data["total"] == len(sample_keywords) - 1

@pytest.mark.asyncio
async def test_filter_keywords(app_client: TestClient, sample_keywords: Dict[str, Any]):
    """تست فیلتر کلمات کلیدی"""
    # فیلتر براساس وضعیت فعال
    response = app_client.get("/api/v1/keywords/?is_active=true")
    assert response.status_code == 200
    
    data = response.json()
    active_keywords = [k for k, v in sample_keywords.items() if v["is_active"]]
    assert data["total"] == len(active_keywords)
    assert all(k["is_active"] for k in data["keywords"])
    
    # فیلتر براساس تگ
    response = app_client.get("/api/v1/keywords/?tag=sample")
    assert response.status_code == 200
    
    data = response.json()
    keywords_with_tag = [k for k, v in sample_keywords.items() if "sample" in v["tags"]]
    assert data["total"] == len(keywords_with_tag)
    
    # فیلتر براساس اولویت
    response = app_client.get("/api/v1/keywords/?priority=1")
    assert response.status_code == 200
    
    data = response.json()
    priority_keywords = [k for k, v in sample_keywords.items() if v["priority"] == 1]
    assert data["total"] == len(priority_keywords)
    assert all(k["priority"] == 1 for k in data["keywords"])

@pytest.mark.asyncio
async def test_duplicate_keyword(app_client: TestClient, sample_keywords: Dict[str, Any]):
    """تست ایجاد کلمه کلیدی تکراری"""
    # انتخاب یک کلمه کلیدی موجود
    keyword_name, keyword_data = next(iter(sample_keywords.items()))
    
    # تلاش برای ایجاد کلمه کلیدی با نام تکراری
    test_keyword = {
        "keyword": keyword_name,
        "is_active": True,
        "description": "Duplicate keyword",
        "priority": 1
    }
    
    # ارسال درخواست
    response = app_client.post("/api/v1/keywords/", json=test_keyword)
    assert response.status_code == 409  # Conflict

@pytest.mark.asyncio
async def test_keyword_validation(app_client: TestClient):
    """تست اعتبارسنجی داده‌های کلمه کلیدی"""
    # تست با اولویت نامعتبر
    test_keyword = {
        "keyword": "invalid_priority",
        "priority": 10  # خارج از محدوده مجاز (1-5)
    }
    
    response = app_client.post("/api/v1/keywords/", json=test_keyword)
    assert response.status_code == 422  # Unprocessable Entity
    
    # تست با فرکانس استخراج نامعتبر
    test_keyword = {
        "keyword": "invalid_frequency",
        "extraction_frequency": 5  # کمتر از حداقل (15)
    }
    
    response = app_client.post("/api/v1/keywords/", json=test_keyword)
    assert response.status_code == 422  # Unprocessable Entity
    
    # تست با تعداد توییت نامعتبر
    test_keyword = {
        "keyword": "invalid_max_tweets",
        "max_tweets_per_request": 5  # کمتر از حداقل (10)
    }
    
    response = app_client.post("/api/v1/keywords/", json=test_keyword)
    assert response.status_code == 422  # Unprocessable Entity

@pytest.mark.asyncio
async def test_keyword_stats(app_client: TestClient, sample_keywords: Dict[str, Any], sample_tweets: Dict[str, Any]):
    """تست آمار کلمات کلیدی"""
    response = app_client.get("/api/v1/keywords/stats")
    assert response.status_code == 200
    
    data = response.json()
    assert "total_keywords" in data
    assert "active_keywords" in data
    assert "keywords_by_priority" in data
    
    # بررسی تعداد کل کلمات کلیدی
    assert data["total_keywords"] == len(sample_keywords)
    
    # بررسی تعداد کلمات کلیدی فعال
    active_count = sum(1 for k in sample_keywords.values() if k["is_active"])
    assert data["active_keywords"] == active_count

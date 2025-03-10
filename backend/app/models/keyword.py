from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field
from bson import ObjectId
from .tweet import PyObjectId


class KeywordBase(BaseModel):
    """مدل پایه برای کلمات کلیدی"""
    keyword: str
    is_active: bool = True
    description: Optional[str] = None
    priority: int = 1  # 1 (بالاترین) تا 5 (پایین‌ترین)
    max_tweets_per_request: int = 100
    tags: List[str] = []
    extraction_frequency: int = 60  # زمان بین استخراج‌ها به دقیقه


class KeywordInDB(KeywordBase):
    """مدل کلمه کلیدی ذخیره شده در دیتابیس"""
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    total_tweets: int = 0
    last_extracted_at: Optional[datetime] = None
    
    class Config:
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}
        schema_extra = {
            "example": {
                "_id": "604f0c3c2e15f0b236c7c8a9",
                "keyword": "فیلترینگ",
                "is_active": True,
                "description": "Posts about internet filtering",
                "priority": 1,
                "max_tweets_per_request": 100,
                "tags": ["internet", "filtering"],
                "extraction_frequency": 60,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
                "total_tweets": 0,
                "last_extracted_at": None
            }
        }


class KeywordCreate(KeywordBase):
    """مدل برای ایجاد کلمه کلیدی جدید"""
    pass


class KeywordUpdate(BaseModel):
    """مدل برای به‌روزرسانی کلمه کلیدی موجود"""
    keyword: Optional[str] = None
    is_active: Optional[bool] = None
    description: Optional[str] = None
    priority: Optional[int] = None
    max_tweets_per_request: Optional[int] = None
    tags: Optional[List[str]] = None
    extraction_frequency: Optional[int] = None


def create_keyword_indexes(db):
    """ایجاد ایندکس‌های کالکشن کلمات کلیدی"""
    db["keywords"].create_index("keyword", unique=True)
    db["keywords"].create_index("is_active")
    db["keywords"].create_index("priority")
    db["keywords"].create_index("last_extracted_at")
    
    # ایندکس‌های ترکیبی برای جستجوهای رایج
    db["keywords"].create_index([("is_active", 1), ("priority", 1)])
    db["keywords"].create_index([("tags", 1), ("is_active", 1)])

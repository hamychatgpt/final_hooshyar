from datetime import datetime
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
from bson import ObjectId


class PyObjectId(ObjectId):
    """کلاس کمکی برای تبدیل ObjectId به رشته و بالعکس"""
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v):
        if not ObjectId.is_valid(v):
            raise ValueError("Invalid ObjectId")
        return ObjectId(v)

    @classmethod
    def __modify_schema__(cls, field_schema):
        field_schema.update(type="string")


class TweetBase(BaseModel):
    """مدل پایه برای داده‌های توییتر"""
    tweet_id: str
    text: str
    created_at: datetime
    lang: str
    user_id: str
    user_screen_name: str
    user_name: str
    user_verified: bool
    user_followers_count: int
    user_friends_count: int
    retweet_count: int
    favorite_count: int
    quote_count: Optional[int] = 0
    reply_count: Optional[int] = 0
    hashtags: List[str] = []
    mentions: List[Dict[str, str]] = []
    urls: List[str] = []
    media: List[Dict[str, str]] = []
    is_retweet: bool = False
    is_quote: bool = False
    is_reply: bool = False
    in_reply_to_status_id: Optional[str] = None
    in_reply_to_user_id: Optional[str] = None
    in_reply_to_screen_name: Optional[str] = None
    quoted_status_id: Optional[str] = None
    retweeted_status_id: Optional[str] = None
    raw_data: Dict[str, Any] = {}  # ذخیره داده‌های خام توییت
    keywords: List[str] = []  # کلمات کلیدی که باعث استخراج این توییت شده‌اند


class TweetInDB(TweetBase):
    """مدل توییت ذخیره شده در دیتابیس"""
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    created_in_db: datetime = Field(default_factory=datetime.utcnow)
    updated_in_db: datetime = Field(default_factory=datetime.utcnow)
    is_processed: bool = False
    importance_score: float = 0.0  # امتیاز اهمیت توییت
    sentiment_score: Optional[float] = None  # نتیجه تحلیل احساسات
    sentiment_label: Optional[str] = None  # برچسب احساسات (مثبت، منفی، خنثی)
    topics: List[str] = []  # موضوعات استخراج شده از توییت
    is_sensitive: bool = False  # پرچم محتوای حساس

    class Config:
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}
        schema_extra = {
            "example": {
                "_id": "604f0c3c2e15f0b236c7c8a9",
                "tweet_id": "1372938593675001857",
                "text": "This is a sample tweet text",
                "created_at": datetime.utcnow(),
                "lang": "fa",
                "user_id": "2244994945",
                "user_screen_name": "username",
                "user_name": "User Name",
                "user_verified": False,
                "user_followers_count": 1000,
                "user_friends_count": 500,
                "retweet_count": 10,
                "favorite_count": 20,
                "hashtags": ["sample", "test"],
                "keywords": ["sample"],
                "created_in_db": datetime.utcnow(),
                "updated_in_db": datetime.utcnow(),
                "is_processed": False,
                "importance_score": 0.5
            }
        }


def create_tweet_indexes(db):
    """ایجاد ایندکس‌های کالکشن توییت‌ها"""
    db["tweets"].create_index("tweet_id", unique=True)
    db["tweets"].create_index("created_at")
    db["tweets"].create_index("keywords")
    db["tweets"].create_index("user_id")
    db["tweets"].create_index("importance_score")
    db["tweets"].create_index([("text", "text")], default_language="none")  # ایندکس متنی برای جستجو
    
    # ایندکس‌های ترکیبی برای جستجوهای رایج
    db["tweets"].create_index([("created_at", -1), ("importance_score", -1)])
    db["tweets"].create_index([("user_screen_name", 1), ("created_at", -1)])
    db["tweets"].create_index([("sentiment_label", 1), ("created_at", -1)])

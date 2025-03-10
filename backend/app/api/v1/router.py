from fastapi import APIRouter
from app.api.v1.endpoints import tweets, keywords

# روتر اصلی API
api_router = APIRouter()

# اضافه کردن روترهای نقاط انتهایی مختلف
api_router.include_router(tweets.router, prefix="/tweets", tags=["tweets"])
api_router.include_router(keywords.router, prefix="/keywords", tags=["keywords"])

# روترهای اضافی در آینده می‌توانند به اینجا اضافه شوند
# مثال:
# api_router.include_router(analytics.router, prefix="/analytics", tags=["analytics"])
# api_router.include_router(profiles.router, prefix="/profiles", tags=["profiles"])

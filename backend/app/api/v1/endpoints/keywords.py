from fastapi import APIRouter, Depends, HTTPException, Query, Path, Body
from typing import List, Dict, Any, Optional
from datetime import datetime
from bson import ObjectId
from pydantic import ValidationError

from app.core.logging import get_logger
from app.core.db import get_collection
from app.models.keyword import KeywordCreate, KeywordUpdate, KeywordInDB

logger = get_logger("app.api.keywords")

router = APIRouter()

@router.get("/", summary="Get keywords with filters")
async def get_keywords(
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    tag: Optional[str] = Query(None, description="Filter by tag"),
    priority: Optional[int] = Query(None, ge=1, le=5, description="Filter by priority"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page")
):
    """
    دریافت کلمات کلیدی با فیلترهای مختلف
    """
    try:
        keywords_collection = get_collection("keywords")
        
        # ساخت کوئری
        query = {}
        
        # اعمال فیلترها
        if is_active is not None:
            query["is_active"] = is_active
        
        if tag:
            query["tags"] = tag
        
        if priority:
            query["priority"] = priority
        
        # اجرای کوئری با صفحه‌بندی
        total_count = await keywords_collection.count_documents(query)
        
        skip = (page - 1) * page_size
        cursor = keywords_collection.find(query).sort("priority", 1).skip(skip).limit(page_size)
        
        keywords = []
        async for keyword in cursor:
            # تبدیل ObjectId به رشته
            keyword["id"] = str(keyword.pop("_id"))
            keywords.append(keyword)
        
        return {
            "total": total_count,
            "page": page,
            "page_size": page_size,
            "keywords": keywords
        }
        
    except Exception as e:
        logger.error(f"Error getting keywords: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving keywords: {str(e)}"
        )

@router.post("/", status_code=201, summary="Create new keyword")
async def create_keyword(
    keyword: KeywordCreate = Body(...)
):
    """
    ایجاد کلمه کلیدی جدید
    """
    try:
        keywords_collection = get_collection("keywords")
        
        # بررسی تکراری بودن کلمه کلیدی
        existing = await keywords_collection.find_one({"keyword": keyword.keyword})
        if existing:
            raise HTTPException(
                status_code=409,
                detail=f"Keyword '{keyword.keyword}' already exists"
            )
        
        # ایجاد مدل کلمه کلیدی
        keyword_db = KeywordInDB(**keyword.dict())
        
        # ذخیره در دیتابیس
        result = await keywords_collection.insert_one(keyword_db.dict(by_alias=True))
        
        # بازیابی کلمه کلیدی ذخیره شده
        created_keyword = await keywords_collection.find_one({"_id": result.inserted_id})
        created_keyword["id"] = str(created_keyword.pop("_id"))
        
        return created_keyword
        
    except ValidationError as e:
        logger.error(f"Validation error creating keyword: {e}")
        raise HTTPException(
            status_code=422,
            detail=f"Validation error: {str(e)}"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating keyword: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error creating keyword: {str(e)}"
        )

@router.get("/{keyword_id}", summary="Get keyword by ID")
async def get_keyword(
    keyword_id: str = Path(..., description="Keyword ID")
):
    """
    دریافت یک کلمه کلیدی با شناسه
    """
    try:
        keywords_collection = get_collection("keywords")
        
        # تبدیل شناسه به ObjectId
        try:
            object_id = ObjectId(keyword_id)
        except:
            raise HTTPException(
                status_code=400,
                detail="Invalid keyword ID format"
            )
        
        # جستجوی کلمه کلیدی
        keyword = await keywords_collection.find_one({"_id": object_id})
        
        if not keyword:
            raise HTTPException(
                status_code=404,
                detail=f"Keyword with ID {keyword_id} not found"
            )
        
        # تبدیل ObjectId به رشته
        keyword["id"] = str(keyword.pop("_id"))
        
        return keyword
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting keyword {keyword_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving keyword: {str(e)}"
        )

@router.put("/{keyword_id}", summary="Update keyword")
async def update_keyword(
    keyword_id: str = Path(..., description="Keyword ID"),
    keyword_update: KeywordUpdate = Body(...)
):
    """
    به‌روزرسانی کلمه کلیدی
    """
    try:
        keywords_collection = get_collection("keywords")
        
        # تبدیل شناسه به ObjectId
        try:
            object_id = ObjectId(keyword_id)
        except:
            raise HTTPException(
                status_code=400,
                detail="Invalid keyword ID format"
            )
        
        # بررسی وجود کلمه کلیدی
        existing = await keywords_collection.find_one({"_id": object_id})
        if not existing:
            raise HTTPException(
                status_code=404,
                detail=f"Keyword with ID {keyword_id} not found"
            )
        
        # اگر نام کلمه کلیدی تغییر کرده، بررسی تکراری بودن
        if keyword_update.keyword and keyword_update.keyword != existing["keyword"]:
            duplicate = await keywords_collection.find_one({"keyword": keyword_update.keyword})
            if duplicate:
                raise HTTPException(
                    status_code=409,
                    detail=f"Keyword '{keyword_update.keyword}' already exists"
                )
        
        # ساخت داده‌های به‌روزرسانی
        update_data = {}
        for field, value in keyword_update.dict(exclude_unset=True).items():
            if value is not None:
                update_data[field] = value
        
        # اضافه کردن زمان به‌روزرسانی
        update_data["updated_at"] = datetime.utcnow()
        
        # به‌روزرسانی در دیتابیس
        await keywords_collection.update_one(
            {"_id": object_id},
            {"$set": update_data}
        )
        
        # بازیابی کلمه کلیدی به‌روزرسانی شده
        updated_keyword = await keywords_collection.find_one({"_id": object_id})
        updated_keyword["id"] = str(updated_keyword.pop("_id"))
        
        return updated_keyword
        
    except ValidationError as e:
        logger.error(f"Validation error updating keyword: {e}")
        raise HTTPException(
            status_code=422,
            detail=f"Validation error: {str(e)}"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating keyword {keyword_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error updating keyword: {str(e)}"
        )

@router.delete("/{keyword_id}", status_code=204, summary="Delete keyword")
async def delete_keyword(
    keyword_id: str = Path(..., description="Keyword ID")
):
    """
    حذف کلمه کلیدی
    """
    try:
        keywords_collection = get_collection("keywords")
        
        # تبدیل شناسه به ObjectId
        try:
            object_id = ObjectId(keyword_id)
        except:
            raise HTTPException(
                status_code=400,
                detail="Invalid keyword ID format"
            )
        
        # حذف کلمه کلیدی
        result = await keywords_collection.delete_one({"_id": object_id})
        
        if result.deleted_count == 0:
            raise HTTPException(
                status_code=404,
                detail=f"Keyword with ID {keyword_id} not found"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting keyword {keyword_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error deleting keyword: {str(e)}"
        )

@router.get("/stats", summary="Get keyword statistics")
async def get_keyword_stats():
    """
    دریافت آمار کلمات کلیدی
    """
    try:
        keywords_collection = get_collection("keywords")
        tweets_collection = get_collection("tweets")
        
        # تعداد کل کلمات کلیدی
        total_keywords = await keywords_collection.count_documents({})
        
        # تعداد کلمات کلیدی فعال
        active_keywords = await keywords_collection.count_documents({"is_active": True})
        
        # کلمات کلیدی به تفکیک اولویت
        pipeline = [
            {"$group": {"_id": "$priority", "count": {"$sum": 1}}},
            {"$sort": {"_id": 1}}
        ]
        priority_cursor = keywords_collection.aggregate(pipeline)
        keywords_by_priority = {}
        async for item in priority_cursor:
            keywords_by_priority[str(item["_id"])] = item["count"]
        
        # پراستفاده‌ترین کلمات کلیدی
        pipeline = [
            {"$unwind": "$keywords"},
            {"$group": {"_id": "$keywords", "total_tweets": {"$sum": 1}}},
            {"$sort": {"total_tweets": -1}},
            {"$limit": 10}
        ]
        tweets_cursor = tweets_collection.aggregate(pipeline)
        most_used_keywords = []
        async for item in tweets_cursor:
            keyword_info = await keywords_collection.find_one({"keyword": item["_id"]})
            most_used_keywords.append({
                "keyword": item["_id"],
                "total_tweets": item["total_tweets"],
                "is_active": keyword_info["is_active"] if keyword_info else False,
                "priority": keyword_info["priority"] if keyword_info else None
            })
        
        return {
            "total_keywords": total_keywords,
            "active_keywords": active_keywords,
            "keywords_by_priority": keywords_by_priority,
            "most_used_keywords": most_used_keywords
        }
        
    except Exception as e:
        logger.error(f"Error getting keyword stats: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving keyword statistics: {str(e)}"
        )
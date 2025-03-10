import streamlit as st
import pandas as pd
from datetime import datetime
from typing import Dict, Any, List, Optional, Union, Callable
import re

def apply_custom_css():
    """اعمال استایل‌های سفارشی به برنامه"""
    
    # استایل کلی
    st.markdown("""
    <style>
        /* فونت و رنگ بندی */
        body {
            font-family: "Vazirmatn", "Segoe UI", Tahoma, sans-serif;
            color: #1A1A1A;
        }
        
        /* کارت‌ها */
        .card {
            border-radius: 10px;
            border: 1px solid rgba(49, 51, 63, 0.2);
            padding: 1.5rem;
            margin-bottom: 1rem;
            background-color: white;
            box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05);
        }
        
        /* استایل خاص برای توییت کارت */
        .tweet-card {
            border-radius: 10px;
            border: 1px solid rgba(29, 161, 242, 0.2);
            padding: 1rem;
            margin-bottom: 1rem;
            background-color: white;
            box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05);
        }
        
        /* هدر توییت */
        .tweet-header {
            display: flex;
            margin-bottom: 0.5rem;
        }
        
        /* نام کاربر */
        .user-name {
            font-weight: bold;
            color: #333;
        }
        
        /* نام کاربری */
        .screen-name {
            color: #657786;
            margin-left: 0.5rem;
        }
        
        /* متن توییت */
        .tweet-text {
            white-space: pre-wrap;
            margin-bottom: 0.5rem;
        }
        
        /* برچسب‌ها */
        .badge {
            display: inline-block;
            padding: 3px 8px;
            border-radius: 12px;
            font-size: 0.75rem;
            margin-right: 0.5rem;
            font-weight: bold;
            color: white;
        }
        
        /* رنگ‌های برچسب */
        .badge-blue { background-color: #1DA1F2; }
        .badge-green { background-color: #17bf63; }
        .badge-red { background-color: #e0245e; }
        .badge-gray { background-color: #657786; }
        
        /* کارت آمار */
        .stat-card {
            text-align: center;
            padding: 1rem;
            border-radius: 10px;
            margin-bottom: 1rem;
            background-color: white;
            box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
        }
        
        .stat-value {
            font-size: 2rem;
            font-weight: bold;
            margin: 0.5rem 0;
        }
        
        .stat-label {
            color: #657786;
            font-size: 0.9rem;
        }
        
        /* برای هماهنگی نمودارها */
        .chart-container {
            border-radius: 10px;
            border: 1px solid rgba(49, 51, 63, 0.2);
            padding: 1rem;
            margin-bottom: 1rem;
        }
    </style>
    """, unsafe_allow_html=True)

def format_number(num: Union[int, float]) -> str:
    """قالب‌بندی اعداد برای نمایش
    
    Args:
        num: عدد برای قالب‌بندی
        
    Returns:
        رشته قالب‌بندی شده
    """
    if num is None:
        return "-"
    
    if isinstance(num, int) or num.is_integer():
        return f"{int(num):,}"
    else:
        return f"{num:,.2f}"

def format_datetime(dt) -> str:
    """قالب‌بندی تاریخ و زمان
    
    Args:
        dt: شیء تاریخ/زمان یا رشته
        
    Returns:
        رشته قالب‌بندی شده
    """
    if dt is None:
        return "-"
    
    # تبدیل رشته به تاریخ/زمان
    if isinstance(dt, str):
        try:
            # تلاش برای تبدیل رشته ISO به تاریخ/زمان
            dt = datetime.fromisoformat(dt.replace("Z", "+00:00"))
        except:
            return dt
    
    # قالب‌بندی تاریخ/زمان
    try:
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except:
        return str(dt)

def get_tweet_url(tweet_id: str, user_screen_name: Optional[str] = None) -> str:
    """تولید URL توییت
    
    Args:
        tweet_id: شناسه توییت
        user_screen_name: نام کاربری کاربر (اختیاری)
        
    Returns:
        URL توییت
    """
    if user_screen_name:
        return f"https://twitter.com/{user_screen_name}/status/{tweet_id}"
    else:
        return f"https://twitter.com/i/web/status/{tweet_id}"

def render_tweet_card(tweet: Dict[str, Any]) -> str:
    """تولید HTML برای نمایش کارت توییت
    
    Args:
        tweet: داده‌های توییت
        
    Returns:
        HTML کارت توییت
    """
    # استخراج داده‌های توییت
    tweet_id = tweet.get("tweet_id")
    text = tweet.get("text", "")
    created_at = format_datetime(tweet.get("created_at"))
    user_name = tweet.get("user_name", "")
    user_screen_name = tweet.get("user_screen_name", "")
    user_verified = tweet.get("user_verified", False)
    retweet_count = tweet.get("retweet_count", 0)
    favorite_count = tweet.get("favorite_count", 0)
    reply_count = tweet.get("reply_count", 0)
    
    # تولید HTML
    html = f"""
    <div class="tweet-card">
        <div class="tweet-header">
            <div class="user-info">
                <span class="user-name">{user_name}</span>
                {' ✓' if user_verified else ''}
                <span class="screen-name">@{user_screen_name}</span>
            </div>
            <div style="flex-grow: 1;"></div>
            <div class="tweet-date">
                {created_at}
            </div>
        </div>
        
        <div class="tweet-text">
            {text}
        </div>
        
        <div class="tweet-hashtags">
    """
    
    # افزودن هشتگ‌ها
    for hashtag in tweet.get("hashtags", []):
        html += f'<span class="badge badge-blue">#{hashtag}</span>'
    
    html += """
        </div>
        
        <div class="tweet-stats" style="display: flex; justify-content: space-between; margin-top: 0.5rem;">
    """
    
    # آمار توییت
    html += f"""
            <div>
                <span style="color: #657786;">Retweets:</span> {retweet_count}
            </div>
            <div>
                <span style="color: #657786;">Likes:</span> {favorite_count}
            </div>
            <div>
                <span style="color: #657786;">Replies:</span> {reply_count}
            </div>
            <div>
                <a href="{get_tweet_url(tweet_id, user_screen_name)}" target="_blank" style="color: #1DA1F2;">View on Twitter</a>
            </div>
    """
    
    html += """
        </div>
    </div>
    """
    
    return html

def render_stat_card(value: Union[int, float, str], label: str, color: str = "#1DA1F2") -> str:
    """تولید HTML برای نمایش کارت آمار
    
    Args:
        value: مقدار آمار
        label: برچسب آمار
        color: رنگ کارت
        
    Returns:
        HTML کارت آمار
    """
    # قالب‌بندی مقدار اگر عدد باشد
    if isinstance(value, (int, float)):
        formatted_value = format_number(value)
    else:
        formatted_value = value
    
    html = f"""
    <div class="stat-card" style="border-left: 5px solid {color};">
        <div class="stat-value" style="color: {color};">
            {formatted_value}
        </div>
        <div class="stat-label">
            {label}
        </div>
    </div>
    """
    
    return html

def show_error(message: str, detail: Optional[str] = None) -> None:
    """نمایش پیام خطا
    
    Args:
        message: پیام خطا
        detail: جزئیات خطا (اختیاری)
    """
    st.error(message)
    if detail:
        with st.expander("جزئیات خطا"):
            st.code(detail)

def show_api_error(response: Dict[str, Any]) -> None:
    """نمایش خطای API
    
    Args:
        response: پاسخ API که حاوی خطاست
    """
    if "error" in response:
        show_error(
            message=response["error"],
            detail=response.get("detail", "No additional details")
        )
    else:
        show_error("خطای نامشخص در ارتباط با سرور")

def with_loading(label: str = "در حال بارگذاری...") -> Callable:
    """دکوراتور برای نمایش نشانگر بارگذاری
    
    Args:
        label: برچسب نشانگر بارگذاری
        
    Returns:
        دکوراتور
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            with st.spinner(label):
                return func(*args, **kwargs)
        return wrapper
    return decorator

def format_duration(seconds: Union[int, float]) -> str:
    """قالب‌بندی مدت زمان به ثانیه
    
    Args:
        seconds: مدت زمان به ثانیه
        
    Returns:
        رشته قالب‌بندی شده
    """
    if seconds < 60:
        return f"{seconds:.1f} ثانیه"
    elif seconds < 3600:
        minutes = seconds / 60
        return f"{minutes:.1f} دقیقه"
    else:
        hours = seconds / 3600
        return f"{hours:.1f} ساعت"

def render_code_block(code: str, language: str = "") -> str:
    """تولید HTML برای نمایش بلوک کد
    
    Args:
        code: کد برای نمایش
        language: زبان کد (اختیاری)
        
    Returns:
        HTML بلوک کد
    """
    html = f"""
    <div style="background-color: #f6f8fa; border-radius: 5px; padding: 1rem; margin: 1rem 0; overflow: auto;">
        <pre style="margin: 0;"><code class="language-{language}">{code}</code></pre>
    </div>
    """
    
    return html

def truncate_text(text: str, max_length: int = 100) -> str:
    """کوتاه کردن متن طولانی
    
    Args:
        text: متن برای کوتاه کردن
        max_length: حداکثر طول
        
    Returns:
        متن کوتاه شده
    """
    if not text:
        return ""
    
    if len(text) <= max_length:
        return text
    
    return text[:max_length - 3] + "..."

def camel_to_snake(name: str) -> str:
    """تبدیل نام camelCase به snake_case
    
    Args:
        name: نام به فرمت camelCase
        
    Returns:
        نام به فرمت snake_case
    """
    pattern = re.compile(r'(?<!^)(?=[A-Z])')
    return pattern.sub('_', name).lower()

def snake_to_camel(name: str) -> str:
    """تبدیل نام snake_case به camelCase
    
    Args:
        name: نام به فرمت snake_case
        
    Returns:
        نام به فرمت camelCase
    """
    components = name.split('_')
    return components[0] + ''.join(x.title() for x in components[1:])

def format_json(data: Any) -> str:
    """قالب‌بندی داده به صورت JSON خوانا
    
    Args:
        data: داده برای قالب‌بندی
        
    Returns:
        رشته JSON قالب‌بندی شده
    """
    import json
    return json.dumps(data, indent=2, ensure_ascii=False)

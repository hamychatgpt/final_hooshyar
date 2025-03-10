import streamlit as st
import os
import time
from datetime import datetime
from utils.api import APIClient
from utils.ui import apply_custom_css, render_stat_card, show_api_error, with_loading

# تنظیم پیکربندی صفحه
st.set_page_config(
    page_title="سیستم پایش توییتر",
    page_icon="🐦",
    layout="wide",
    initial_sidebar_state="expanded",
)

# اعمال استایل‌های سفارشی
apply_custom_css()

# مقداردهی اولیه ارتباط با API
if "api_client" not in st.session_state:
    backend_url = os.environ.get("BACKEND_URL", "http://localhost:8000")
    st.session_state.api_client = APIClient(backend_url)
    st.session_state.app_start_time = time.time()

# نمایش نام برنامه در نوار کناری
st.sidebar.title("سیستم پایش توییتر")
st.sidebar.markdown("---")

# بررسی اتصال به سرور
if not hasattr(st.session_state, "server_connected"):
    with st.spinner("در حال بررسی اتصال به سرور..."):
        st.session_state.server_connected = st.session_state.api_client.check_health()

# نمایش وضعیت اتصال
if st.session_state.server_connected:
    st.sidebar.success("✅ اتصال به سرور برقرار است")
else:
    st.sidebar.error("❌ خطا در اتصال به سرور")
    # حالت بدون اتصال
    if st.sidebar.button("تلاش مجدد"):
        st.session_state.server_connected = st.session_state.api_client.check_health()
        st.experimental_rerun()

# نمایش اطلاعات برنامه در نوار کناری
st.sidebar.markdown("---")
st.sidebar.markdown("📊 سیستم پایش توییتر | نسخه ۱.۰.۰")
st.sidebar.markdown(f"📅 {datetime.now().strftime('%Y-%m-%d')}")

# محتوای اصلی صفحه خانه
st.title("به سیستم پایش توییتر خوش آمدید")

st.markdown("""
این سیستم به شما امکان می‌دهد توییت‌های مرتبط با کلمات کلیدی مختلف را استخراج و تحلیل کنید.

از منوی سمت راست، بخش مورد نظر خود را انتخاب کنید:
- **داشبورد**: نمای کلی از آمار و اطلاعات
- **توییت‌ها**: جستجو و مشاهده توییت‌ها
- **کلمات کلیدی**: مدیریت کلمات کلیدی
- **استخراج داده**: استخراج توییت‌های جدید
- **آمار و تحلیل**: گزارش‌ها و نمودارهای تحلیلی
- **وضعیت سیستم**: مشاهده وضعیت سیستم و عملیات نگهداری
""")

# بخش آمار سریع
st.header("آمار کلی سیستم")

@with_loading("در حال دریافت آمار...")
def load_stats():
    """بارگیری آمار سیستم"""
    try:
        # دریافت آمار توییت‌ها
        tweet_stats = st.session_state.api_client.get_tweet_stats()
        
        # دریافت آمار کلمات کلیدی
        keyword_stats = st.session_state.api_client.get_keyword_stats()
        
        return tweet_stats, keyword_stats
    except Exception as e:
        st.error(f"خطا در دریافت آمار: {str(e)}")
        return None, None

# بارگیری آمار
tweet_stats, keyword_stats = load_stats()

if tweet_stats and keyword_stats and "error" not in tweet_stats and "error" not in keyword_stats:
    # نمایش آمار در ۴ ستون
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown(render_stat_card(
            tweet_stats.get("total_tweets", 0),
            "توییت‌های کل",
            "#1DA1F2"
        ), unsafe_allow_html=True)
    
    with col2:
        st.markdown(render_stat_card(
            tweet_stats.get("tweets_today", 0),
            "توییت‌های امروز",
            "#17bf63"
        ), unsafe_allow_html=True)
    
    with col3:
        st.markdown(render_stat_card(
            keyword_stats.get("total_keywords", 0),
            "کلمات کلیدی",
            "#ffad1f"
        ), unsafe_allow_html=True)
    
    with col4:
        st.markdown(render_stat_card(
            keyword_stats.get("active_keywords", 0),
            "کلیدواژه فعال",
            "#e0245e"
        ), unsafe_allow_html=True)
    
    # آمار بیشتر در بخش بازشونده
    with st.expander("آمار بیشتر", expanded=False):
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("توییت‌ها")
            st.markdown(f"**توییت‌های ۲۴ ساعت اخیر**: {tweet_stats.get('tweets_last_24h', 0):,}")
            
            # تاریخ داده‌ها
            date_range = tweet_stats.get("date_range", {})
            oldest = date_range.get("oldest", "-")
            newest = date_range.get("newest", "-")
            
            st.markdown(f"**قدیمی‌ترین توییت**: {oldest}")
            st.markdown(f"**جدیدترین توییت**: {newest}")
        
        with col2:
            st.subheader("کلمات کلیدی")
            
            # توزیع اولویت کلمات کلیدی
            priority_data = keyword_stats.get("keywords_by_priority", {})
            st.markdown("**توزیع اولویت کلمات کلیدی**:")
            for priority, count in sorted(priority_data.items(), key=lambda x: int(x[0])):
                st.markdown(f"- اولویت {priority}: {count} کلمه کلیدی")
            
            # کلمات کلیدی پراستفاده
            st.markdown("**پراستفاده‌ترین کلمات کلیدی**:")
            most_used = keyword_stats.get("most_used_keywords", [])
            for keyword in most_used[:5]:  # نمایش ۵ مورد اول
                st.markdown(f"- {keyword.get('keyword')}: {keyword.get('total_tweets', 0):,} توییت")
else:
    if tweet_stats and "error" in tweet_stats:
        show_api_error(tweet_stats)
    elif keyword_stats and "error" in keyword_stats:
        show_api_error(keyword_stats)
    else:
        st.warning("امکان دریافت آمار وجود ندارد. لطفاً اتصال به سرور را بررسی کنید.")

# بخش دسترسی سریع
st.header("دسترسی سریع")

col1, col2, col3 = st.columns(3)

with col1:
    st.subheader("مشاهده توییت‌ها")
    if st.button("جستجوی توییت‌ها", use_container_width=True):
        st.switch_page("pages/01_tweets.py")

with col2:
    st.subheader("مدیریت کلمات کلیدی")
    if st.button("افزودن کلمه کلیدی جدید", use_container_width=True):
        st.switch_page("pages/02_keywords.py")

with col3:
    st.subheader("استخراج داده")
    if st.button("استخراج توییت‌های جدید", use_container_width=True):
        st.switch_page("pages/03_extraction.py")

# نمایش توییت‌های اخیر
st.header("توییت‌های اخیر")

@with_loading("در حال دریافت توییت‌های اخیر...")
def load_recent_tweets():
    """بارگیری توییت‌های اخیر"""
    try:
        return st.session_state.api_client.get_tweets(page=1, page_size=5)
    except Exception as e:
        st.error(f"خطا در دریافت توییت‌های اخیر: {str(e)}")
        return None

# بارگیری توییت‌های اخیر
recent_tweets = load_recent_tweets()

if recent_tweets and "error" not in recent_tweets and recent_tweets.get("tweets"):
    # نمایش توییت‌ها
    from utils.ui import render_tweet_card
    
    for tweet in recent_tweets.get("tweets", []):
        st.markdown(render_tweet_card(tweet), unsafe_allow_html=True)
    
    # دکمه مشاهده همه
    if st.button("مشاهده همه توییت‌ها", use_container_width=True):
        st.switch_page("pages/01_tweets.py")
else:
    if recent_tweets and "error" in recent_tweets:
        show_api_error(recent_tweets)
    else:
        st.info("هنوز توییتی استخراج نشده است.")
        if st.button("استخراج توییت‌های جدید", use_container_width=True):
            st.switch_page("pages/03_extraction.py")

```markdown
# سیستم پایش توییتر

سیستم پایش توییتر یک ابزار قدرتمند برای استخراج، ذخیره و تحلیل توییت‌ها بر اساس کلمات کلیدی است.

## ویژگی‌ها

- استخراج خودکار توییت‌ها بر اساس کلمات کلیدی
- ذخیره‌سازی توییت‌ها در MongoDB
- رتبه‌بندی توییت‌ها بر اساس اهمیت
- داشبورد مدیریت با Streamlit
- API کامل با FastAPI
- زمان‌بندی خودکار استخراج و به‌روزرسانی

## پیش‌نیازها

- Docker و Docker Compose
- دسترسی به API توییتر (رسمی یا TwitterAPI.io)

## راه‌اندازی سریع

1. کلون کردن مخزن:
   ```bash
   git clone https://github.com/your-repo/twitter-monitoring-system.git
   cd twitter-monitoring-system
   ```

2. ایجاد فایل `.env` از روی نمونه:
   ```bash
   cp .env.example .env
   ```

3. ویرایش فایل `.env` و تنظیم مقادیر مورد نیاز:
   - تنظیمات API توییتر
   - تنظیمات MongoDB
   - سایر تنظیمات مورد نیاز

4. راه‌اندازی با اسکریپت:
   ```bash
   chmod +x ./setup.sh
   ./setup.sh
   ```

5. دسترسی به سرویس‌ها:
   - داشبورد فرانت‌اند: http://localhost:8501
   - API بک‌اند: http://localhost:8000
   - مستندات API: http://localhost:8000/docs

## ساختار پروژه

```
twitter-monitoring-system/
├── backend/                # کدهای بک‌اند
│   ├── app/                # کد اصلی برنامه
│   │   ├── api/            # API ها
│   │   ├── core/           # هسته سیستم
│   │   ├── models/         # مدل‌های داده
│   │   ├── services/       # سرویس‌ها
│   │   └── tasks/          # وظایف زمان‌بندی شده
│   ├── tests/              # تست‌ها
│   ├── Dockerfile          # فایل داکر بک‌اند
│   └── requirements.txt    # وابستگی‌های بک‌اند
├── frontend/               # کدهای فرانت‌اند
│   ├── app.py              # برنامه اصلی Streamlit
│   ├── pages/              # صفحات داشبورد
│   ├── utils/              # توابع کمکی
│   ├── Dockerfile          # فایل داکر فرانت‌اند
│   └── requirements.txt    # وابستگی‌های فرانت‌اند
├── mongodb-init/           # اسکریپت‌های راه‌اندازی MongoDB
├── docker-compose.yml      # تنظیمات Docker Compose
├── .env.example            # نمونه فایل تنظیمات محیطی
├── setup.sh                # اسکریپت راه‌اندازی
└── run-tests.sh            # اسکریپت اجرای تست‌ها
```

## معماری سیستم

سیستم از یک معماری لایه‌بندی شده پیروی می‌کند:

1. **لایه API**: مسئول مدیریت درخواست‌ها و پاسخ‌ها (`app/api`)
2. **لایه سرویس**: منطق کسب‌وکار برنامه (`app/services`)
3. **لایه مدل**: نمایش داده‌ها و ارتباط با دیتابیس (`app/models`)
4. **لایه هسته**: قابلیت‌های مرکزی و زیرساختی (`app/core`)

## سرویس‌های توییتر

سیستم از دو سرویس مختلف برای دسترسی به API توییتر پشتیبانی می‌کند:

1. **API رسمی توییتر**: با استفاده از کتابخانه Tweepy
2. **TwitterAPI.io**: سرویس جایگزین برای دسترسی به API توییتر

نوع سرویس مورد استفاده با تنظیم `TWITTER_SERVICE_TYPE` در فایل `.env` مشخص می‌شود.

## دستورات مفید

### مدیریت سرویس‌ها

```bash
# مشاهده وضعیت سرویس‌ها
docker-compose ps

# مشاهده لاگ‌ها
docker-compose logs -f

# راه‌اندازی مجدد سرویس بک‌اند
docker-compose restart backend

# راه‌اندازی مجدد سرویس فرانت‌اند
docker-compose restart frontend

# توقف همه سرویس‌ها
docker-compose down

# راه‌اندازی همه سرویس‌ها
docker-compose up -d
```

### اجرای تست‌ها

```bash
# اجرای همه تست‌ها
./run-tests.sh

# اجرای تست‌ها با گزارش پوشش کد
./run-tests.sh --coverage

# اجرای تست‌های یک ماژول خاص
./run-tests.sh --path app/services/test_twitter_service.py
```

### پشتیبان‌گیری

```bash
# ایجاد پشتیبان از دیتابیس
docker-compose exec mongodb mongodump --out=/data/db/backup --username admin --password password --authenticationDatabase admin

# بازیابی پشتیبان
docker-compose exec mongodb mongorestore --username admin --password password --authenticationDatabase admin /data/db/backup
```

## توسعه

### قواعد نام‌گذاری

- **ماژول‌ها و پکیج‌ها**: snake_case (مانند `twitter_service.py`)
- **کلاس‌ها**: PascalCase (مانند `TweetService`)
- **متدها و توابع**: snake_case (مانند `extract_tweets()`)
- **متغیرها**: snake_case (مانند `tweet_count`)
- **ثابت‌ها**: UPPER_CASE (مانند `MAX_TWEETS_PER_REQUEST`)

### استانداردهای کد

- از docstring برای مستندسازی کلاس‌ها، توابع و ماژول‌ها استفاده کنید.
- از type hints پایتون برای مشخص کردن نوع پارامترها و مقدار بازگشتی استفاده کنید.
- استثناءهای مناسب تعریف کنید و خطاها را به درستی مدیریت کنید.
- از الگوهای طراحی مناسب مانند Dependency Injection استفاده کنید.

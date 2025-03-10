#!/bin/bash

# تنظیم رنگ‌ها برای خروجی
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# توابع کمکی
print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# بررسی آیا کانتینرها در حال اجرا هستند
BACKEND_RUNNING=$(docker ps -q -f name=twitter-monitor-backend)
if [ -z "$BACKEND_RUNNING" ]; then
    print_warning "کانتینر بک‌اند در حال اجرا نیست. در حال راه‌اندازی سرویس‌ها..."
    docker-compose up -d
    
    # انتظار برای راه‌اندازی کامل
    print_info "در حال انتظار برای راه‌اندازی کامل سرویس‌ها..."
    sleep 10
fi

# پردازش پارامترهای ورودی
TEST_ARGS=""
COVERAGE=false
VERBOSE=false

# پردازش پارامترهای ورودی
while [[ $# -gt 0 ]]; do
    case $1 in
        --coverage)
            COVERAGE=true
            shift
            ;;
        --verbose|-v)
            VERBOSE=true
            shift
            ;;
        --path)
            TEST_ARGS="$TEST_ARGS $2"
            shift 2
            ;;
        *)
            TEST_ARGS="$TEST_ARGS $1"
            shift
            ;;
    esac
done

# اضافه کردن پارامترهای مناسب برای pytest
if [ "$VERBOSE" = true ]; then
    TEST_ARGS="$TEST_ARGS -v"
fi

if [ "$COVERAGE" = true ]; then
    TEST_ARGS="$TEST_ARGS --cov=app --cov-report=term --cov-report=html"
    
    # پاک کردن گزارش‌های قبلی پوشش کد
    print_info "در حال پاک کردن گزارش‌های قبلی پوشش کد..."
    docker exec twitter-monitor-backend rm -rf htmlcov .coverage
fi

print_info "در حال اجرای تست‌ها..."
print_info "پارامترهای تست: $TEST_ARGS"

# اجرای تست‌ها در کانتینر بک‌اند
docker exec twitter-monitor-backend bash -c "cd /app && PYTHONPATH=/app pytest $TEST_ARGS"

# بررسی نتیجه اجرای تست‌ها
TEST_RESULT=$?

if [ $TEST_RESULT -eq 0 ]; then
    print_success "همه تست‌ها با موفقیت اجرا شدند."
else
    print_error "تست‌ها با خطا مواجه شدند. کد خروجی: $TEST_RESULT"
fi

# نمایش گزارش پوشش کد اگر درخواست شده باشد
if [ "$COVERAGE" = true ]; then
    print_info "در حال کپی گزارش پوشش کد..."
    
    # ایجاد دایرکتوری گزارش
    mkdir -p reports/coverage
    
    # کپی گزارش پوشش کد از کانتینر
    docker cp twitter-monitor-backend:/app/htmlcov reports/coverage
    
    print_success "گزارش پوشش کد در دایرکتوری reports/coverage ایجاد شد."
    print_info "برای مشاهده گزارش، فایل reports/coverage/htmlcov/index.html را باز کنید."
fi

exit $TEST_RESULT
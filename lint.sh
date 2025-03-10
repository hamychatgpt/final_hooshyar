#!/bin/bash

# اسکریپت بررسی کیفیت کد پروژه پایش توییتر

# تنظیم رنگ‌ها برای خروجی
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # بدون رنگ

# چاپ پیام سبز
print_success() {
    echo -e "${GREEN}$1${NC}"
}

# چاپ پیام هشدار
print_warning() {
    echo -e "${YELLOW}$1${NC}"
}

# چاپ پیام خطا
print_error() {
    echo -e "${RED}$1${NC}"
}

# چاپ پیام اطلاعات
print_info() {
    echo -e "${BLUE}$1${NC}"
}

# بررسی آیا داکر در حال اجراست
if ! docker info > /dev/null 2>&1; then
    print_error "داکر در حال اجرا نیست یا دسترسی کافی ندارید."
    print_info "لطفاً مطمئن شوید داکر در حال اجراست و دسترسی‌های لازم را دارید."
    exit 1
fi

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
FIX=false
BACKEND_ONLY=false
FRONTEND_ONLY=false
TARGET="."

while [[ $# -gt 0 ]]; do
    case $1 in
        --fix)
            FIX=true
            shift
            ;;
        --backend)
            BACKEND_ONLY=true
            shift
            ;;
        --frontend)
            FRONTEND_ONLY=true
            shift
            ;;
        --path)
            TARGET="$2"
            shift 2
            ;;
        *)
            print_error "پارامتر نامعتبر: $1"
            print_info "پارامترهای مجاز: --fix, --backend, --frontend, --path PATH"
            exit 1
            ;;
    esac
done

# تنظیم پارامترهای اجرا
if [ "$FIX" = true ]; then
    ISORT_ARGS="--profile black --line-length 100 --multi-line 3 --trailing-comma"
    BLACK_ARGS="--line-length 100"
    PRINT_MODE="در حال اصلاح"
else
    ISORT_ARGS="--profile black --line-length 100 --multi-line 3 --trailing-comma --check-only --diff"
    BLACK_ARGS="--line-length 100 --check --diff"
    PRINT_MODE="در حال بررسی"
fi

# شمارنده خطاها
ERROR_COUNT=0

# اجرای لینترها روی کد بک‌اند
if [ "$FRONTEND_ONLY" = false ]; then
    print_info "$PRINT_MODE کد بک‌اند..."
    
    # اجرای isort
    print_info "در حال اجرای isort..."
    docker exec twitter-monitor-backend bash -c "cd /app && isort $ISORT_ARGS $TARGET"
    if [ $? -ne 0 ]; then
        print_error "خطا در isort."
        ERROR_COUNT=$((ERROR_COUNT + 1))
    else
        print_success "isort: بدون خطا"
    fi
    
    # اجرای black
    print_info "در حال اجرای black..."
    docker exec twitter-monitor-backend bash -c "cd /app && black $BLACK_ARGS $TARGET"
    if [ $? -ne 0 ]; then
        print_error "خطا در black."
        ERROR_COUNT=$((ERROR_COUNT + 1))
    else
        print_success "black: بدون خطا"
    fi
    
    # اجرای flake8 (فقط بررسی)
    print_info "در حال اجرای flake8..."
    docker exec twitter-monitor-backend bash -c "cd /app && python -m flake8 --max-line-length 100 --exclude=venv,__pycache__,migrations $TARGET"
    if [ $? -ne 0 ]; then
        print_error "خطا در flake8."
        ERROR_COUNT=$((ERROR_COUNT + 1))
    else
        print_success "flake8: بدون خطا"
    fi
    
    # اجرای mypy (فقط بررسی)
    print_info "در حال اجرای mypy..."
    docker exec twitter-monitor-backend bash -c "cd /app && mypy --ignore-missing-imports $TARGET"
    if [ $? -ne 0 ]; then
        print_warning "هشدار در mypy. این خطاها برای اجرای کد حیاتی نیستند."
    else
        print_success "mypy: بدون هشدار"
    fi
fi

# اجرای لینترها روی کد فرانت‌اند
if [ "$BACKEND_ONLY" = false ]; then
    print_info "$PRINT_MODE کد فرانت‌اند..."
    
    # اجرای isort
    print_info "در حال اجرای isort..."
    docker exec twitter-monitor-frontend bash -c "cd /app && isort $ISORT_ARGS $TARGET"
    if [ $? -ne 0 ]; then
        print_error "خطا در isort."
        ERROR_COUNT=$((ERROR_COUNT + 1))
    else
        print_success "isort: بدون خطا"
    fi
    
    # اجرای black
    print_info "در حال اجرای black..."
    docker exec twitter-monitor-frontend bash -c "cd /app && black $BLACK_ARGS $TARGET"
    if [ $? -ne 0 ]; then
        print_error "خطا در black."
        ERROR_COUNT=$((ERROR_COUNT + 1))
    else
        print_success "black: بدون خطا"
    fi
    
    # اجرای flake8 (فقط بررسی)
    print_info "در حال اجرای flake8..."
    docker exec twitter-monitor-frontend bash -c "cd /app && python -m flake8 --max-line-length 100 --exclude=venv,__pycache__ $TARGET"
    if [ $? -ne 0 ]; then
        print_error "خطا در flake8."
        ERROR_COUNT=$((ERROR_COUNT + 1))
    else
        print_success "flake8: بدون خطا"
    fi
fi

# نمایش نتیجه نهایی
if [ $ERROR_COUNT -eq 0 ]; then
    print_success "تمام بررسی‌های کیفیت کد با موفقیت انجام شدند."
    exit 0
else
    print_error "$ERROR_COUNT خطا در بررسی کیفیت کد یافت شد."
    if [ "$FIX" = false ]; then
        print_info "می‌توانید با اجرای دستور './lint.sh --fix' بسیاری از این خطاها را به صورت خودکار اصلاح کنید."
    fi
    exit 1
fi

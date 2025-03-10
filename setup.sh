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

# بررسی پیش‌نیازها
check_requirements() {
    print_info "بررسی پیش‌نیازها..."
    
    # بررسی نصب داکر
    if ! command -v docker &> /dev/null; then
        print_error "Docker نصب نشده است. لطفاً ابتدا Docker را نصب کنید."
        print_info "برای نصب Docker می‌توانید از دستور زیر استفاده کنید:"
        echo "curl -fsSL https://get.docker.com -o get-docker.sh && sudo sh get-docker.sh"
        exit 1
    fi
    
    # بررسی نصب داکر-کامپوز
    if ! command -v docker-compose &> /dev/null; then
        print_error "Docker Compose نصب نشده است. لطفاً ابتدا Docker Compose را نصب کنید."
        print_info "برای نصب Docker Compose می‌توانید از دستور زیر استفاده کنید:"
        echo "sudo apt-get install -y docker-compose"
        exit 1
    fi
    
    # بررسی وجود فایل .env
    if [ ! -f .env ]; then
        print_warning "فایل .env یافت نشد. در حال ایجاد از روی نمونه..."
        if [ -f .env.example ]; then
            cp .env.example .env
            print_success "فایل .env از روی .env.example ایجاد شد."
            print_warning "لطفاً فایل .env را با مقادیر مناسب ویرایش کنید."
        else
            print_error "فایل .env.example یافت نشد. لطفاً فایل .env را به صورت دستی ایجاد کنید."
            exit 1
        fi
    fi
    
    print_success "همه پیش‌نیازها موجود هستند."
}

# ایجاد دایرکتوری‌های مورد نیاز
create_directories() {
    print_info "ایجاد دایرکتوری‌های مورد نیاز..."
    
    mkdir -p backend/logs
    mkdir -p frontend/logs
    mkdir -p mongodb-init
    
    # تنظیم دسترسی‌ها
    chmod 777 backend/logs
    chmod 777 frontend/logs
    
    # کپی اسکریپت راه‌اندازی MongoDB اگر وجود ندارد
    if [ ! -f mongodb-init/init-mongo.js ]; then
        if [ -f init-mongo.js ]; then
            cp init-mongo.js mongodb-init/
        else
            print_warning "اسکریپت init-mongo.js یافت نشد. در حال ایجاد اسکریپت پیش‌فرض..."
            cat > mongodb-init/init-mongo.js << 'EOF'
// اسکریپت راه‌اندازی اولیه پایگاه داده MongoDB

// دریافت نام کاربری، رمز عبور و نام دیتابیس از متغیرهای محیطی
const adminUser = process.env.MONGO_INITDB_ROOT_USERNAME || 'admin';
const adminPassword = process.env.MONGO_INITDB_ROOT_PASSWORD || 'password';
const dbName = process.env.MONGO_INITDB_DATABASE || 'twitter_monitor';

// ایجاد کاربر برنامه با دسترسی به دیتابیس اصلی
db.auth(adminUser, adminPassword);

db = db.getSiblingDB(dbName);

// بررسی وجود کاربر
const userExists = db.getUser('app_user');
if (!userExists) {
    // ایجاد کاربر جدید با دسترسی به دیتابیس اصلی
    db.createUser({
        user: 'app_user',
        pwd: 'app_password',
        roles: [
            { role: 'readWrite', db: dbName }
        ]
    });
    
    print('کاربر app_user با موفقیت ایجاد شد.');
} else {
    print('کاربر app_user از قبل وجود دارد.');
}

// ایجاد کالکشن‌های اصلی
const collections = [
    'tweets',
    'keywords',
    'system_settings',
    'migrations',
    'execution_logs',
    'system_stats',
    'scheduler_jobs'
];

collections.forEach(collection => {
    if (!db.getCollectionNames().includes(collection)) {
        db.createCollection(collection);
        print(`کالکشن ${collection} با موفقیت ایجاد شد.`);
    } else {
        print(`کالکشن ${collection} از قبل وجود دارد.`);
    }
});

// ایجاد ایندکس‌های کالکشن tweets
db.tweets.createIndex({ "tweet_id": 1 }, { unique: true });
db.tweets.createIndex({ "created_at": -1 });
db.tweets.createIndex({ "keywords": 1 });
db.tweets.createIndex({ "user_id": 1 });
db.tweets.createIndex({ "importance_score": -1 });
db.tweets.createIndex({ "text": "text" }, { default_language: "none" });

// ایجاد ایندکس‌های کالکشن keywords
db.keywords.createIndex({ "keyword": 1 }, { unique: true });
db.keywords.createIndex({ "is_active": 1 });
db.keywords.createIndex({ "priority": 1 });

print('ایندکس‌های مورد نیاز با موفقیت ایجاد شدند.');

// ایجاد تنظیمات پیش‌فرض سیستم
const defaultSettings = [
    { 
        key: 'extraction_enabled', 
        value: true,
        description: 'فعال بودن استخراج خودکار توییت‌ها',
        last_updated: new Date()
    },
    { 
        key: 'max_extraction_per_hour', 
        value: 5, 
        description: 'حداکثر تعداد استخراج در هر ساعت',
        last_updated: new Date()
    },
    { 
        key: 'default_language', 
        value: 'fa', 
        description: 'زبان پیش‌فرض برای استخراج توییت‌ها',
        last_updated: new Date()
    },
    { 
        key: 'system_initialized', 
        value: true, 
        description: 'وضعیت راه‌اندازی اولیه سیستم',
        last_updated: new Date()
    }
];

// اضافه کردن تنظیمات پیش‌فرض
defaultSettings.forEach(setting => {
    db.system_settings.updateOne(
        { key: setting.key },
        { $set: setting },
        { upsert: true }
    );
});
EOF
        fi
    fi
    
    print_success "دایرکتوری‌های مورد نیاز ایجاد شدند."
}

# راه‌اندازی سرویس‌ها
start_services() {
    print_info "در حال راه‌اندازی سرویس‌ها..."
    
    # تنظیم متغیر زمان شروع برنامه
    export APP_START_TIME=$(date +%s)
    
    # بررسی وضعیت فعلی سرویس‌ها
    if docker-compose ps | grep -q "twitter-monitor"; then
        print_warning "سرویس‌ها از قبل در حال اجرا هستند. در حال راه‌اندازی مجدد..."
        docker-compose down
    fi
    
    # راه‌اندازی سرویس‌ها
    docker-compose up -d --build
    
    # بررسی وضعیت راه‌اندازی
    if [ $? -eq 0 ]; then
        print_success "سرویس‌ها با موفقیت راه‌اندازی شدند."
    else
        print_error "خطا در راه‌اندازی سرویس‌ها."
        exit 1
    fi
    
    # نمایش وضعیت سرویس‌ها
    print_info "وضعیت سرویس‌ها:"
    docker-compose ps
}

# اجرای میگریشن‌ها
run_migrations() {
    print_info "در حال انتظار برای آماده شدن سرویس‌ها..."
    sleep 10
    
    print_info "در حال اجرای میگریشن‌های دیتابیس..."
    
    # اجرای میگریشن‌ها از طریق API
    curl -s -X POST http://localhost:8000/api/v1/system/migrations/run -H "Content-Type: application/json" -d '{"target_version": null}'
    
    if [ $? -eq 0 ]; then
        print_success "میگریشن‌ها با موفقیت اجرا شدند."
    else
        print_warning "خطا در اجرای میگریشن‌ها. ممکن است سرویس بک‌اند هنوز آماده نباشد."
        print_info "می‌توانید بعداً میگریشن‌ها را با دستور زیر اجرا کنید:"
        echo "curl -X POST http://localhost:8000/api/v1/system/migrations/run -H \"Content-Type: application/json\" -d '{\"target_version\": null}'"
    fi
}

# نمایش راهنمای استفاده
show_usage() {
    cat << EOF

${GREEN}سیستم پایش توییتر با موفقیت راه‌اندازی شد!${NC}

برای دسترسی به سرویس‌ها:

- داشبورد فرانت‌اند: ${BLUE}http://localhost:8501${NC}
- API بک‌اند: ${BLUE}http://localhost:8000${NC}
- مستندات API: ${BLUE}http://localhost:8000/docs${NC}

دستورات مفید:

- مشاهده لاگ‌ها:
  ${GREEN}docker-compose logs -f${NC}

- راه‌اندازی مجدد سرویس بک‌اند:
  ${GREEN}docker-compose restart backend${NC}

- راه‌اندازی مجدد سرویس فرانت‌اند:
  ${GREEN}docker-compose restart frontend${NC}

- اجرای پوسته مانگو:
  ${GREEN}docker-compose exec mongodb mongo -u admin -p password${NC}

- اجرای تست‌ها:
  ${GREEN}docker-compose exec backend pytest${NC}

- ایجاد بک‌آپ دیتابیس:
  ${GREEN}docker-compose exec mongodb mongodump --out=/data/db/backup --username admin --password password --authenticationDatabase admin${NC}

EOF
}

# تابع اصلی
main() {
    print_info "شروع راه‌اندازی سیستم پایش توییتر..."
    
    check_requirements
    create_directories
    start_services
    run_migrations
    show_usage
}

# اجرای تابع اصلی
main
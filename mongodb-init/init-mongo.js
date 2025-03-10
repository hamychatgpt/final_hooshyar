// اسکریپت راه‌اندازی اولیه پایگاه داده MongoDB

// تعریف متغیرهای مورد نیاز
const adminUser = 'admin';
const adminPassword = 'password';
const dbName = 'hooshyar';

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
db.keywords.createIndex({ "last_extracted_at": 1 });

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

print('تنظیمات پیش‌فرض سیستم با موفقیت ایجاد شدند.');
print('راه‌اندازی اولیه MongoDB با موفقیت انجام شد.');
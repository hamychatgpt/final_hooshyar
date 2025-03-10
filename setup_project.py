#!/usr/bin/env python3
"""
اسکریپت پایتون برای ایجاد ساختار پوشه‌ای پروژه پایش توییتر و انتقال فایل‌ها
همچنین ایجاد فایل‌های خالی برای تغییرات TwitterAPI.io
"""

import os
import shutil
from pathlib import Path
import re
import sys

# رنگ‌های ANSI برای خروجی
class Colors:
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    ENDC = '\033[0m'

def print_color(text, color):
    """چاپ متن رنگی"""
    print(f"{color}{text}{Colors.ENDC}")

def create_directories(base_path):
    """ایجاد ساختار پوشه‌ای پروژه"""
    print_color("ایجاد ساختار پوشه‌ای پروژه...", Colors.BLUE)
    
    directories = [
        # ساختار backend
        "backend/app/api/v1/endpoints",
        "backend/app/core",
        "backend/app/models",
        "backend/app/schemas",
        "backend/app/services",
        "backend/app/tasks",
        "backend/tests",
        "backend/migrations",
        
        # ساختار frontend
        "frontend/pages",
        "frontend/utils",
        "frontend/components"
    ]
    
    for directory in directories:
        os.makedirs(os.path.join(base_path, directory), exist_ok=True)
        print(f"  ✓ پوشه {directory} ایجاد شد")
    
    # ایجاد فایل‌های __init__.py
    init_paths = [
        "backend/app/__init__.py",
        "backend/app/api/__init__.py",
        "backend/app/api/v1/__init__.py",
        "backend/app/api/v1/endpoints/__init__.py",
        "backend/app/core/__init__.py",
        "backend/app/models/__init__.py",
        "backend/app/schemas/__init__.py",
        "backend/app/services/__init__.py",
        "backend/app/tasks/__init__.py",
        "backend/tests/__init__.py",
        "backend/migrations/__init__.py",
        "frontend/utils/__init__.py",
        "frontend/components/__init__.py"
    ]
    
    for init_file in init_paths:
        Path(os.path.join(base_path, init_file)).touch()
        print(f"  ✓ فایل {init_file} ایجاد شد")

def map_files():
    """نگاشت فایل‌های موجود به مسیرهای جدید"""
    file_mapping = {
        # backend - core
        "backend-config.py": "backend/app/core/config.py",
        "backend-db.py": "backend/app/core/db.py",
        "backend-logging.py": "backend/app/core/logging.py",
        "backend-migrations.py": "backend/app/core/migrations.py",
        
        # backend - models
        "backend-tweet-model.py": "backend/app/models/tweet.py",
        "backend-keyword-model.py": "backend/app/models/keyword.py",
        
        # backend - api
        "backend-api-router.py": "backend/app/api/v1/router.py",
        "backend-system-api.py": "backend/app/api/v1/endpoints/system.py",
        
        # backend - tasks
        "backend-scheduler.py": "backend/app/tasks/scheduler.py",
        "backend-tasks-scheduler.py": "backend/app/tasks/scheduler.py",  # احتمال تکرار
        "backend-maintenance-tasks.py": "backend/app/tasks/maintenance_tasks.py",
        "backend-twitter-tasks.py": "backend/app/tasks/twitter_tasks.py", # فایل به‌روزشده
        
        # backend - services (فایل‌های جدید)
        "backend-twitter-api-io-service.py": "backend/app/services/twitter_api_io_service.py",
        "backend-twitter-service-factory.py": "backend/app/services/factory.py",
        
        # backend - tests
        "backend-conftest.py": "backend/tests/conftest.py",
        "backend-test-tweets.py": "backend/tests/test_tweets.py",
        "backend-test-keywords.py": "backend/tests/test_keywords.py",
        
        # backend - migrations
        "backend-migration-example.py": "backend/migrations/m001_initial.py",
        
        # backend - root files
        "backend-main.py": "backend/app/main.py",
        "backend-requirements.txt": "backend/requirements.txt",
        "backend-requirements (1).txt": "backend/requirements.dev.txt",
        "env-example": "backend/.env.example", # اصلاح شده: بدون پسوند .sh
        
        # frontend files
        "frontend-app.py": "frontend/app.py",
        "frontend-api.py": "frontend/utils/api.py",
        "frontend-ui.py": "frontend/utils/ui.py",
        "frontend-requirements.txt": "frontend/requirements.txt",
        "frontend-requirements (1).txt": "frontend/requirements.dev.txt",
        "frontend-dockerfile.txt": "frontend/Dockerfile",
        
        # project root files
        "docker-compose.txt": "docker-compose.yml",
        "init-mongo.js": "init-mongo.js",
        "setup-script.sh": "setup.sh",
        "run-tests-script.sh": "run_tests.sh",
        "lint-script.sh": "lint.sh",
        "readme.txt": "README.md",
        "contributing.txt": "CONTRIBUTING.md"
    }
    
    return file_mapping

def copy_files(src_dir, dst_base, file_mapping):
    """کپی فایل‌ها به ساختار جدید"""
    print_color("انتقال فایل‌ها به ساختار جدید...", Colors.BLUE)
    
    files_copied = 0
    files_not_found = 0
    
    for src_file, dst_path in file_mapping.items():
        src_path = os.path.join(src_dir, src_file)
        dst_full_path = os.path.join(dst_base, dst_path)
        
        # بررسی نام‌های جایگزین برای env-example
        if src_file == "env-example" and not os.path.exists(src_path):
            alt_src_path = os.path.join(src_dir, "env-example.sh")
            if os.path.exists(alt_src_path):
                src_path = alt_src_path
                print(f"  ! فایل env-example.sh به جای env-example استفاده شد")
        
        if os.path.exists(src_path):
            # اطمینان از وجود دایرکتوری مقصد
            os.makedirs(os.path.dirname(dst_full_path), exist_ok=True)
            
            # کپی فایل
            shutil.copy2(src_path, dst_full_path)
            print(f"  ✓ {src_file} -> {dst_path}")
            files_copied += 1
            
            # تنظیم دسترسی‌های اجرایی برای اسکریپت‌ها
            if dst_path.endswith('.sh'):
                os.chmod(dst_full_path, 0o755)
        else:
            print(f"  ! فایل {src_file} پیدا نشد")
            files_not_found += 1
    
    return files_copied, files_not_found

def create_missing_files(dst_base):
    """ایجاد فایل‌های مفقود شده TwitterAPI.io اگر کپی نشده باشند"""
    print_color("بررسی و ایجاد فایل‌های TwitterAPI.io که ممکن است مفقود شده باشند...", Colors.BLUE)
    
    # مسیرهای فایل‌های TwitterAPI.io
    api_service_path = os.path.join(dst_base, "backend/app/services/twitter_api_io_service.py")
    factory_path = os.path.join(dst_base, "backend/app/services/factory.py")
    
    # اطمینان از وجود دایرکتوری‌ها
    os.makedirs(os.path.dirname(api_service_path), exist_ok=True)
    
    # بررسی وجود فایل‌ها و ایجاد آنها در صورت نیاز
    if not os.path.exists(api_service_path):
        print_color("  ! فایل twitter_api_io_service.py یافت نشد. ایجاد فایل خالی...", Colors.YELLOW)
        with open(api_service_path, 'w', encoding='utf-8') as f:
            f.write("# این فایل برای پیاده‌سازی سرویس TwitterAPI.io ایجاد شده است\n\n")
            f.write("# پیاده‌سازی کامل را از فایل‌های پیوست شده کپی کنید\n")
    
    if not os.path.exists(factory_path):
        print_color("  ! فایل factory.py یافت نشد. ایجاد فایل خالی...", Colors.YELLOW)
        with open(factory_path, 'w', encoding='utf-8') as f:
            f.write("# این فایل برای پیاده‌سازی فکتوری انتخاب سرویس توییتر ایجاد شده است\n\n")
            f.write("# پیاده‌سازی کامل را از فایل‌های پیوست شده کپی کنید\n")

def check_config_consistency(dst_base):
    """بررسی سازگاری تنظیمات در config.py و .env.example"""
    print_color("بررسی سازگاری تنظیمات...", Colors.BLUE)
    
    config_path = os.path.join(dst_base, "backend/app/core/config.py")
    env_path = os.path.join(dst_base, "backend/.env.example")
    
    # بررسی وجود فایل‌ها
    if not os.path.exists(config_path) or not os.path.exists(env_path):
        print_color("  ! یکی از فایل‌های config.py یا .env.example یافت نشد. نمی‌توان سازگاری را بررسی کرد.", Colors.YELLOW)
        return

    config_default = None
    env_value = None
    
    # بررسی مقدار پیش‌فرض در config.py
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config_content = f.read()
            # جستجوی TWITTER_SERVICE_TYPE با regex
            match = re.search(r'TWITTER_SERVICE_TYPE:\s*str\s*=\s*["\']([^"\']+)["\']', config_content)
            if match:
                config_default = match.group(1)
    except Exception as e:
        print_color(f"  ! خطا در خواندن config.py: {e}", Colors.RED)
    
    # بررسی مقدار در .env.example
    try:
        with open(env_path, 'r', encoding='utf-8') as f:
            env_content = f.read()
            # جستجوی TWITTER_SERVICE_TYPE با regex
            match = re.search(r'TWITTER_SERVICE_TYPE\s*=\s*([^\s#]+)', env_content)
            if match:
                env_value = match.group(1)
    except Exception as e:
        print_color(f"  ! خطا در خواندن .env.example: {e}", Colors.RED)
    
    # مقایسه مقادیر
    if config_default and env_value and config_default != env_value:
        print_color(f"  ! ناسازگاری در تنظیمات: TWITTER_SERVICE_TYPE در config.py: '{config_default}' و در .env.example: '{env_value}'", Colors.YELLOW)
        
        # پیشنهاد اصلاح
        print_color("  → پیشنهاد می‌شود هر دو مقدار یکسان باشند.", Colors.BLUE)
    elif config_default and env_value:
        print_color(f"  ✓ تنظیمات TWITTER_SERVICE_TYPE در هر دو فایل سازگار هستند: '{config_default}'", Colors.GREEN)
    else:
        print_color("  ! نمی‌توان مقادیر TWITTER_SERVICE_TYPE را در فایل‌ها پیدا کرد.", Colors.YELLOW)

def add_aiohttp_to_requirements(dst_base):
    """اضافه کردن aiohttp به requirements.txt اگر وجود ندارد"""
    req_path = os.path.join(dst_base, 'backend/requirements.txt')
    if os.path.exists(req_path):
        try:
            with open(req_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # بررسی وجود aiohttp
            if 'aiohttp' not in content:
                with open(req_path, 'a', encoding='utf-8') as f:
                    f.write("\n# برای TwitterAPI.io اضافه شده است\naiohttp==3.8.4\n")
                print_color("  ✓ aiohttp به requirements.txt اضافه شد", Colors.GREEN)
            else:
                print_color("  ✓ aiohttp از قبل در requirements.txt وجود دارد", Colors.GREEN)
        except Exception as e:
            print_color(f"  ! خطا در بررسی/بروزرسانی requirements.txt: {e}", Colors.RED)

def main():
    """تابع اصلی برنامه"""
    if len(sys.argv) < 2:
        print_color("خطا: لطفاً مسیر دایرکتوری منبع را مشخص کنید.", Colors.RED)
        print("استفاده: python setup_project.py [مسیر دایرکتوری منبع] [مسیر پروژه جدید (اختیاری)]")
        sys.exit(1)
    
    src_dir = sys.argv[1]
    
    # مسیر پروژه جدید (اختیاری)
    if len(sys.argv) > 2:
        dst_base = sys.argv[2]
    else:
        dst_base = "twitter-monitoring-system"
    
    # بررسی وجود دایرکتوری منبع
    if not os.path.isdir(src_dir):
        print_color(f"خطا: دایرکتوری {src_dir} پیدا نشد.", Colors.RED)
        sys.exit(1)
    
    # ایجاد دایرکتوری پروژه اصلی
    os.makedirs(dst_base, exist_ok=True)
    print_color(f"پروژه جدید در {dst_base} ایجاد خواهد شد.", Colors.BLUE)
    
    # ایجاد ساختار پوشه‌ای
    create_directories(dst_base)
    
    # نگاشت فایل‌ها
    file_mapping = map_files()
    
    # کپی فایل‌ها
    files_copied, files_not_found = copy_files(src_dir, dst_base, file_mapping)
    
    # ایجاد فایل‌های مفقودشده TwitterAPI.io
    create_missing_files(dst_base)
    
    # بررسی سازگاری تنظیمات
    check_config_consistency(dst_base)
    
    # اضافه کردن aiohttp به requirements
    add_aiohttp_to_requirements(dst_base)
    
    # نمایش خلاصه
    print_color("\nخلاصه عملیات:", Colors.BLUE)
    print(f"  • دایرکتوری‌ها ایجاد شدند: {Colors.GREEN}✓{Colors.ENDC}")
    print(f"  • فایل‌های منتقل شده: {Colors.GREEN}{files_copied}{Colors.ENDC}")
    print(f"  • فایل‌های پیدا نشده: {Colors.YELLOW}{files_not_found}{Colors.ENDC}")
    print(f"  • بررسی و تکمیل فایل‌های TwitterAPI.io: {Colors.GREEN}✓{Colors.ENDC}")
    
    print_color("\nساختار پروژه با موفقیت ایجاد شد.", Colors.GREEN)
    print("برای مرحله بعدی، باید محتوای کامل فایل‌های TwitterAPI.io را درون فایل‌های ایجاد شده کپی کنید.")
    
if __name__ == "__main__":
    main()

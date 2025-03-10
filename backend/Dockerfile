FROM python:3.9-slim as build

WORKDIR /app

# تنظیم محیط
ENV PYTHONFAULTHANDLER=1 \
    PYTHONHASHSEED=random \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_DEFAULT_TIMEOUT=100

# نصب ابزارهای مورد نیاز
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# نصب وابستگی‌ها
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# اجرا در محیط تولید
FROM python:3.9-slim as production

WORKDIR /app

# متغیرهای محیطی
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# نصب ابزارهای مورد نیاز
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# کپی وابستگی‌ها از مرحله قبل
COPY --from=build /usr/local/lib/python3.9/site-packages/ /usr/local/lib/python3.9/site-packages/
COPY --from=build /usr/local/bin/ /usr/local/bin/

# ایجاد کاربر غیر root
RUN addgroup --system app && \
    adduser --system --group app && \
    mkdir -p /app/logs && \
    chown -R app:app /app

# کپی کدهای برنامه
COPY --chown=app:app . .

# تعیین کاربر غیر root
USER app

# بنادر مورد نیاز
EXPOSE 8000

# نقطه ورود
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

# اجرا در محیط توسعه
FROM production as development

USER root

# نصب ابزارهای توسعه
RUN pip install --no-cache-dir pytest pytest-asyncio pytest-cov black isort flake8 mypy

# تعیین کاربر غیر root
USER app

# نقطه ورود در حالت توسعه همراه با قابلیت‌های دیباگ
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
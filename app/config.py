"""
系统配置模块
"""

import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv(override=True)

# Redis 配置
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
REDIS_DB = int(os.getenv("REDIS_DB", 0))
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", None)
REDIS_URL = f"redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}"

# Celery 配置
CELERY_BROKER_URL = REDIS_URL
CELERY_RESULT_BACKEND = REDIS_URL

# API 反馈配置
API_FEEDBACK_URL = os.getenv("API_FEEDBACK_URL", "http://localhost:6000/gateway")
API_KEY = os.getenv("API_KEY", "")

# 运行时配置
print(f"ENV var: {os.getenv('MAX_RUNTIME_SECONDS')}")
MAX_RUNTIME_SECONDS = int(os.getenv("MAX_RUNTIME_SECONDS", 21600))
SHUTDOWN_GRACE_PERIOD_SECONDS = int(os.getenv("SHUTDOWN_GRACE_PERIOD_SECONDS", 1800))
RETRY_DELAY_SECONDS = int(os.getenv("RETRY_DELAY_SECONDS", 300))

# 任务配置
TASK_RETRY_COUNT = 1  # 任务失败后重试次数

# 日志配置
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S" # 日志日期格式

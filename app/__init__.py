"""
GitHub Actions 任务队列系统
"""

from app.core.runner import Runner
from app.core.tasks import init_celery_app

__version__ = "0.1.0" 
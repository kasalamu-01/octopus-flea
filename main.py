#!/usr/bin/env python3
"""
GitHub Actions 任务队列系统主入口
"""

import os
import sys
import time
from typing import Dict, Any, List, Optional

from app import __version__
from app.config import LOG_LEVEL
from app.core.logger import configure_remote_logging, feedback_handler
from app.core.runner import Runner
from app.core.tasks import init_celery_app, celery_app
from app.tasks import video_processing  # 导入视频处理任务
from app.utils.helpers import setup_logger

logger = setup_logger(__name__, LOG_LEVEL)

def shutdown_celery():
    """
    关闭Celery
    """
    logger.info("Shutting down Celery")
    # 这里不需要真正关闭Celery Worker，因为它会随着主进程退出而终止

def main():
    """
    主函数
    """
    # 打印版本信息
    logger.info(f"GitHub Actions 任务队列系统 v{__version__}")
    
    # 配置远程日志
    configure_remote_logging()
    
    # 初始化Celery
    init_celery_app()
    logger.info("Celery initialized")
    
    # 导入所有任务模块，确保任务被注册到Celery
    logger.info(f"Available video tasks: {', '.join(dir(video_processing))}")
    
    # 创建运行管理器
    runner = Runner()
    
    # 注册关闭回调
    runner.register_shutdown_callback(shutdown_celery)
    
    # 启动运行管理器
    return runner.start()

if __name__ == "__main__":
    # 启动应用
    exit_code = main()
    sys.exit(exit_code) 
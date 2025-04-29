"""
任务队列模块
"""

import functools
import traceback
from typing import Dict, Any, Callable, Optional, Type, TypeVar, cast

from celery import Celery, Task
from celery.signals import task_failure, task_success, task_retry
from celery.utils.log import get_task_logger

from app.config import (
    CELERY_BROKER_URL, 
    CELERY_RESULT_BACKEND, 
    TASK_RETRY_COUNT, 
    RETRY_DELAY_SECONDS
)
from app.core.logger import feedback_handler
from app.utils.helpers import run_command

# 创建Celery应用
celery_app = Celery(
    'tasks',
    broker=CELERY_BROKER_URL,
    backend=CELERY_RESULT_BACKEND
)

# 配置Celery
celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600,  # 1小时
    worker_prefetch_multiplier=1,  # 一次只取一个任务
)

logger = get_task_logger(__name__)

# 任务基类
class BaseTask(Task):
    """
    任务基类，提供通用功能和错误处理
    """
    
    abstract = True  # Celery不会将其注册为任务
    
    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """
        任务失败时的回调
        """
        logger.error(f"Task {task_id} failed: {exc}")
        
        # 获取详细的错误信息
        error_info = {
            "exception": str(exc),
            "traceback": einfo.traceback if einfo else None
        }
        
        # 发送失败反馈
        feedback_handler.send_task_result(
            task_id=task_id,
            status="failure",
            error=str(exc),
            result={"args": args, "kwargs": kwargs, "error_info": error_info}
        )
        
    def on_success(self, retval, task_id, args, kwargs):
        """
        任务成功时的回调
        """
        logger.info(f"Task {task_id} succeeded")
        
        # 发送成功反馈
        feedback_handler.send_task_result(
            task_id=task_id,
            status="success",
            result={"args": args, "kwargs": kwargs, "result": retval}
        )
        
    def on_retry(self, exc, task_id, args, kwargs, einfo):
        """
        任务重试时的回调
        """
        logger.warning(f"Task {task_id} retrying: {exc}")
        
        # 获取详细的错误信息
        error_info = {
            "exception": str(exc),
            "traceback": einfo.traceback if einfo else None
        }
        
        # 发送重试反馈
        feedback_handler.send_task_result(
            task_id=task_id,
            status="retry",
            error=str(exc),
            result={"args": args, "kwargs": kwargs, "error_info": error_info}
        )

# 视频处理任务
@celery_app.task(
    bind=True, 
    base=BaseTask, 
    max_retries=TASK_RETRY_COUNT, 
    default_retry_delay=RETRY_DELAY_SECONDS
)
def process_video(self, command: str, timeout: Optional[int] = None) -> Dict[str, Any]:
    """
    处理视频的任务
    
    Args:
        command: 要执行的视频处理命令
        timeout: 命令执行超时时间（秒）
        
    Returns:
        包含执行结果的字典
    """
    task_id = self.request.id
    logger.info(f"Processing video with task ID: {task_id}")
    logger.info(f"Command: {command}")
    
    try:
        # 执行命令
        result = run_command(command, timeout)
        
        # 检查命令是否成功执行
        if not result["success"]:
            error_msg = f"Command failed with return code {result['returncode']}: {result['error']}"
            logger.error(error_msg)
            
            # 尝试重试任务
            if self.request.retries < self.max_retries:
                logger.info(f"Retrying task {task_id}...")
                raise self.retry(exc=Exception(error_msg))
            else:
                logger.error(f"Max retries reached for task {task_id}")
                raise Exception(error_msg)
                
        return result
        
    except Exception as exc:
        logger.exception(f"Error processing video: {exc}")
        
        # 尝试重试任务
        if self.request.retries < self.max_retries:
            logger.info(f"Retrying task {task_id}...")
            raise self.retry(exc=exc)
        
        # 重新抛出异常
        raise

# 类型变量，用于任务工厂函数
T = TypeVar('T')

def task_factory(task_type: str) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """
    任务工厂函数，用于创建不同类型的任务
    
    Args:
        task_type: 任务类型
        
    Returns:
        装饰器函数
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @celery_app.task(
            bind=True, 
            base=BaseTask, 
            max_retries=TASK_RETRY_COUNT, 
            default_retry_delay=RETRY_DELAY_SECONDS,
            name=f"{task_type}.{func.__name__}"
        )
        @functools.wraps(func)
        def wrapper(self, *args, **kwargs):
            task_id = self.request.id
            logger.info(f"Running {task_type} task with ID: {task_id}")
            
            try:
                result = func(*args, **kwargs)
                return result
                
            except Exception as exc:
                logger.exception(f"Error in {task_type} task: {exc}")
                
                # 尝试重试任务
                if self.request.retries < self.max_retries:
                    logger.info(f"Retrying task {task_id}...")
                    raise self.retry(exc=exc)
                
                # 重新抛出异常
                raise
                
        return cast(Callable[..., T], wrapper)
    
    return decorator

# 注册所有任务到Celery
def init_celery_app():
    """
    初始化Celery应用
    """
    # 注册信号处理器
    register_celery_signals()
    
    return celery_app

# 注册Celery信号处理器
def register_celery_signals():
    """
    注册Celery信号处理器
    """
    @task_success.connect
    def task_success_handler(sender=None, **kwargs):
        """
        任务成功信号处理器
        """
        if sender and hasattr(sender, 'on_success'):
            # 让任务类自己处理成功回调
            pass
        else:
            # 对于没有on_success方法的任务，记录日志
            logger.info(f"Task {kwargs.get('sender', 'unknown')} succeeded")
    
    @task_failure.connect
    def task_failure_handler(sender=None, exception=None, **kwargs):
        """
        任务失败信号处理器
        """
        if sender and hasattr(sender, 'on_failure'):
            # 让任务类自己处理失败回调
            pass
        else:
            # 对于没有on_failure方法的任务，记录日志
            logger.error(f"Task {kwargs.get('sender', 'unknown')} failed: {exception}")
    
    @task_retry.connect
    def task_retry_handler(sender=None, reason=None, **kwargs):
        """
        任务重试信号处理器
        """
        if sender and hasattr(sender, 'on_retry'):
            # 让任务类自己处理重试回调
            pass
        else:
            # 对于没有on_retry方法的任务，记录日志
            logger.warning(f"Task {kwargs.get('sender', 'unknown')} retrying: {reason}")
    
    logger.info("Celery signal handlers registered") 
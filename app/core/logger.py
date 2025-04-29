"""
日志与反馈模块
"""

import json
import logging
import time
import uuid
import requests
from typing import Any, Dict, Optional

from app.config import API_FEEDBACK_URL, API_KEY, LOG_LEVEL
from app.utils.helpers import setup_logger

logger = setup_logger(__name__, LOG_LEVEL)

class FeedbackHandler:
    """
    反馈处理类
    """

    def __init__(self, api_url: str = API_FEEDBACK_URL, api_key: str = API_KEY):
        """
        初始化反馈处理类

        Args:
            api_url: API接口URL
            api_key: API密钥
        """
        self.api_url = api_url
        self.api_key = api_key
        self.logger = setup_logger(f"{__name__}.FeedbackHandler", LOG_LEVEL)

    def send_feedback(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        发送反馈数据到API接口

        Args:
            data: 反馈数据字典

        Returns:
            API响应数据
        """
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }

        payload = {
            "id": str(uuid.uuid4()),
            "timestamp": int(time.time()),
            "data": data
        }

        response = {"success": False, "error": None, "response": None}

        try:
            # 发送请求
            self.logger.debug(f"Sending feedback to {self.api_url} with payload: {json.dumps(payload)}")
            r = requests.post(
                self.api_url,
                headers=headers,
                data=json.dumps(payload),
                timeout=10
            )

            # 处理响应
            response["success"] = r.status_code == 200
            response["response"] = r.json() if response["success"] else None

            if not response["success"]:
                response["error"] = f"HTTP Error: {r.status_code} - {r.text}"
                self.logger.error(f"Feedback failed: {response['error']}")
            else:
                self.logger.info(f"Feedback sent successfully")

        except requests.RequestException as e:
            response["error"] = f"Request Error: {str(e)}"
            self.logger.error(f"Failed to send feedback: {response['error']}")
        except json.JSONDecodeError:
            response["error"] = "Invalid JSON response from server"
            self.logger.error(f"Failed to decode JSON response: {response['error']}")
        except Exception as e:
            response["error"] = f"Unexpected Error: {str(e)}"
            self.logger.error(f"An unexpected error occurred: {response['error']}")

        return response
    
    def send_task_result(
        self,
        task_id: str,
        status: str,
        result: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None) -> Dict[str, Any]:
        """
        发送任务结果到API接口
        Args:
            task_id: 任务ID
            status: 任务状态
            result: 任务结果数据
            error: 错误信息
        Returns:
            API响应数据
        """
        data = {
            "type": "task_result",
            "task_id": task_id,
            "status": status,
            "result": result or {},
            "error": error
        }

        return self.send_feedback(data)
    
    def send_system_log(
        self,
        level: str,
        message: str,
        context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        发送系统日志到API接口
        Args:
            level: 日志级别
            message: 日志消息
            context: 上下文数据
        Returns:
            API响应数据
        """
        data = {
            "type": "system_log",
            "level": level,
            "message": message,
            "context": context or {}
        }
        return self.send_feedback(data)
    
    def send_heartbeat(
        self,
        status: str,
        metrics: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        发送心跳数据到API接口
        Args:
            status: 心跳状态
            metrics: 监控指标数据
        Returns:
            API响应数据
        """
        data = {
            "type": "heartbeat",
            "status": status,
            "metrics": metrics or {}
        }
        return self.send_feedback(data)
    
# 创建全局反馈处理器实例
feedback_handler = FeedbackHandler()

# 定义日志处理器子类，将日志发送到远程服务器
class RemoteLoggingHandler(logging.Handler):
    """
    远程日志处理器
    """

    def __init__(self, feedback_handler: FeedbackHandler = feedback_handler):
        """
        初始化远程日志处理器
        Args:
            feedback_handler: 反馈处理器实例
        """        
        super().__init__()
        self.feedback_handler = feedback_handler

    def emit(self, record: logging.LogRecord):
        """
        发送日志记录到远程服务器
        Args:
            record: 日志记录对象
        """
        # 获取日志级别名称
        level = record.levelname.lower()

        # 构建上下文信息
        context = {
            "logger_name": record.name,
            "pathname": record.pathname,
            "lineno": record.lineno,
            "funcName": record.funcName
        }

        # 发送日志
        try:
            self.feedback_handler.send_system_log(
                level=level,
                message=record.getMessage(),
                context=context
            )
        except Exception:
            # 避免日志处理器异常导致的无限递归
            self.handleError(record)

def configure_remote_logging():
    """
    配置远程日志记录
    """
    root_logger = logging.getLogger()

    # 添加远程日志处理器
    handler = RemoteLoggingHandler()

    # 设置日志级别 - 仅发送警告及以上级别的日志到远程服务器
    handler.setLevel(logging.WARNING)

    # 添加处理器到根日志记录器
    root_logger.addHandler(handler)

    logger.info("Remote logging configured successfully.")
        
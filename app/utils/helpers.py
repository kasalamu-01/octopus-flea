"""
辅助函数模块
"""

import json
import logging
import subprocess
import time
from typing import Dict, Any, Union, List

def run_command(command: Union[str, List[str]], timeout: int = None) -> Dict[str, Any]:
    """
    执行命令行指令并返回结果

    Args:
        command: 要执行的命令行指令，可以是字符串或字符串列表
        timeout: 超时时间，单位为秒

    Returns:
        包含执行结果的字典，格式为:
        {
            "success": bool,  # 是否成功
            "returncode": int,  # 返回码
            "output": str,  # 标准输出
            "error": str,  # 标准错误
            "duration": float,  # 执行时间（秒）
        }
    """

    start_time = time.time()
    result = {
        "success": False,
        "returncode": -1,
        "output": "",
        "error": "",
        "duration": 0,
    }

    try:
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=isinstance(command, str),
            text=True
        )

        stdout, stderr = process.communicate(timeout=timeout)

        result["returncode"] = process.returncode
        result["output"] = stdout.strip()
        result["error"] = stderr.strip()
        result["success"] = process.returncode == 0

    except subprocess.TimeoutExpired:
        result["error"] = f"Command '{' '.join(command)}' timed out after {timeout} seconds."
    except Exception as e:
        result["error"] = str(e)
    finally:
        result["duration"] = time.time() - start_time

    return result

def format_json_response(data: Dict[str, Any]) -> str:
    """
    将字典格式化为 JSON 字符串

    Args:
        data: 要格式化的数据

    Returns:
        格式化后的 JSON 字符串
    """
    try:
        return json.dumps(data, ensure_ascii=False, indent=2)
    except (TypeError, ValueError) as e:
        logging.error(f"JSON formatting error: {e}")
        return json.dumps({"error": "Invalid data format"}, ensure_ascii=False)
    
def setup_logger(name: str, level: str = "INFO") -> logging.Logger:
    """
    设置并返回日志记录器

    Args:
        name: 日志记录器名称
        level: 日志级别

    Returns:
        配置好的日志记录器
    """
    from app.config import LOG_FORMAT, LOG_DATE_FORMAT

    logger = logging.getLogger(name)

    # 设置日志级别
    level_map = {
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "WARNING": logging.WARNING,
        "ERROR": logging.ERROR,
        "CRITICAL": logging.CRITICAL,
    }
    logger.setLevel(level_map.get(level.upper(), logging.INFO))

    # 添加控制台处理器
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter(LOG_FORMAT, datefmt=LOG_DATE_FORMAT)
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    return logger
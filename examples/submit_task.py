#!/usr/bin/env python3
"""
任务提交示例脚本
"""

import os
import sys
import json
import time
from typing import Dict, Any

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.core.tasks import celery_app
from app.tasks.video_processing import convert_video_format, compress_video, extract_frames
from app.utils.helpers import format_json_response

def submit_convert_task(input_file: str, output_format: str = "mp4") -> Dict[str, Any]:
    """
    提交视频格式转换任务
    
    Args:
        input_file: 输入文件路径
        output_format: 输出格式
        
    Returns:
        任务信息
    """
    # 提交任务
    task = convert_video_format.delay(input_file, output_format)
    
    # 返回任务信息
    return {
        "task_id": task.id,
        "task_name": "convert_video_format",
        "status": task.status,
        "args": {
            "input_file": input_file,
            "output_format": output_format
        }
    }

def submit_compress_task(
    input_file: str, 
    quality: str = "medium",
    resolution: str = None
) -> Dict[str, Any]:
    """
    提交视频压缩任务
    
    Args:
        input_file: 输入文件路径
        quality: 压缩质量
        resolution: 分辨率
        
    Returns:
        任务信息
    """
    # 提交任务
    task = compress_video.delay(
        input_file=input_file,
        quality=quality,
        resolution=resolution
    )
    
    # 返回任务信息
    return {
        "task_id": task.id,
        "task_name": "compress_video",
        "status": task.status,
        "args": {
            "input_file": input_file,
            "quality": quality,
            "resolution": resolution
        }
    }

def submit_extract_frames_task(
    input_file: str,
    output_dir: str,
    frame_rate: float = 1.0
) -> Dict[str, Any]:
    """
    提交视频帧提取任务
    
    Args:
        input_file: 输入文件路径
        output_dir: 输出目录
        frame_rate: 每秒提取的帧数
        
    Returns:
        任务信息
    """
    # 提交任务
    task = extract_frames.delay(
        input_file=input_file,
        output_dir=output_dir,
        frame_rate=frame_rate
    )
    
    # 返回任务信息
    return {
        "task_id": task.id,
        "task_name": "extract_frames",
        "status": task.status,
        "args": {
            "input_file": input_file,
            "output_dir": output_dir,
            "frame_rate": frame_rate
        }
    }

def monitor_task(task_id: str, timeout: int = 60) -> Dict[str, Any]:
    """
    监控任务执行状态
    
    Args:
        task_id: 任务ID
        timeout: 超时时间（秒）
        
    Returns:
        任务结果
    """
    # 获取任务对象
    task = celery_app.AsyncResult(task_id)
    
    # 等待任务完成
    start_time = time.time()
    while not task.ready():
        # 检查是否超时
        if time.time() - start_time > timeout:
            return {
                "task_id": task_id,
                "status": "TIMEOUT",
                "result": None
            }
        
        # 打印当前状态
        print(f"Task {task_id} status: {task.status}")
        
        # 等待一段时间
        time.sleep(2)
    
    # 获取任务结果
    result = task.get() if task.successful() else None
    
    # 返回任务信息
    return {
        "task_id": task_id,
        "status": task.status,
        "result": result
    }

if __name__ == "__main__":
    # 示例视频文件路径
    input_file = "/path/to/your/video.mp4"
    
    # 确保使用正确的视频文件路径
    if not os.path.exists(input_file):
        print(f"Error: Video file '{input_file}' not found.")
        print("Please update the input_file path in this script.")
        sys.exit(1)
    
    # 提交转换格式任务
    print("提交视频格式转换任务...")
    convert_task = submit_convert_task(input_file, "avi")
    print(format_json_response(convert_task))
    
    # 提交压缩任务
    print("\n提交视频压缩任务...")
    compress_task = submit_compress_task(input_file, quality="high", resolution="720p")
    print(format_json_response(compress_task))
    
    # 提交帧提取任务
    print("\n提交视频帧提取任务...")
    frames_dir = os.path.join(os.path.dirname(input_file), "frames")
    extract_task = submit_extract_frames_task(input_file, frames_dir, frame_rate=1.0)
    print(format_json_response(extract_task))
    
    # 监控任务执行状态
    print("\n监控任务执行状态...")
    result = monitor_task(convert_task["task_id"])
    print(format_json_response(result)) 
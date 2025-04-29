"""
视频处理任务模块

此模块提供视频处理相关的任务定义
"""

import os
import time
from typing import Dict, Any, Optional, List

from app.core.tasks import celery_app, task_factory
from app.utils.helpers import run_command, setup_logger

logger = setup_logger(__name__)

# 使用任务工厂创建视频处理任务
video_task = task_factory("video")

@video_task
def convert_video_format(
    input_file: str, 
    output_format: str = "mp4", 
    output_file: Optional[str] = None,
    options: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    转换视频格式
    
    Args:
        input_file: 输入文件路径
        output_format: 输出格式
        output_file: 输出文件路径（可选）
        options: 其他FFmpeg选项
        
    Returns:
        命令执行结果
    """
    # 如果没有指定输出文件，则根据输入文件和输出格式生成输出文件路径
    if not output_file:
        base_name = os.path.splitext(os.path.basename(input_file))[0]
        output_file = f"{base_name}.{output_format}"
    
    # 构建FFmpeg命令
    cmd = ["ffmpeg", "-i", input_file]
    
    # 添加其他选项
    if options:
        for key, value in options.items():
            if value is True:
                cmd.append(f"-{key}")
            elif value is not False and value is not None:
                cmd.append(f"-{key}")
                cmd.append(str(value))
    
    # 添加输出文件
    cmd.append(output_file)
    
    # 执行命令
    result = run_command(cmd)
    
    # 添加任务特定信息到结果
    result["task_info"] = {
        "input_file": input_file,
        "output_format": output_format,
        "output_file": output_file
    }
    
    return result

@video_task
def compress_video(
    input_file: str, 
    output_file: Optional[str] = None,
    quality: str = "medium",
    resolution: Optional[str] = None,
    bitrate: Optional[str] = None
) -> Dict[str, Any]:
    """
    压缩视频
    
    Args:
        input_file: 输入文件路径
        output_file: 输出文件路径（可选）
        quality: 压缩质量，可选值：low、medium、high
        resolution: 分辨率，例如：720p、1080p
        bitrate: 比特率，例如：1M、2M
        
    Returns:
        命令执行结果
    """
    # 如果没有指定输出文件，则根据输入文件生成输出文件路径
    if not output_file:
        base_name = os.path.splitext(os.path.basename(input_file))[0]
        output_file = f"{base_name}_compressed.mp4"
    
    # 根据质量设置参数
    quality_presets = {
        "low": {"crf": "28", "preset": "ultrafast"},
        "medium": {"crf": "23", "preset": "medium"},
        "high": {"crf": "18", "preset": "slow"}
    }
    
    preset = quality_presets.get(quality.lower(), quality_presets["medium"])
    
    # 构建FFmpeg命令
    cmd = ["ffmpeg", "-i", input_file, "-c:v", "libx264"]
    
    # 添加质量参数
    cmd.extend(["-crf", preset["crf"], "-preset", preset["preset"]])
    
    # 添加分辨率参数
    if resolution:
        if resolution == "720p":
            cmd.extend(["-vf", "scale=-1:720"])
        elif resolution == "1080p":
            cmd.extend(["-vf", "scale=-1:1080"])
        else:
            cmd.extend(["-vf", f"scale={resolution}"])
    
    # 添加比特率参数
    if bitrate:
        cmd.extend(["-b:v", bitrate])
    
    # 添加音频参数
    cmd.extend(["-c:a", "aac", "-b:a", "128k"])
    
    # 添加输出文件
    cmd.append(output_file)
    
    # 执行命令
    result = run_command(cmd)
    
    # 添加任务特定信息到结果
    result["task_info"] = {
        "input_file": input_file,
        "output_file": output_file,
        "quality": quality,
        "resolution": resolution,
        "bitrate": bitrate
    }
    
    return result

@video_task
def extract_frames(
    input_file: str,
    output_dir: str,
    frame_rate: Optional[float] = None,
    start_time: Optional[str] = None,
    duration: Optional[str] = None,
    format: str = "jpg"
) -> Dict[str, Any]:
    """
    从视频中提取帧
    
    Args:
        input_file: 输入文件路径
        output_dir: 输出目录
        frame_rate: 每秒提取的帧数
        start_time: 开始时间，格式：HH:MM:SS
        duration: 持续时间，格式：HH:MM:SS
        format: 输出图像格式
        
    Returns:
        命令执行结果
    """
    # 确保输出目录存在
    os.makedirs(output_dir, exist_ok=True)
    
    # 构建输出路径模式
    output_pattern = os.path.join(output_dir, f"frame_%04d.{format}")
    
    # 构建FFmpeg命令
    cmd = ["ffmpeg", "-i", input_file]
    
    # 添加开始时间参数
    if start_time:
        cmd.extend(["-ss", start_time])
    
    # 添加持续时间参数
    if duration:
        cmd.extend(["-t", duration])
    
    # 添加帧率参数
    if frame_rate:
        cmd.extend(["-r", str(frame_rate)])
    
    # 添加输出参数
    cmd.extend(["-q:v", "2"])  # 高质量
    
    # 添加输出路径
    cmd.append(output_pattern)
    
    # 执行命令
    result = run_command(cmd)
    
    # 添加任务特定信息到结果
    result["task_info"] = {
        "input_file": input_file,
        "output_dir": output_dir,
        "frame_rate": frame_rate,
        "start_time": start_time,
        "duration": duration,
        "format": format
    }
    
    return result 
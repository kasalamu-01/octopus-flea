"""
运行管理模块
"""

import atexit
import datetime
import signal
import sys
import threading
import time
from typing import Optional, List, Dict, Any, Callable

from app.config import (
    MAX_RUNTIME_SECONDS, 
    SHUTDOWN_GRACE_PERIOD_SECONDS,
    LOG_LEVEL
)
from app.core.logger import feedback_handler
from app.utils.helpers import setup_logger

logger = setup_logger(__name__, LOG_LEVEL)

class Runner:
    """
    运行管理器，负责监控和管理整个系统的运行
    """
    
    def __init__(
        self,
        max_runtime_seconds: int = MAX_RUNTIME_SECONDS,
        shutdown_grace_period_seconds: int = SHUTDOWN_GRACE_PERIOD_SECONDS
    ):
        """
        初始化运行管理器
        
        Args:
            max_runtime_seconds: 最大运行时间（秒）
            shutdown_grace_period_seconds: 关闭前的宽限期（秒）
        """
        self.max_runtime_seconds = max_runtime_seconds
        self.shutdown_grace_period_seconds = shutdown_grace_period_seconds
        self.shutdown_threshold = max_runtime_seconds - shutdown_grace_period_seconds
        
        self.start_time = time.time()
        self.is_running = False
        self.shutdown_timer: Optional[threading.Timer] = None
        self.monitor_thread: Optional[threading.Thread] = None
        self.should_exit = threading.Event()
        self.exit_code = 0
        
        # 存储注册的回调函数，回调函数无参数无返回值
        self.shutdown_callbacks: List[Callable[[], None]] = []
        
        # 注册信号处理器
        self._register_signal_handlers()
        
        # 注册退出处理器
        atexit.register(self._cleanup)
        
        logger.info(f"Runner initialized with max runtime: {max_runtime_seconds}s, "
                   f"shutdown grace period: {shutdown_grace_period_seconds}s")
    
    def start(self) -> int:
        """
        启动运行管理器
        
        Returns:
            退出码
        """
        if self.is_running:
            logger.warning("Runner is already running")
            return 0
            
        self.is_running = True
        self.start_time = time.time()
        
        logger.info("Runner started")
        feedback_handler.send_heartbeat(status="started", metrics=self._get_metrics())
        
        try:
            # 开始监控线程
            self._start_monitor_thread()
            
            # 设置关闭定时器
            self._schedule_shutdown()
            
            # 等待退出信号
            self._wait_for_exit()
            
        except KeyboardInterrupt:
            logger.info("Keyboard interrupt received")
            self.shutdown(0)
        except Exception as e:
            logger.exception(f"Error in runner: {e}")
            self.shutdown(1)
        finally:
            return self.exit_code
    
    def shutdown(self, exit_code: int = 0):
        """
        关闭运行管理器
        
        Args:
            exit_code: 退出码
        """
        if not self.is_running:
            return
            
        logger.info(f"Shutting down with exit code {exit_code}")
        
        self.exit_code = exit_code
        self.is_running = False
        self.should_exit.set()
        
        # 执行所有注册的关闭回调
        self._run_shutdown_callbacks()
        
        # 发送关闭心跳
        feedback_handler.send_heartbeat(status="shutdown", metrics=self._get_metrics())
        
        # 终止监控线程
        if self.monitor_thread and self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=2.0)
            
        # 取消关闭定时器
        if self.shutdown_timer and self.shutdown_timer.is_alive():
            self.shutdown_timer.cancel()
            
        logger.info("Runner shutdown complete")
    
    def register_shutdown_callback(self, callback: Callable[[], None]):
        """
        注册关闭回调函数
        
        Args:
            callback: 回调函数
        """
        self.shutdown_callbacks.append(callback)
        logger.debug(f"Registered shutdown callback: {callback.__name__}")
    
    def _start_monitor_thread(self):
        """
        启动监控线程
        """
        self.monitor_thread = threading.Thread(
            target=self._monitor_loop,
            name="RunnerMonitor",
            daemon=True
        )
        self.monitor_thread.start()
        logger.debug("Monitor thread started")
    
    def _schedule_shutdown(self):
        """
        设置关闭定时器
        """
        # 计算距离关闭的时间
        seconds_until_shutdown = self.shutdown_threshold
        
        logger.info(f"Scheduling shutdown in {seconds_until_shutdown} seconds")
        
        # 创建定时器
        self.shutdown_timer = threading.Timer(
            seconds_until_shutdown,
            self._scheduled_shutdown
        )
        # 以守护线程方式运行
        # 这样主线程退出时，定时器线程也会自动退出
        # 这对于避免僵尸线程非常重要
        self.shutdown_timer.daemon = True
        self.shutdown_timer.start()
    
    def _scheduled_shutdown(self):
        """
        定时关闭回调
        """
        uptime = time.time() - self.start_time
        logger.warning(f"Scheduled shutdown triggered after {uptime:.2f} seconds")
        feedback_handler.send_system_log(
            "warning",
            f"Maximum runtime reached ({self.shutdown_threshold} seconds), initiating graceful shutdown",
            {"uptime": uptime}
        )
        self.shutdown(0)
    
    def _monitor_loop(self):
        """
        监控循环
        负责定期发送心跳信息和检查运行状态
        """
        logger.debug("Monitor loop started")
        
        heartbeat_interval = 60  # 1分钟发送一次心跳
        last_heartbeat = 0
        
        while self.is_running and not self.should_exit.is_set():
            current_time = time.time()
            uptime = current_time - self.start_time
            
            # 发送周期性心跳
            if current_time - last_heartbeat >= heartbeat_interval:
                # 获取系统指标
                metrics = self._get_metrics()
                # 向服务器发送心跳信息
                feedback_handler.send_heartbeat(status="running", metrics=metrics)
                # 更新上次心跳时间
                last_heartbeat = current_time
                logger.debug(f"Sent heartbeat at uptime {uptime:.2f}s")
            
            # 检查是否接近最大运行时间
            if uptime >= self.max_runtime_seconds:
                logger.warning(f"Maximum runtime reached: {uptime:.2f}s > {self.max_runtime_seconds}s")
                self.shutdown(0)
                break
                
            # 休眠一段时间
            time.sleep(5)
    
    def _wait_for_exit(self):
        """
        等待退出信号
        """
        while self.is_running and not self.should_exit.is_set():
            time.sleep(1)
    
    def _run_shutdown_callbacks(self):
        """
        运行所有注册的关闭回调
        """
        logger.info(f"Running {len(self.shutdown_callbacks)} shutdown callbacks")
        
        for callback in self.shutdown_callbacks:
            try:
                logger.debug(f"Running shutdown callback: {callback.__name__}")
                callback()
            except Exception as e:
                logger.error(f"Error in shutdown callback {callback.__name__}: {e}")
    
    def _register_signal_handlers(self):
        """
        注册信号处理器
        """
        # 注册SIGTERM处理器
        def handle_sigterm(signum, frame):
            logger.info("SIGTERM received")
            self.shutdown(0)
            
        # 注册SIGINT处理器
        def handle_sigint(signum, frame):
            logger.info("SIGINT received")
            self.shutdown(0)
        
        # 注册信号处理器
        signal.signal(signal.SIGTERM, handle_sigterm)
        signal.signal(signal.SIGINT, handle_sigint)
        
        logger.debug("Signal handlers registered")
    
    def _cleanup(self):
        """
        清理资源
        """
        if self.is_running:
            logger.warning("Runner is still running during cleanup, forcing shutdown")
            self.shutdown(0)
    
    def _get_metrics(self) -> Dict[str, Any]:
        """
        获取系统指标
        
        Returns:
            指标字典
        """
        current_time = time.time()
        uptime = current_time - self.start_time
        
        return {
            "uptime": uptime,
            "uptime_formatted": str(datetime.timedelta(seconds=int(uptime))),
            "start_time": self.start_time,
            "start_time_formatted": datetime.datetime.fromtimestamp(self.start_time).isoformat(),
            "current_time": current_time,
            "current_time_formatted": datetime.datetime.fromtimestamp(current_time).isoformat(),
            "max_runtime": self.max_runtime_seconds,
            "shutdown_threshold": self.shutdown_threshold,
            "remaining_time": max(0, self.max_runtime_seconds - uptime),
            "memory_usage_mb": self._get_memory_usage()
        }
    
    def _get_memory_usage(self) -> float:
        """
        获取内存使用量
        
        Returns:
            内存使用量（MB）
        """
        try:
            import psutil
            process = psutil.Process()
            memory_info = process.memory_info()
            return memory_info.rss / (1024 * 1024)  # 转换为MB
        except ImportError:
            return -1  # psutil不可用 
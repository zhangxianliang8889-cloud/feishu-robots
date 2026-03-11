"""SpiderX 重试机制模块"""

from dataclasses import dataclass
from typing import Optional, Callable, List, Type, Tuple
from enum import Enum
import time
import random
import logging
from functools import wraps

logger = logging.getLogger(__name__)


class RetryStrategy(Enum):
    """重试策略"""
    FIXED = "fixed"
    LINEAR = "linear"
    EXPONENTIAL = "exponential"
    RANDOM = "random"


@dataclass
class RetryPolicy:
    """
    重试策略配置
    
    Attributes:
        max_retries: 最大重试次数
        strategy: 重试策略
        base_delay: 基础延迟(秒)
        max_delay: 最大延迟(秒)
        exponential_base: 指数基数
        jitter: 是否添加随机抖动
        retry_exceptions: 触发重试的异常类型
        retry_status_codes: 触发重试的状态码
    """
    max_retries: int = 3
    strategy: RetryStrategy = RetryStrategy.EXPONENTIAL
    base_delay: float = 1.0
    max_delay: float = 60.0
    exponential_base: float = 2.0
    jitter: bool = True
    retry_exceptions: Tuple[Type[Exception], ...] = (Exception,)
    retry_status_codes: Tuple[int, ...] = (429, 500, 502, 503, 504)
    
    def get_delay(self, attempt: int) -> float:
        """计算重试延迟"""
        if self.strategy == RetryStrategy.FIXED:
            delay = self.base_delay
        
        elif self.strategy == RetryStrategy.LINEAR:
            delay = self.base_delay * attempt
        
        elif self.strategy == RetryStrategy.EXPONENTIAL:
            delay = self.base_delay * (self.exponential_base ** (attempt - 1))
        
        elif self.strategy == RetryStrategy.RANDOM:
            delay = random.uniform(self.base_delay, self.base_delay * attempt)
        
        else:
            delay = self.base_delay
        
        delay = min(delay, self.max_delay)
        
        if self.jitter:
            delay = delay * random.uniform(0.5, 1.5)
        
        return delay
    
    def should_retry(self, exception: Optional[Exception] = None, 
                     status_code: Optional[int] = None) -> bool:
        """判断是否应该重试"""
        if exception is not None:
            return isinstance(exception, self.retry_exceptions)
        
        if status_code is not None:
            return status_code in self.retry_status_codes
        
        return False


class RetryContext:
    """重试上下文"""
    
    def __init__(self, policy: RetryPolicy):
        self.policy = policy
        self.attempt = 0
        self.last_exception: Optional[Exception] = None
        self.total_delay = 0.0
    
    def next_attempt(self) -> bool:
        """是否可以继续重试"""
        return self.attempt < self.policy.max_retries
    
    def get_delay(self) -> float:
        """获取下次重试延迟"""
        return self.policy.get_delay(self.attempt)
    
    def record_attempt(self, exception: Exception = None):
        """记录重试"""
        self.attempt += 1
        self.last_exception = exception


def retry(policy: Optional[RetryPolicy] = None,
          max_retries: int = 3,
          strategy: RetryStrategy = RetryStrategy.EXPONENTIAL,
          base_delay: float = 1.0,
          exceptions: Tuple[Type[Exception], ...] = (Exception,)):
    """
    重试装饰器
    
    Args:
        policy: 重试策略对象
        max_retries: 最大重试次数
        strategy: 重试策略
        base_delay: 基础延迟
        exceptions: 触发重试的异常
    
    Example:
        @retry(max_retries=3, strategy=RetryStrategy.EXPONENTIAL)
        def fetch_url(url):
            return requests.get(url)
    """
    if policy is None:
        policy = RetryPolicy(
            max_retries=max_retries,
            strategy=strategy,
            base_delay=base_delay,
            retry_exceptions=exceptions
        )
    
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            context = RetryContext(policy)
            
            while True:
                try:
                    return func(*args, **kwargs)
                
                except policy.retry_exceptions as e:
                    context.record_attempt(e)
                    
                    if not context.next_attempt():
                        logger.error(f"重试耗尽: {func.__name__}, 尝试次数: {context.attempt}")
                        raise
                    
                    delay = context.get_delay()
                    context.total_delay += delay
                    
                    logger.warning(
                        f"重试 {func.__name__}: "
                        f"第{context.attempt}次, "
                        f"等待{delay:.2f}秒, "
                        f"错误: {e}"
                    )
                    
                    time.sleep(delay)
        
        return wrapper
    return decorator


def async_retry(policy: Optional[RetryPolicy] = None,
                max_retries: int = 3,
                strategy: RetryStrategy = RetryStrategy.EXPONENTIAL,
                base_delay: float = 1.0,
                exceptions: Tuple[Type[Exception], ...] = (Exception,)):
    """
    异步重试装饰器
    
    Example:
        @async_retry(max_retries=3)
        async def fetch_url(url):
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    return await response.text()
    """
    if policy is None:
        policy = RetryPolicy(
            max_retries=max_retries,
            strategy=strategy,
            base_delay=base_delay,
            retry_exceptions=exceptions
        )
    
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            context = RetryContext(policy)
            
            while True:
                try:
                    return await func(*args, **kwargs)
                
                except policy.retry_exceptions as e:
                    context.record_attempt(e)
                    
                    if not context.next_attempt():
                        logger.error(f"重试耗尽: {func.__name__}, 尝试次数: {context.attempt}")
                        raise
                    
                    delay = context.get_delay()
                    context.total_delay += delay
                    
                    logger.warning(
                        f"重试 {func.__name__}: "
                        f"第{context.attempt}次, "
                        f"等待{delay:.2f}秒, "
                        f"错误: {e}"
                    )
                    
                    import asyncio
                    await asyncio.sleep(delay)
        
        return wrapper
    return decorator


class RetryManager:
    """重试管理器"""
    
    def __init__(self, policy: RetryPolicy):
        self.policy = policy
        self._stats = {
            "total_retries": 0,
            "successful_retries": 0,
            "failed_retries": 0,
            "total_delay": 0.0
        }
    
    def execute(self, func: Callable, *args, **kwargs):
        """执行带重试的函数"""
        context = RetryContext(self.policy)
        
        while True:
            try:
                result = func(*args, **kwargs)
                
                if context.attempt > 0:
                    self._stats["successful_retries"] += 1
                
                return result
            
            except self.policy.retry_exceptions as e:
                context.record_attempt(e)
                self._stats["total_retries"] += 1
                
                if not context.next_attempt():
                    self._stats["failed_retries"] += 1
                    raise
                
                delay = context.get_delay()
                self._stats["total_delay"] += delay
                
                logger.warning(f"重试中: 第{context.attempt}次, 等待{delay:.2f}秒")
                time.sleep(delay)
    
    def get_stats(self) -> dict:
        """获取统计信息"""
        return self._stats.copy()

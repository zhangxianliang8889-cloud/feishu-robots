#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
增强API客户端 - 行业最优重试机制
指数退避 + 限流 + 熔断 + 超时控制
"""

import time
import random
import requests
from typing import Dict, Any, Optional, Callable
from datetime import datetime
from enum import Enum

class CircuitState(Enum):
    """熔断器状态"""
    CLOSED = "关闭"
    OPEN = "打开"
    HALF_OPEN = "半开"


class CircuitBreaker:
    """熔断器"""
    
    def __init__(
        self, 
        failure_threshold: int = 5, 
        recovery_timeout: int = 60,
        half_open_requests: int = 3
    ):
        """
        初始化熔断器
        
        Args:
            failure_threshold: 失败阈值
            recovery_timeout: 恢复超时（秒）
            half_open_requests: 半开状态请求数
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_requests = half_open_requests
        
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.last_failure_time = None
        self.half_open_success = 0
    
    def is_allowed(self) -> bool:
        """
        检查是否允许请求
        
        Returns:
            bool: 是否允许
        """
        if self.state == CircuitState.CLOSED:
            return True
        
        if self.state == CircuitState.OPEN:
            if self.last_failure_time:
                elapsed = (datetime.now() - self.last_failure_time).total_seconds()
                if elapsed >= self.recovery_timeout:
                    self.state = CircuitState.HALF_OPEN
                    self.half_open_success = 0
                    return True
            return False
        
        if self.state == CircuitState.HALF_OPEN:
            return self.half_open_success < self.half_open_requests
        
        return False
    
    def record_success(self):
        """记录成功"""
        if self.state == CircuitState.HALF_OPEN:
            self.half_open_success += 1
            if self.half_open_success >= self.half_open_requests:
                self.state = CircuitState.CLOSED
                self.failure_count = 0
        elif self.state == CircuitState.CLOSED:
            self.failure_count = 0
    
    def record_failure(self):
        """记录失败"""
        self.failure_count += 1
        self.last_failure_time = datetime.now()
        
        if self.state == CircuitState.HALF_OPEN:
            self.state = CircuitState.OPEN
        elif self.state == CircuitState.CLOSED:
            if self.failure_count >= self.failure_threshold:
                self.state = CircuitState.OPEN
    
    def get_state(self) -> Dict[str, Any]:
        """获取状态"""
        return {
            "state": self.state.value,
            "failure_count": self.failure_count,
            "last_failure": self.last_failure_time.strftime('%Y-%m-%d %H:%M:%S') if self.last_failure_time else None
        }


class EnhancedRetryClient:
    """增强重试客户端"""
    
    def __init__(
        self,
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0,
        jitter: bool = True,
        timeout: int = 30,
        rate_limit: int = 10,
        rate_window: int = 60
    ):
        """
        初始化增强重试客户端
        
        Args:
            max_retries: 最大重试次数
            base_delay: 基础延迟（秒）
            max_delay: 最大延迟（秒）
            exponential_base: 指数基数
            jitter: 是否添加抖动
            timeout: 请求超时（秒）
            rate_limit: 限流请求数
            rate_window: 限流时间窗口（秒）
        """
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.jitter = jitter
        self.timeout = timeout
        
        self.circuit_breaker = CircuitBreaker()
        self.rate_limit = rate_limit
        self.rate_window = rate_window
        self.request_times = []
        
        self.stats = {
            "total_requests": 0,
            "success_requests": 0,
            "failed_requests": 0,
            "retried_requests": 0,
            "circuit_open_rejects": 0,
            "rate_limit_waits": 0
        }
    
    def _calculate_delay(self, attempt: int) -> float:
        """
        计算延迟时间（指数退避 + 抖动）
        
        Args:
            attempt: 尝试次数
        
        Returns:
            float: 延迟时间
        """
        delay = self.base_delay * (self.exponential_base ** attempt)
        delay = min(delay, self.max_delay)
        
        if self.jitter:
            delay = delay * (0.5 + random.random())
        
        return delay
    
    def _check_rate_limit(self) -> bool:
        """
        检查限流
        
        Returns:
            bool: 是否允许请求
        """
        now = time.time()
        self.request_times = [t for t in self.request_times if now - t < self.rate_window]
        
        if len(self.request_times) >= self.rate_limit:
            return False
        
        self.request_times.append(now)
        return True
    
    def _wait_for_rate_limit(self):
        """等待限流"""
        while not self._check_rate_limit():
            self.stats["rate_limit_waits"] += 1
            time.sleep(1)
    
    def request(
        self,
        method: str,
        url: str,
        **kwargs
    ) -> Optional[Dict[str, Any]]:
        """
        发送请求（带重试、限流、熔断）
        
        Args:
            method: 请求方法
            url: 请求URL
            **kwargs: 请求参数
        
        Returns:
            Optional[Dict]: 响应数据
        """
        self.stats["total_requests"] += 1
        
        if not self.circuit_breaker.is_allowed():
            self.stats["circuit_open_rejects"] += 1
            print(f"⚠️ 熔断器打开，拒绝请求: {url}")
            return None
        
        self._wait_for_rate_limit()
        
        kwargs.setdefault("timeout", self.timeout)
        kwargs.setdefault("proxies", {})
        
        last_error = None
        
        for attempt in range(self.max_retries + 1):
            try:
                if attempt > 0:
                    self.stats["retried_requests"] += 1
                    delay = self._calculate_delay(attempt - 1)
                    print(f"🔄 第 {attempt} 次重试，等待 {delay:.1f} 秒...")
                    time.sleep(delay)
                
                response = requests.request(method, url, **kwargs)
                
                if response.status_code == 200:
                    self.circuit_breaker.record_success()
                    self.stats["success_requests"] += 1
                    return response.json()
                
                if response.status_code == 429:
                    retry_after = int(response.headers.get("Retry-After", 60))
                    print(f"⚠️ 触发限流，等待 {retry_after} 秒...")
                    time.sleep(retry_after)
                    continue
                
                if response.status_code >= 500:
                    last_error = f"服务器错误: {response.status_code}"
                    continue
                
                last_error = f"请求失败: {response.status_code}"
                break
                
            except requests.exceptions.Timeout:
                last_error = "请求超时"
                continue
            except requests.exceptions.ConnectionError:
                last_error = "连接错误"
                continue
            except Exception as e:
                last_error = f"未知错误: {str(e)}"
                continue
        
        self.circuit_breaker.record_failure()
        self.stats["failed_requests"] += 1
        print(f"❌ 请求失败: {last_error}")
        return None
    
    def get(self, url: str, **kwargs) -> Optional[Dict[str, Any]]:
        """GET请求"""
        return self.request("GET", url, **kwargs)
    
    def post(self, url: str, **kwargs) -> Optional[Dict[str, Any]]:
        """POST请求"""
        return self.request("POST", url, **kwargs)
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            **self.stats,
            "success_rate": (
                self.stats["success_requests"] / self.stats["total_requests"] * 100
                if self.stats["total_requests"] > 0 else 0
            ),
            "circuit_breaker": self.circuit_breaker.get_state()
        }


class FeishuAPIClient:
    """飞书API客户端（增强版）"""
    
    def __init__(self, app_id: str, app_secret: str, retry_client: EnhancedRetryClient = None):
        """
        初始化飞书API客户端
        
        Args:
            app_id: 应用ID
            app_secret: 应用密钥
            retry_client: 重试客户端
        """
        self.app_id = app_id
        self.app_secret = app_secret
        self.retry_client = retry_client or EnhancedRetryClient()
        self.token = None
        self.token_expire = 0
    
    def _get_token(self) -> bool:
        """
        获取访问令牌
        
        Returns:
            bool: 是否成功
        """
        if self.token and time.time() < self.token_expire - 300:
            return True
        
        url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
        data = {
            "app_id": self.app_id,
            "app_secret": self.app_secret
        }
        
        result = self.retry_client.post(url, json=data)
        
        if result and result.get("code") == 0:
            self.token = result.get("tenant_access_token")
            self.token_expire = time.time() + result.get("expire", 7200)
            return True
        
        return False
    
    def _get_headers(self) -> Dict[str, str]:
        """获取请求头"""
        return {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }
    
    def get_messages(
        self, 
        chat_id: str, 
        start_time: int = None, 
        end_time: int = None,
        page_size: int = 50
    ) -> Optional[Dict[str, Any]]:
        """
        获取群消息
        
        Args:
            chat_id: 群ID
            start_time: 开始时间戳
            end_time: 结束时间戳
            page_size: 每页大小
        
        Returns:
            Optional[Dict]: 消息数据
        """
        if not self._get_token():
            return None
        
        url = "https://open.feishu.cn/open-apis/im/v1/messages"
        params = {
            "receive_id_type": "chat_id",
            "page_size": page_size
        }
        
        if start_time:
            params["start_time"] = start_time
        if end_time:
            params["end_time"] = end_time
        
        result = self.retry_client.get(url, headers=self._get_headers(), params=params)
        return result
    
    def send_message(
        self, 
        chat_id: str, 
        content: str, 
        msg_type: str = "text"
    ) -> Optional[Dict[str, Any]]:
        """
        发送消息
        
        Args:
            chat_id: 群ID
            content: 消息内容
            msg_type: 消息类型
        
        Returns:
            Optional[Dict]: 发送结果
        """
        if not self._get_token():
            return None
        
        url = "https://open.feishu.cn/open-apis/im/v1/messages"
        data = {
            "receive_id": chat_id,
            "msg_type": msg_type,
            "content": json.dumps({"text": content}) if msg_type == "text" else content
        }
        
        result = self.retry_client.post(
            url, 
            headers=self._get_headers(), 
            json=data
        )
        return result
    
    def get_group_members(self, chat_id: str) -> Optional[Dict[str, Any]]:
        """
        获取群成员列表
        
        Args:
            chat_id: 群ID
        
        Returns:
            Optional[Dict]: 成员数据
        """
        if not self._get_token():
            return None
        
        url = f"https://open.feishu.cn/open-apis/im/v1/chats/{chat_id}/members"
        result = self.retry_client.get(url, headers=self._get_headers())
        return result


import json


if __name__ == "__main__":
    print("🧪 测试增强API客户端")
    print("=" * 60)
    
    print("\n1. 熔断器测试")
    cb = CircuitBreaker(failure_threshold=3, recovery_timeout=5)
    print(f"   初始状态: {cb.get_state()}")
    
    for i in range(5):
        cb.record_failure()
        print(f"   记录失败 {i+1}: {cb.get_state()}")
    
    print(f"   是否允许请求: {cb.is_allowed()}")
    
    print("\n2. 重试客户端测试")
    client = EnhancedRetryClient(max_retries=3, base_delay=0.5)
    
    print(f"   尝试请求不存在的URL...")
    result = client.get("https://httpbin.org/status/500")
    print(f"   结果: {result}")
    
    stats = client.get_stats()
    print(f"   统计: 总请求={stats['total_requests']}, 成功={stats['success_requests']}, 失败={stats['failed_requests']}")
    
    print("\n3. 限流测试")
    limiter_client = EnhancedRetryClient(rate_limit=3, rate_window=5)
    for i in range(5):
        allowed = limiter_client._check_rate_limit()
        print(f"   请求 {i+1}: {'✅ 允许' if allowed else '❌ 限流'}")
    
    print("\n✅ 测试完成")

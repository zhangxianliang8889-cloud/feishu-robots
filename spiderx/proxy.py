"""SpiderX 代理池模块"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, List, Dict, Callable
from enum import Enum
import random
import time
import logging
from collections import defaultdict

logger = logging.getLogger(__name__)


class ProxyStatus(Enum):
    """代理状态"""
    VALID = "valid"
    INVALID = "invalid"
    TESTING = "testing"


@dataclass
class ProxyInfo:
    """代理信息"""
    url: str
    protocol: str = "http"
    username: Optional[str] = None
    password: Optional[str] = None
    status: ProxyStatus = ProxyStatus.VALID
    success_count: int = 0
    fail_count: int = 0
    avg_response_time: float = 0.0
    last_used: float = 0.0
    
    @property
    def success_rate(self) -> float:
        total = self.success_count + self.fail_count
        return self.success_count / total if total > 0 else 0.5
    
    @property
    def proxy_url(self) -> str:
        if self.username and self.password:
            return f"{self.protocol}://{self.username}:{self.password}@{self.url}"
        return f"{self.protocol}://{self.url}"


class ProxyStrategy(ABC):
    """代理选择策略基类"""
    
    @abstractmethod
    def select(self, proxies: List[ProxyInfo], url: str) -> Optional[ProxyInfo]:
        """选择代理"""
        pass


class RoundRobinStrategy(ProxyStrategy):
    """轮询策略"""
    
    def __init__(self):
        self._index = 0
    
    def select(self, proxies: List[ProxyInfo], url: str) -> Optional[ProxyInfo]:
        if not proxies:
            return None
        
        valid_proxies = [p for p in proxies if p.status == ProxyStatus.VALID]
        if not valid_proxies:
            return None
        
        proxy = valid_proxies[self._index % len(valid_proxies)]
        self._index += 1
        return proxy


class RandomStrategy(ProxyStrategy):
    """随机策略"""
    
    def select(self, proxies: List[ProxyInfo], url: str) -> Optional[ProxyInfo]:
        valid_proxies = [p for p in proxies if p.status == ProxyStatus.VALID]
        if not valid_proxies:
            return None
        return random.choice(valid_proxies)


class WeightedStrategy(ProxyStrategy):
    """加权策略 - 根据成功率选择"""
    
    def select(self, proxies: List[ProxyInfo], url: str) -> Optional[ProxyInfo]:
        valid_proxies = [p for p in proxies if p.status == ProxyStatus.VALID]
        if not valid_proxies:
            return None
        
        weights = [p.success_rate + 0.1 for p in valid_proxies]
        return random.choices(valid_proxies, weights=weights)[0]


class DomainRoutingStrategy(ProxyStrategy):
    """域名路由策略 - 不同域名使用不同代理"""
    
    def __init__(self):
        self._domain_proxy: Dict[str, ProxyInfo] = {}
    
    def select(self, proxies: List[ProxyInfo], url: str) -> Optional[ProxyInfo]:
        from urllib.parse import urlparse
        domain = urlparse(url).netloc
        
        if domain in self._domain_proxy:
            proxy = self._domain_proxy[domain]
            if proxy.status == ProxyStatus.VALID:
                return proxy
        
        valid_proxies = [p for p in proxies if p.status == ProxyStatus.VALID]
        if not valid_proxies:
            return None
        
        proxy = random.choice(valid_proxies)
        self._domain_proxy[domain] = proxy
        return proxy


class ProxyPool:
    """
    代理池管理器
    
    功能:
    - 动态添加/移除代理
    - 代理健康检查
    - 多种选择策略
    - 失败自动降级
    """
    
    STRATEGIES = {
        "round_robin": RoundRobinStrategy,
        "random": RandomStrategy,
        "weighted": WeightedStrategy,
        "domain_routing": DomainRoutingStrategy,
    }
    
    def __init__(self,
                 strategy: str = "weighted",
                 check_interval: int = 300,
                 max_fail_count: int = 3,
                 min_success_rate: float = 0.3):
        """
        初始化代理池
        
        Args:
            strategy: 选择策略
            check_interval: 健康检查间隔(秒)
            max_fail_count: 最大失败次数
            min_success_rate: 最低成功率
        """
        self._proxies: List[ProxyInfo] = []
        self._strategy = self.STRATEGIES.get(strategy, WeightedStrategy)()
        self._check_interval = check_interval
        self._max_fail_count = max_fail_count
        self._min_success_rate = min_success_rate
        self._last_check = 0.0
    
    def add_proxy(self, 
                  url: str,
                  protocol: str = "http",
                  username: Optional[str] = None,
                  password: Optional[str] = None) -> None:
        """添加代理"""
        proxy = ProxyInfo(
            url=url,
            protocol=protocol,
            username=username,
            password=password
        )
        self._proxies.append(proxy)
        logger.info(f"添加代理: {url}")
    
    def add_proxies(self, proxy_urls: List[str]) -> None:
        """批量添加代理"""
        for url in proxy_urls:
            self.add_proxy(url)
    
    def remove_proxy(self, url: str) -> None:
        """移除代理"""
        self._proxies = [p for p in self._proxies if p.url != url]
        logger.info(f"移除代理: {url}")
    
    def get_proxy(self, url: str = "") -> Optional[ProxyInfo]:
        """获取代理"""
        return self._strategy.select(self._proxies, url)
    
    def report_success(self, proxy_url: str, response_time: float) -> None:
        """报告成功"""
        for proxy in self._proxies:
            if proxy.url == proxy_url:
                proxy.success_count += 1
                proxy.avg_response_time = (
                    (proxy.avg_response_time * (proxy.success_count - 1) + response_time)
                    / proxy.success_count
                )
                proxy.last_used = time.time()
                break
    
    def report_failure(self, proxy_url: str) -> None:
        """报告失败"""
        for proxy in self._proxies:
            if proxy.url == proxy_url:
                proxy.fail_count += 1
                proxy.last_used = time.time()
                
                if proxy.fail_count >= self._max_fail_count:
                    proxy.status = ProxyStatus.INVALID
                    logger.warning(f"代理失效: {proxy_url}")
                break
    
    def get_valid_proxies(self) -> List[ProxyInfo]:
        """获取有效代理列表"""
        return [p for p in self._proxies if p.status == ProxyStatus.VALID]
    
    def get_stats(self) -> Dict:
        """获取统计信息"""
        valid = len([p for p in self._proxies if p.status == ProxyStatus.VALID])
        invalid = len([p for p in self._proxies if p.status == ProxyStatus.INVALID])
        
        return {
            "total": len(self._proxies),
            "valid": valid,
            "invalid": invalid,
            "proxies": [
                {
                    "url": p.url,
                    "status": p.status.value,
                    "success_rate": f"{p.success_rate:.2%}",
                    "avg_time": f"{p.avg_response_time:.2f}s"
                }
                for p in self._proxies
            ]
        }
    
    def clear(self) -> None:
        """清空代理池"""
        self._proxies.clear()
    
    def set_strategy(self, strategy: str) -> None:
        """设置选择策略"""
        if strategy in self.STRATEGIES:
            self._strategy = self.STRATEGIES[strategy]()
            logger.info(f"切换代理策略: {strategy}")
    
    @classmethod
    def from_file(cls, filepath: str, strategy: str = "weighted") -> "ProxyPool":
        """从文件加载代理"""
        pool = cls(strategy=strategy)
        with open(filepath, "r") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    pool.add_proxy(line)
        return pool
    
    @classmethod
    def from_api(cls, api_url: str, strategy: str = "weighted") -> "ProxyPool":
        """从API加载代理"""
        import requests
        
        pool = cls(strategy=strategy)
        response = requests.get(api_url, timeout=10)
        
        if response.status_code == 200:
            proxies = response.text.strip().split("\n")
            for proxy in proxies:
                proxy = proxy.strip()
                if proxy:
                    pool.add_proxy(proxy)
        
        return pool

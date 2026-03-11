"""SpiderX URL池模块 - 去重与分布式支持"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, Set, List, Dict, Any
from enum import Enum
import hashlib
import time
import logging
import threading
from urllib.parse import urlparse, urljoin, urlunparse, parse_qs, urlencode

logger = logging.getLogger(__name__)


class UrlStatus(Enum):
    """URL状态"""
    PENDING = "pending"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"


@dataclass
class UrlInfo:
    """URL信息"""
    url: str
    depth: int = 0
    status: UrlStatus = UrlStatus.PENDING
    retry_count: int = 0
    parent_url: Optional[str] = None
    extra: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.extra is None:
            self.extra = {}


class UrlPool(ABC):
    """URL池基类"""
    
    @abstractmethod
    def add(self, url_info: UrlInfo) -> bool:
        """添加URL"""
        pass
    
    @abstractmethod
    def get(self) -> Optional[UrlInfo]:
        """获取URL"""
        pass
    
    @abstractmethod
    def done(self, url: str, success: bool = True) -> None:
        """标记URL完成"""
        pass
    
    @abstractmethod
    def is_visited(self, url: str) -> bool:
        """检查是否已访问"""
        pass
    
    @abstractmethod
    def size(self) -> int:
        """获取待处理数量"""
        pass
    
    @abstractmethod
    def clear(self) -> None:
        """清空URL池"""
        pass


class LocalUrlPool(UrlPool):
    """
    本地URL池 - 单机版
    
    功能:
    - 内存去重
    - URL规范化
    - 深度控制
    - 线程安全
    """
    
    def __init__(self, 
                 normalize: bool = True,
                 max_size: int = 1000000,
                 dedup_params: Optional[Set[str]] = None):
        """
        初始化URL池
        
        Args:
            normalize: 是否规范化URL
            max_size: 最大容量
            dedup_params: 用于去重的参数名集合
        """
        self._normalize = normalize
        self._max_size = max_size
        self._dedup_params = dedup_params or set()
        
        self._pending: List[UrlInfo] = []
        self._visited: Set[str] = set()
        self._running: Dict[str, UrlInfo] = {}
        
        self._lock = threading.RLock()
    
    def _normalize_url(self, url: str) -> str:
        """规范化URL"""
        if not self._normalize:
            return url
        
        try:
            parsed = urlparse(url)
            
            scheme = parsed.scheme.lower()
            netloc = parsed.netloc.lower()
            
            if netloc.startswith("www."):
                netloc = netloc[4:]
            
            path = parsed.path
            if not path:
                path = "/"
            if path != "/" and path.endswith("/"):
                path = path[:-1]
            
            if self._dedup_params and parsed.query:
                params = parse_qs(parsed.query)
                filtered_params = {k: v for k, v in params.items() if k in self._dedup_params}
                query = urlencode(filtered_params, doseq=True) if filtered_params else ""
            else:
                query = parsed.query
            
            normalized = urlunparse((
                scheme,
                netloc,
                path,
                parsed.params,
                query,
                ""
            ))
            
            return normalized
            
        except Exception:
            return url
    
    def _get_fingerprint(self, url: str) -> str:
        """获取URL指纹"""
        normalized = self._normalize_url(url)
        return hashlib.md5(normalized.encode()).hexdigest()
    
    def add(self, url_info: UrlInfo) -> bool:
        """添加URL"""
        with self._lock:
            if len(self._visited) >= self._max_size:
                logger.warning("URL池已满")
                return False
            
            fingerprint = self._get_fingerprint(url_info.url)
            
            if fingerprint in self._visited:
                return False
            
            if fingerprint in {self._get_fingerprint(u.url) for u in self._running.values()}:
                return False
            
            url_info.url = self._normalize_url(url_info.url)
            self._pending.append(url_info)
            self._visited.add(fingerprint)
            
            return True
    
    def add_batch(self, urls: List[str], depth: int = 0, parent_url: str = None) -> int:
        """批量添加URL"""
        count = 0
        for url in urls:
            url_info = UrlInfo(url=url, depth=depth, parent_url=parent_url)
            if self.add(url_info):
                count += 1
        return count
    
    def get(self) -> Optional[UrlInfo]:
        """获取URL"""
        with self._lock:
            if not self._pending:
                return None
            
            url_info = self._pending.pop(0)
            url_info.status = UrlStatus.RUNNING
            fingerprint = self._get_fingerprint(url_info.url)
            self._running[fingerprint] = url_info
            
            return url_info
    
    def done(self, url: str, success: bool = True) -> None:
        """标记URL完成"""
        with self._lock:
            fingerprint = self._get_fingerprint(url)
            
            if fingerprint in self._running:
                url_info = self._running.pop(fingerprint)
                url_info.status = UrlStatus.DONE if success else UrlStatus.FAILED
    
    def is_visited(self, url: str) -> bool:
        """检查是否已访问"""
        fingerprint = self._get_fingerprint(url)
        return fingerprint in self._visited
    
    def size(self) -> int:
        """获取待处理数量"""
        return len(self._pending)
    
    def running_count(self) -> int:
        """获取正在处理数量"""
        return len(self._running)
    
    def visited_count(self) -> int:
        """获取已访问数量"""
        return len(self._visited)
    
    def clear(self) -> None:
        """清空URL池"""
        with self._lock:
            self._pending.clear()
            self._visited.clear()
            self._running.clear()


class RedisUrlPool(UrlPool):
    """
    Redis URL池 - 分布式版
    
    功能:
    - 分布式共享
    - 持久化
    - 多爬虫协作
    """
    
    def __init__(self,
                 redis_url: str = "redis://localhost:6379/0",
                 key_prefix: str = "spiderx",
                 normalize: bool = True):
        """
        初始化Redis URL池
        
        Args:
            redis_url: Redis连接URL
            key_prefix: 键前缀
            normalize: 是否规范化URL
        """
        try:
            import redis
            self._redis = redis.from_url(redis_url)
            self._key_prefix = key_prefix
            self._normalize = normalize
            self._local_visited: Set[str] = set()
            
            self._pending_key = f"{key_prefix}:pending"
            self._visited_key = f"{key_prefix}:visited"
            self._running_key = f"{key_prefix}:running"
            
        except ImportError:
            raise ImportError("请安装redis: pip install redis")
    
    def _normalize_url(self, url: str) -> str:
        """规范化URL"""
        if not self._normalize:
            return url
        
        try:
            parsed = urlparse(url)
            normalized = urlunparse((
                parsed.scheme.lower(),
                parsed.netloc.lower().replace("www.", ""),
                parsed.path or "/",
                parsed.params,
                parsed.query,
                ""
            ))
            return normalized
        except Exception:
            return url
    
    def _get_fingerprint(self, url: str) -> str:
        """获取URL指纹"""
        normalized = self._normalize_url(url)
        return hashlib.md5(normalized.encode()).hexdigest()
    
    def add(self, url_info: UrlInfo) -> bool:
        """添加URL"""
        fingerprint = self._get_fingerprint(url_info.url)
        
        if self._redis.sismember(self._visited_key, fingerprint):
            return False
        
        if self._redis.hexists(self._running_key, fingerprint):
            return False
        
        import json
        url_data = json.dumps({
            "url": self._normalize_url(url_info.url),
            "depth": url_info.depth,
            "parent_url": url_info.parent_url,
            "extra": url_info.extra
        })
        
        self._redis.lpush(self._pending_key, url_data)
        self._redis.sadd(self._visited_key, fingerprint)
        
        return True
    
    def get(self) -> Optional[UrlInfo]:
        """获取URL"""
        import json
        
        result = self._redis.rpop(self._pending_key)
        
        if not result:
            return None
        
        url_data = json.loads(result)
        url_info = UrlInfo(
            url=url_data["url"],
            depth=url_data.get("depth", 0),
            parent_url=url_data.get("parent_url"),
            extra=url_data.get("extra", {})
        )
        
        fingerprint = self._get_fingerprint(url_info.url)
        self._redis.hset(self._running_key, fingerprint, time.time())
        
        return url_info
    
    def done(self, url: str, success: bool = True) -> None:
        """标记URL完成"""
        fingerprint = self._get_fingerprint(url)
        self._redis.hdel(self._running_key, fingerprint)
    
    def is_visited(self, url: str) -> bool:
        """检查是否已访问"""
        fingerprint = self._get_fingerprint(url)
        return self._redis.sismember(self._visited_key, fingerprint)
    
    def size(self) -> int:
        """获取待处理数量"""
        return self._redis.llen(self._pending_key)
    
    def clear(self) -> None:
        """清空URL池"""
        self._redis.delete(self._pending_key)
        self._redis.delete(self._visited_key)
        self._redis.delete(self._running_key)


class UrlFilter:
    """URL过滤器"""
    
    def __init__(self,
                 whitelist: Optional[List[str]] = None,
                 blacklist: Optional[List[str]] = None,
                 allowed_domains: Optional[List[str]] = None,
                 allowed_schemes: Optional[List[str]] = None):
        """
        初始化URL过滤器
        
        Args:
            whitelist: 白名单正则列表
            blacklist: 黑名单正则列表
            allowed_domains: 允许的域名列表
            allowed_schemes: 允许的协议列表
        """
        import re
        
        self._whitelist = [re.compile(p) for p in (whitelist or [])]
        self._blacklist = [re.compile(p) for p in (blacklist or [])]
        self._allowed_domains = set(allowed_domains or [])
        self._allowed_schemes = set(allowed_schemes or ["http", "https"])
    
    def is_allowed(self, url: str) -> bool:
        """检查URL是否允许"""
        try:
            parsed = urlparse(url)
            
            if parsed.scheme not in self._allowed_schemes:
                return False
            
            if self._allowed_domains and parsed.netloc not in self._allowed_domains:
                if not any(parsed.netloc.endswith(f".{d}") for d in self._allowed_domains):
                    return False
            
            for pattern in self._blacklist:
                if pattern.search(url):
                    return False
            
            if self._whitelist:
                for pattern in self._whitelist:
                    if pattern.search(url):
                        return True
                return False
            
            return True
            
        except Exception:
            return False
    
    def filter_urls(self, urls: List[str]) -> List[str]:
        """过滤URL列表"""
        return [url for url in urls if self.is_allowed(url)]

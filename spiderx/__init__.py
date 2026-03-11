"""
SpiderX - 高性能Python爬虫框架

特性:
1. 简洁API - 直观易用
2. 轻量级 - 最小依赖
3. 模块化 - 灵活扩展
4. 装饰器驱动 - 数据提取注解
5. 多线程/异步 - 高效并发
6. JS渲染 - Playwright/Selenium
7. 代理池 - 动态代理路由
8. 失败重试 - 自动重试机制
9. 幂等去重 - 防止重复爬取
10. 分布式支持 - Redis共享
"""

__version__ = "1.0.0"
__author__ = "SpiderX Team"

from .engine import Spider, SpiderEngine
from .decorators import css, xpath, regex, json_field, attr
from .config import SpiderConfig
from .loaders import RequestsLoader, PlaywrightLoader, SeleniumLoader
from .proxy import ProxyPool, ProxyStrategy
from .urlpool import LocalUrlPool, RedisUrlPool
from .retry import RetryPolicy
from .async_spider import AsyncSpider

__all__ = [
    "Spider",
    "SpiderEngine", 
    "SpiderConfig",
    "css",
    "xpath", 
    "regex",
    "json_field",
    "attr",
    "RequestsLoader",
    "PlaywrightLoader",
    "SeleniumLoader",
    "ProxyPool",
    "ProxyStrategy",
    "LocalUrlPool",
    "RedisUrlPool",
    "RetryPolicy",
    "AsyncSpider",
]

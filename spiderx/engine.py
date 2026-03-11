"""SpiderX 核心引擎模块"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, Callable, Type, Generator, AsyncGenerator
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
import logging
import threading
from urllib.parse import urljoin, urlparse

from .config import SpiderConfig, LoadMode, RunMode
from .loaders import PageLoader, RequestsLoader, PlaywrightLoader, SeleniumLoader, Response, create_loader
from .decorators import PageVO, DataExtractor, page_vo
from .urlpool import UrlPool, LocalUrlPool, RedisUrlPool, UrlFilter, UrlInfo
from .proxy import ProxyPool
from .retry import RetryPolicy, RetryManager
from .exceptions import SpiderException, DownloadException, ParseException

logger = logging.getLogger(__name__)


@dataclass
class SpiderContext:
    """爬虫上下文"""
    url: str
    response: Optional[Response] = None
    html: str = ""
    depth: int = 0
    extra: Dict[str, Any] = field(default_factory=dict)
    spider: Optional["Spider"] = None
    
    @property
    def soup(self):
        """BeautifulSoup对象"""
        from bs4 import BeautifulSoup
        return BeautifulSoup(self.html, "lxml")
    
    def xpath(self, selector: str):
        """XPath选择"""
        from lxml import etree
        tree = etree.HTML(self.html)
        return tree.xpath(selector)
    
    def css(self, selector: str):
        """CSS选择"""
        return self.soup.select(selector)
    
    def extract_links(self, base_url: str = None) -> List[str]:
        """提取页面所有链接"""
        links = []
        for a in self.soup.find_all("a", href=True):
            href = a["href"]
            full_url = urljoin(base_url or self.url, href)
            links.append(full_url)
        return links


class Spider(ABC):
    """
    爬虫基类
    
    子类需要实现:
    - start_urls: 起始URL列表
    - parse(): 解析方法
    
    Example:
        class MySpider(Spider):
            start_urls = ["https://example.com"]
            
            def parse(self, ctx: SpiderContext):
                for item in ctx.css(".item"):
                    yield {"title": item.text}
    """
    
    name: str = "spider"
    start_urls: List[str] = []
    config: SpiderConfig = SpiderConfig()
    
    allowed_domains: List[str] = []
    url_whitelist: List[str] = []
    url_blacklist: List[str] = []
    
    custom_settings: Dict[str, Any] = {}
    
    def __init__(self, config: SpiderConfig = None):
        if config:
            self.config = config
        
        if self.custom_settings:
            for key, value in self.custom_settings.items():
                if hasattr(self.config, key):
                    setattr(self.config, key, value)
        
        self._loader: Optional[PageLoader] = None
        self._url_pool: Optional[UrlPool] = None
        self._proxy_pool: Optional[ProxyPool] = None
        self._url_filter: Optional[UrlFilter] = None
        self._results: List[Any] = []
        self._running = False
        self._stats = {
            "pages_visited": 0,
            "items_scraped": 0,
            "errors": 0,
            "start_time": None,
            "end_time": None,
        }
    
    @abstractmethod
    def parse(self, ctx: SpiderContext):
        """解析方法 - 子类必须实现"""
        pass
    
    def start_request(self) -> Generator[UrlInfo, None, None]:
        """生成初始请求"""
        for url in self.start_urls:
            yield UrlInfo(url=url, depth=0)
    
    def process_item(self, item: Any) -> Any:
        """处理提取的数据项"""
        return item
    
    def on_start(self):
        """爬虫启动时调用"""
        pass
    
    def on_finish(self):
        """爬虫结束时调用"""
        pass
    
    def on_error(self, url: str, error: Exception):
        """发生错误时调用"""
        logger.error(f"处理URL失败: {url}, 错误: {error}")
    
    def _init_components(self):
        """初始化组件"""
        self._loader = create_loader(self.config)
        
        if self.config.dedup_method == "redis" and self.config.redis_url:
            self._url_pool = RedisUrlPool(self.config.redis_url)
        else:
            self._url_pool = LocalUrlPool()
        
        if self.config.proxy_enabled and self.config.proxy_pool:
            self._proxy_pool = ProxyPool()
            self._proxy_pool.add_proxies(self.config.proxy_pool)
        
        self._url_filter = UrlFilter(
            whitelist=self.url_whitelist or self.config.url_whitelist,
            blacklist=self.url_blacklist or self.config.url_blacklist,
            allowed_domains=self.allowed_domains
        )
    
    def _process_url(self, url_info: UrlInfo) -> Optional[SpiderContext]:
        """处理单个URL"""
        url = url_info.url
        
        if not self._url_filter.is_allowed(url):
            logger.debug(f"URL被过滤: {url}")
            return None
        
        proxy = None
        if self._proxy_pool:
            proxy_info = self._proxy_pool.get_proxy(url)
            if proxy_info:
                proxy = proxy_info.proxy_url
        
        try:
            response = self._loader.load(url, proxy=proxy)
            
            if self._proxy_pool and proxy:
                self._proxy_pool.report_success(proxy, response.elapsed)
            
            ctx = SpiderContext(
                url=url,
                response=response,
                html=response.html,
                depth=url_info.depth,
                extra=url_info.extra,
                spider=self
            )
            
            return ctx
            
        except Exception as e:
            if self._proxy_pool and proxy:
                self._proxy_pool.report_failure(proxy)
            
            self.on_error(url, e)
            raise
    
    def _handle_result(self, result, depth: int):
        """处理解析结果"""
        if result is None:
            return
        
        if isinstance(result, dict):
            processed = self.process_item(result)
            if processed:
                self._results.append(processed)
                self._stats["items_scraped"] += 1
        
        elif isinstance(result, UrlInfo):
            if depth < self.config.max_depth or self.config.max_depth == 0:
                if self._url_filter.is_allowed(result.url):
                    result.depth = depth + 1
                    self._url_pool.add(result)
        
        elif isinstance(result, str):
            if depth < self.config.max_depth or self.config.max_depth == 0:
                if self._url_filter.is_allowed(result):
                    self._url_pool.add(UrlInfo(url=result, depth=depth + 1))
    
    def run(self) -> List[Any]:
        """运行爬虫"""
        self._init_components()
        self._running = True
        self._stats["start_time"] = time.time()
        
        self.on_start()
        
        for url_info in self.start_request():
            self._url_pool.add(url_info)
        
        with ThreadPoolExecutor(max_workers=self.config.concurrent_requests) as executor:
            futures = {}
            
            while self._running and (self._url_pool.size() > 0 or futures):
                while self._url_pool.size() > 0 and len(futures) < self.config.concurrent_requests:
                    url_info = self._url_pool.get()
                    if url_info:
                        future = executor.submit(self._process_url, url_info)
                        futures[future] = url_info
                
                for future in as_completed(futures, timeout=1):
                    url_info = futures.pop(future)
                    
                    try:
                        ctx = future.result()
                        
                        if ctx:
                            self._stats["pages_visited"] += 1
                            
                            for result in self.parse(ctx) or []:
                                self._handle_result(result, ctx.depth)
                            
                            delay = self.config.get_delay()
                            time.sleep(delay)
                    
                    except Exception as e:
                        self._stats["errors"] += 1
                        self.on_error(url_info.url, e)
        
        self._stats["end_time"] = time.time()
        self.on_finish()
        
        if self._loader:
            self._loader.close()
        
        return self._results
    
    def stop(self):
        """停止爬虫"""
        self._running = False
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        stats = self._stats.copy()
        if stats["start_time"] and stats["end_time"]:
            stats["duration"] = stats["end_time"] - stats["start_time"]
        return stats


class SpiderEngine:
    """
    爬虫引擎 - 管理多个爬虫
    
    Example:
        engine = SpiderEngine()
        engine.add_spider(MySpider)
        results = engine.run()
    """
    
    def __init__(self, config: SpiderConfig = None):
        self.config = config or SpiderConfig()
        self._spiders: List[Type[Spider]] = []
        self._results: Dict[str, List[Any]] = {}
    
    def add_spider(self, spider_class: Type[Spider], config: SpiderConfig = None):
        """添加爬虫"""
        self._spiders.append((spider_class, config))
    
    def run(self) -> Dict[str, List[Any]]:
        """运行所有爬虫"""
        for spider_class, config in self._spiders:
            spider = spider_class(config or self.config)
            spider.name = spider_class.name
            self._results[spider.name] = spider.run()
        
        return self._results
    
    def get_results(self, spider_name: str = None) -> List[Any]:
        """获取结果"""
        if spider_name:
            return self._results.get(spider_name, [])
        return self._results


def crawl(urls: List[str], 
          parse_func: Callable[[SpiderContext], Any],
          config: SpiderConfig = None) -> List[Any]:
    """
    快速爬取函数
    
    Args:
        urls: URL列表
        parse_func: 解析函数
        config: 配置
    
    Returns:
        结果列表
    
    Example:
        def parse(ctx):
            return {"title": ctx.css("h1")[0].text}
        
        results = crawl(["https://example.com"], parse)
    """
    class QuickSpider(Spider):
        start_urls = urls
        
        def parse(self, ctx):
            return parse_func(ctx)
    
    spider = QuickSpider(config or SpiderConfig())
    return spider.run()

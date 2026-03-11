"""SpiderX 异步爬虫模块"""

import asyncio
import aiohttp
import logging
from typing import Optional, List, Dict, Any, Callable, AsyncGenerator, Type
from dataclasses import dataclass, field
from urllib.parse import urljoin
import time

from .config import SpiderConfig
from .decorators import PageVO, DataExtractor
from .urlpool import UrlPool, LocalUrlPool, UrlFilter, UrlInfo
from .proxy import ProxyPool
from .exceptions import DownloadException, TimeoutException

logger = logging.getLogger(__name__)


@dataclass
class AsyncResponse:
    """异步响应"""
    url: str
    html: str
    status_code: int
    headers: Dict[str, str]
    elapsed: float


class AsyncSpider:
    """
    异步爬虫基类
    
    使用aiohttp实现高性能异步爬取
    
    Example:
        class MyAsyncSpider(AsyncSpider):
            start_urls = ["https://example.com"]
            
            async def parse(self, ctx):
                yield {"title": ctx.css("h1")[0].text}
        
        spider = MyAsyncSpider()
        results = await spider.run_async()
    """
    
    name: str = "async_spider"
    start_urls: List[str] = []
    config: SpiderConfig = SpiderConfig()
    
    allowed_domains: List[str] = []
    url_whitelist: List[str] = []
    url_blacklist: List[str] = []
    
    def __init__(self, config: SpiderConfig = None):
        self.config = config or SpiderConfig()
        self._session: Optional[aiohttp.ClientSession] = None
        self._url_pool: Optional[UrlPool] = None
        self._proxy_pool: Optional[ProxyPool] = None
        self._url_filter: Optional[UrlFilter] = None
        self._results: List[Any] = []
        self._semaphore: Optional[asyncio.Semaphore] = None
        self._running = False
        self._stats = {
            "pages_visited": 0,
            "items_scraped": 0,
            "errors": 0,
            "start_time": None,
            "end_time": None,
        }
    
    async def parse(self, ctx):
        """解析方法 - 子类实现"""
        pass
    
    async def start_request(self) -> AsyncGenerator[UrlInfo, None]:
        """生成初始请求"""
        for url in self.start_urls:
            yield UrlInfo(url=url, depth=0)
    
    async def process_item(self, item: Any) -> Any:
        """处理数据项"""
        return item
    
    async def on_start(self):
        """启动时调用"""
        pass
    
    async def on_finish(self):
        """结束时调用"""
        pass
    
    async def on_error(self, url: str, error: Exception):
        """错误时调用"""
        logger.error(f"处理URL失败: {url}, 错误: {error}")
    
    async def _init_components(self):
        """初始化组件"""
        connector = aiohttp.TCPConnector(
            limit=self.config.concurrent_requests * 2,
            limit_per_host=self.config.concurrent_requests,
            ttl_dns_cache=300,
        )
        
        timeout = aiohttp.ClientTimeout(
            total=self.config.download_timeout,
            connect=self.config.connect_timeout,
        )
        
        self._session = aiohttp.ClientSession(
            connector=connector,
            timeout=timeout,
            headers=self.config.get_headers(),
        )
        
        self._url_pool = LocalUrlPool()
        
        if self.config.proxy_enabled and self.config.proxy_pool:
            self._proxy_pool = ProxyPool()
            self._proxy_pool.add_proxies(self.config.proxy_pool)
        
        self._url_filter = UrlFilter(
            whitelist=self.url_whitelist or self.config.url_whitelist,
            blacklist=self.url_blacklist or self.config.url_blacklist,
            allowed_domains=self.allowed_domains
        )
        
        self._semaphore = asyncio.Semaphore(self.config.concurrent_requests)
    
    async def _fetch(self, url: str, proxy: str = None) -> AsyncResponse:
        """异步获取页面"""
        start_time = time.time()
        
        proxy_url = None
        if proxy:
            proxy_url = proxy
        
        try:
            async with self._semaphore:
                async with self._session.get(url, proxy=proxy_url, ssl=False) as response:
                    html = await response.text()
                    elapsed = time.time() - start_time
                    
                    return AsyncResponse(
                        url=str(response.url),
                        html=html,
                        status_code=response.status,
                        headers=dict(response.headers),
                        elapsed=elapsed
                    )
        
        except asyncio.TimeoutError:
            raise TimeoutException(f"请求超时: {url}")
        except aiohttp.ClientError as e:
            raise DownloadException(f"下载失败: {url}, 错误: {e}")
    
    async def _process_url(self, url_info: UrlInfo) -> Optional[Dict]:
        """处理单个URL"""
        url = url_info.url
        
        if not self._url_filter.is_allowed(url):
            return None
        
        proxy = None
        if self._proxy_pool:
            proxy_info = self._proxy_pool.get_proxy(url)
            if proxy_info:
                proxy = proxy_info.proxy_url
        
        try:
            response = await self._fetch(url, proxy)
            
            if self._proxy_pool and proxy:
                self._proxy_pool.report_success(proxy, response.elapsed)
            
            return {
                "url": url,
                "html": response.html,
                "depth": url_info.depth,
                "extra": url_info.extra,
            }
        
        except Exception as e:
            if self._proxy_pool and proxy:
                self._proxy_pool.report_failure(proxy)
            
            await self.on_error(url, e)
            raise
    
    async def _handle_result(self, result, depth: int):
        """处理结果"""
        if result is None:
            return
        
        if isinstance(result, dict):
            processed = await self.process_item(result)
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
    
    async def run_async(self) -> List[Any]:
        """异步运行爬虫"""
        await self._init_components()
        self._running = True
        self._stats["start_time"] = time.time()
        
        await self.on_start()
        
        async for url_info in self.start_request():
            self._url_pool.add(url_info)
        
        tasks = set()
        
        while self._running and (self._url_pool.size() > 0 or tasks):
            while self._url_pool.size() > 0 and len(tasks) < self.config.concurrent_requests:
                url_info = self._url_pool.get()
                if url_info:
                    task = asyncio.create_task(self._process_url(url_info))
                    tasks.add(task)
            
            if tasks:
                done, tasks = await asyncio.wait(
                    tasks,
                    timeout=1,
                    return_when=asyncio.FIRST_COMPLETED
                )
                
                for task in done:
                    try:
                        ctx_data = task.result()
                        
                        if ctx_data:
                            self._stats["pages_visited"] += 1
                            
                            from .engine import SpiderContext
                            ctx = SpiderContext(
                                url=ctx_data["url"],
                                html=ctx_data["html"],
                                depth=ctx_data["depth"],
                                extra=ctx_data["extra"],
                            )
                            
                            async for result in self.parse(ctx) or []:
                                await self._handle_result(result, ctx.depth)
                            
                            delay = self.config.get_delay()
                            await asyncio.sleep(delay)
                    
                    except Exception as e:
                        self._stats["errors"] += 1
        
        self._stats["end_time"] = time.time()
        await self.on_finish()
        
        if self._session:
            await self._session.close()
        
        return self._results
    
    def run(self) -> List[Any]:
        """同步入口"""
        return asyncio.run(self.run_async())
    
    def stop(self):
        """停止爬虫"""
        self._running = False
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计"""
        stats = self._stats.copy()
        if stats["start_time"] and stats["end_time"]:
            stats["duration"] = stats["end_time"] - stats["start_time"]
        return stats


async def async_crawl(urls: List[str],
                      parse_func: Callable,
                      config: SpiderConfig = None,
                      concurrent: int = 10) -> List[Any]:
    """
    异步快速爬取
    
    Args:
        urls: URL列表
        parse_func: 解析函数
        config: 配置
        concurrent: 并发数
    
    Returns:
        结果列表
    
    Example:
        async def parse(ctx):
            return {"title": ctx.css("h1")[0].text}
        
        results = await async_crawl(["https://example.com"], parse)
    """
    config = config or SpiderConfig()
    config.concurrent_requests = concurrent
    
    class QuickAsyncSpider(AsyncSpider):
        start_urls = urls
        
        async def parse(self, ctx):
            result = parse_func(ctx)
            if hasattr(result, '__anext__'):
                async for item in result:
                    yield item
            elif hasattr(result, '__iter__'):
                for item in result:
                    yield item
            else:
                yield result
    
    spider = QuickAsyncSpider(config)
    return await spider.run_async()

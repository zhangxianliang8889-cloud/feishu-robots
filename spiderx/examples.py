"""
SpiderX 使用示例

演示框架的核心功能:
1. 基础爬虫
2. 装饰器数据提取
3. JS渲染
4. 代理池
5. 异步爬虫
6. 分布式支持
"""

import sys
sys.path.insert(0, ".")

from spiderx import (
    Spider, SpiderEngine, SpiderConfig,
    css, xpath, regex, json_field,
    RequestsLoader, PlaywrightLoader, SeleniumLoader,
    ProxyPool, ProxyStrategy,
    LocalUrlPool, RedisUrlPool,
    RetryPolicy, AsyncSpider,
)
from spiderx.decorators import page_vo, PageVO, DataExtractor
from spiderx.engine import SpiderContext, crawl
from spiderx.async_spider import async_crawl


# ==================== 示例1: 基础爬虫 ====================

class NewsSpider(Spider):
    """新闻爬虫示例"""
    
    name = "news_spider"
    start_urls = [
        "https://news.ycombinator.com/",
    ]
    
    config = SpiderConfig(
        concurrent_requests=5,
        download_delay=0.5,
        retry_times=3,
    )
    
    allowed_domains = ["news.ycombinator.com"]
    
    def parse(self, ctx: SpiderContext):
        """解析新闻列表"""
        for item in ctx.css(".athing"):
            title_el = item.select_one(".titleline > a")
            if title_el:
                yield {
                    "title": title_el.text,
                    "link": title_el.get("href", ""),
                }


# ==================== 示例2: 装饰器数据提取 ====================

@page_vo
class ArticlePage(PageVO):
    """文章页面数据对象"""
    
    @css("h1")
    def title(self, value):
        return value.strip() if value else ""
    
    @css(".author")
    def author(self, value):
        return value.strip() if value else ""
    
    @css(".content")
    def content(self, value):
        return value.strip() if value else ""
    
    @xpath("//meta[@property='article:published_time']/@content")
    def publish_time(self, value):
        return value or ""
    
    @regex(r"(\d{4}-\d{2}-\d{2})")
    def date(self, value):
        return value or ""


class ArticleSpider(Spider):
    """文章爬虫 - 使用装饰器提取"""
    
    name = "article_spider"
    start_urls = ["https://example.com/articles"]
    
    def parse(self, ctx: SpiderContext):
        extractor = DataExtractor(ctx.html, ctx.url)
        article = extractor.extract(ArticlePage)
        yield article.to_dict()


# ==================== 示例3: JS渲染爬虫 ====================

class JSSpider(Spider):
    """JS渲染爬虫"""
    
    name = "js_spider"
    start_urls = ["https://spa-example.com"]
    
    config = SpiderConfig(
        load_mode="playwright",
        download_timeout=60,
    )
    
    def parse(self, ctx: SpiderContext):
        for item in ctx.css(".dynamic-item"):
            yield {
                "title": item.text,
            }


# ==================== 示例4: 代理池爬虫 ====================

class ProxySpider(Spider):
    """使用代理池的爬虫"""
    
    name = "proxy_spider"
    start_urls = ["https://httpbin.org/ip"]
    
    config = SpiderConfig(
        proxy_enabled=True,
        proxy_pool=[
            "http://proxy1:8080",
            "http://proxy2:8080",
        ],
    )
    
    def parse(self, ctx: SpiderContext):
        yield {"ip": ctx.css("body")[0].text}


# ==================== 示例5: 扩散全站爬虫 ====================

class CrawlSpider(Spider):
    """全站爬取爬虫"""
    
    name = "crawl_spider"
    start_urls = ["https://example.com"]
    
    config = SpiderConfig(
        max_depth=2,
        concurrent_requests=10,
    )
    
    allowed_domains = ["example.com"]
    
    def parse(self, ctx: SpiderContext):
        for item in ctx.css(".article"):
            yield {
                "title": item.select_one("h2").text if item.select_one("h2") else "",
                "url": ctx.url,
            }
        
        for link in ctx.extract_links():
            if "/article/" in link:
                yield link


# ==================== 示例6: 异步爬虫 ====================

class AsyncNewsSpider(AsyncSpider):
    """异步新闻爬虫"""
    
    name = "async_news_spider"
    start_urls = [f"https://news.ycombinator.com/news?p={i}" for i in range(1, 4)]
    
    config = SpiderConfig(
        concurrent_requests=20,
        download_delay=0.1,
    )
    
    async def parse(self, ctx):
        for item in ctx.css(".athing"):
            title_el = item.select_one(".titleline > a")
            if title_el:
                yield {
                    "title": title_el.text,
                    "link": title_el.get("href", ""),
                }


# ==================== 示例7: 快速爬取 ====================

def quick_crawl_example():
    """快速爬取示例"""
    
    def parse(ctx):
        return {"title": ctx.css("title")[0].text if ctx.css("title") else ""}
    
    results = crawl(
        urls=["https://example.com", "https://example.org"],
        parse_func=parse,
        config=SpiderConfig(concurrent_requests=5)
    )
    
    return results


# ==================== 示例8: 分布式爬虫 ====================

class DistributedSpider(Spider):
    """分布式爬虫"""
    
    name = "distributed_spider"
    start_urls = ["https://example.com"]
    
    config = SpiderConfig(
        dedup_method="redis",
        redis_url="redis://localhost:6379/0",
    )
    
    def parse(self, ctx: SpiderContext):
        yield {"url": ctx.url}


# ==================== 主程序 ====================

if __name__ == "__main__":
    print("=" * 60)
    print("SpiderX 爬虫框架示例")
    print("=" * 60)
    
    print("\n1. 运行基础新闻爬虫...")
    spider = NewsSpider()
    results = spider.run()
    
    print(f"爬取完成! 获取 {len(results)} 条新闻")
    for item in results[:3]:
        print(f"  - {item.get('title', '')[:50]}...")
    
    print(f"\n统计信息: {spider.get_stats()}")
    
    print("\n" + "=" * 60)
    print("更多示例请参考代码中的注释")
    print("=" * 60)

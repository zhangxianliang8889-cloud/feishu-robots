"""
SpiderX 快速入门

安装依赖:
    pip install requests beautifulsoup4 lxml aiohttp
    
    # 可选: JS渲染支持
    pip install playwright && playwright install
    pip install selenium webdriver-manager
    
    # 可选: 分布式支持
    pip install redis
"""

# ==================== 最简示例 ====================

from spiderx import Spider, SpiderConfig
from spiderx.engine import SpiderContext

class SimpleSpider(Spider):
    """最简单的爬虫"""
    
    name = "simple"
    start_urls = ["https://news.ycombinator.com/"]
    
    def parse(self, ctx: SpiderContext):
        for item in ctx.css(".athing"):
            title = item.select_one(".titleline > a")
            if title:
                yield {
                    "title": title.text,
                    "link": title.get("href"),
                }

if __name__ == "__main__":
    spider = SimpleSpider()
    results = spider.run()
    
    print(f"爬取 {len(results)} 条数据")
    for item in results[:5]:
        print(f"  {item['title'][:40]}...")

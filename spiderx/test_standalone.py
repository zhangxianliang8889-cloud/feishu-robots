"""
SpiderX 独立测试 - 爬取 Hacker News 并发送到飞书
"""

import json
import urllib.request
import urllib.error
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
import logging
import re

try:
    import requests
    from bs4 import BeautifulSoup
except ImportError:
    print("请安装依赖: pip install requests beautifulsoup4 lxml")
    exit(1)


FEISHU_WEBHOOK = "https://open.feishu.cn/open-apis/bot/v2/hook/dc73bba3-f734-4e99-8dc6-9463450e16ba"

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class SimpleSpider:
    """简化版爬虫"""
    
    def __init__(self, name="spider", concurrent=5, delay=0.3):
        self.name = name
        self.concurrent = concurrent
        self.delay = delay
        self.results = []
        self.stats = {
            "pages": 0,
            "items": 0,
            "errors": 0,
            "start_time": None,
        }
    
    def fetch(self, url):
        """获取页面"""
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        
        try:
            resp = requests.get(url, headers=headers, timeout=10)
            resp.raise_for_status()
            return resp.text
        except Exception as e:
            logger.error(f"请求失败: {url}, 错误: {e}")
            return None
    
    def parse(self, html, url):
        """解析页面 - 子类重写"""
        pass
    
    def run(self, urls):
        """运行爬虫"""
        self.stats["start_time"] = time.time()
        
        with ThreadPoolExecutor(max_workers=self.concurrent) as executor:
            futures = {executor.submit(self.fetch, url): url for url in urls}
            
            for future in as_completed(futures):
                url = futures[future]
                try:
                    html = future.result()
                    if html:
                        self.stats["pages"] += 1
                        items = self.parse(html, url)
                        if items:
                            self.results.extend(items)
                            self.stats["items"] += len(items)
                        
                        time.sleep(self.delay)
                
                except Exception as e:
                    self.stats["errors"] += 1
                    logger.error(f"处理失败: {url}, 错误: {e}")
        
        return self.results
    
    def get_stats(self):
        stats = self.stats.copy()
        stats["duration"] = time.time() - stats["start_time"]
        return stats


class HackerNewsSpider(SimpleSpider):
    """Hacker News 爬虫"""
    
    def __init__(self):
        super().__init__(name="hn_spider", concurrent=5, delay=0.3)
    
    def parse(self, html, url):
        soup = BeautifulSoup(html, "lxml")
        items = []
        
        for row in soup.select(".athing")[:15]:
            title_el = row.select_one(".titleline > a")
            if title_el:
                subtext = row.next_sibling
                score_el = subtext.select_one(".score") if subtext else None
                
                items.append({
                    "title": title_el.text.strip(),
                    "link": title_el.get("href", ""),
                    "score": score_el.text if score_el else "0 pts",
                })
        
        return items


def send_to_feishu(results):
    """发送到飞书"""
    
    content_lines = [
        "**🚀 SpiderX 爬虫框架测试报告**",
        "",
        f"⏰ **时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"📊 **爬取数量**: {len(results)} 条新闻",
        "",
        "---",
        ""
    ]
    
    for i, item in enumerate(results[:10], 1):
        title = item["title"][:45] + "..." if len(item["title"]) > 45 else item["title"]
        link = item["link"]
        score = item.get("score", "")
        content_lines.append(f"**{i}.** [{title}]({link})")
        content_lines.append(f"    👍 {score}")
        content_lines.append("")
    
    content = "\n".join(content_lines)
    
    message = {
        "msg_type": "interactive",
        "card": {
            "header": {
                "title": {
                    "tag": "plain_text",
                    "content": "SpiderX 爬虫测试结果"
                },
                "template": "blue"
            },
            "elements": [
                {
                    "tag": "markdown",
                    "content": content
                },
                {
                    "tag": "action",
                    "actions": [
                        {
                            "tag": "button",
                            "text": {
                                "tag": "plain_text",
                                "content": "查看 Hacker News"
                            },
                            "url": "https://news.ycombinator.com/",
                            "type": "primary"
                        }
                    ]
                },
                {
                    "tag": "note",
                    "elements": [
                        {
                            "tag": "plain_text",
                            "content": "SpiderX - 高性能 Python 爬虫框架 | 支持: 异步/JS渲染/代理池/分布式"
                        }
                    ]
                }
            ]
        }
    }
    
    try:
        resp = requests.post(
            FEISHU_WEBHOOK,
            json=message,
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        return resp.json()
    
    except Exception as e:
        return {"error": str(e)}


if __name__ == "__main__":
    print("=" * 60)
    print("🕷️  SpiderX 爬虫框架测试")
    print("=" * 60)
    
    print("\n📡 开始爬取 Hacker News...")
    spider = HackerNewsSpider()
    results = spider.run(["https://news.ycombinator.com/"])
    
    print(f"\n✅ 爬取完成!")
    stats = spider.get_stats()
    print(f"   📈 统计: {stats['pages']} 页, {stats['items']} 条, {stats['duration']:.2f}秒")
    
    print("\n📄 爬取结果预览:")
    for item in results[:5]:
        print(f"   • {item['title'][:50]}...")
    
    print("\n📤 发送到飞书...")
    feishu_result = send_to_feishu(results)
    
    if feishu_result.get("StatusCode") == 0:
        print("✅ 发送成功! 请查看飞书消息")
    else:
        print(f"❌ 发送失败: {feishu_result}")
    
    print("\n" + "=" * 60)

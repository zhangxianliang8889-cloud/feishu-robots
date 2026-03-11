"""
SpiderX 测试 - 爬取 Hacker News 并发送到飞书
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import json
import urllib.request
import urllib.error
from datetime import datetime

from engine import Spider, SpiderConfig
from engine import SpiderContext


FEISHU_WEBHOOK = "https://open.feishu.cn/open-apis/bot/v2/hook/dc73bba3-f734-4e99-8dc6-9463450e16ba"


class HackerNewsSpider(Spider):
    """Hacker News 爬虫"""
    
    name = "hn_spider"
    start_urls = ["https://news.ycombinator.com/"]
    
    config = SpiderConfig(
        concurrent_requests=5,
        download_delay=0.3,
        retry_times=3,
    )
    
    allowed_domains = ["news.ycombinator.com"]
    
    def parse(self, ctx: SpiderContext):
        items = ctx.css(".athing")
        for item in items[:10]:
            title_el = item.select_one(".titleline > a")
            if title_el:
                yield {
                    "title": title_el.text.strip(),
                    "link": title_el.get("href", ""),
                    "rank": item.get("id", ""),
                }


def send_to_feishu(results: list):
    """发送结果到飞书"""
    
    lines = [f"**🚀 SpiderX 爬虫测试结果**"]
    lines.append(f"⏰ 时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"📊 爬取数量: {len(results)} 条")
    lines.append("")
    lines.append("---")
    
    for i, item in enumerate(results, 1):
        title = item.get("title", "")[:50]
        link = item.get("link", "")
        lines.append(f"**{i}.** [{title}]({link})")
    
    content = "\n".join(lines)
    
    message = {
        "msg_type": "interactive",
        "card": {
            "header": {
                "title": {
                    "tag": "plain_text",
                    "content": "SpiderX 爬虫框架测试报告"
                },
                "template": "blue"
            },
            "elements": [
                {
                    "tag": "markdown",
                    "content": content
                },
                {
                    "tag": "note",
                    "elements": [
                        {
                            "tag": "plain_text",
                            "content": "SpiderX - 高性能Python爬虫框架"
                        }
                    ]
                }
            ]
        }
    }
    
    try:
        req = urllib.request.Request(
            FEISHU_WEBHOOK,
            data=json.dumps(message).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        
        with urllib.request.urlopen(req, timeout=10) as response:
            result = json.loads(response.read().decode("utf-8"))
            return result
    
    except urllib.error.URLError as e:
        return {"error": str(e)}


if __name__ == "__main__":
    print("=" * 60)
    print("SpiderX 爬虫框架测试")
    print("=" * 60)
    
    print("\n📡 开始爬取 Hacker News...")
    spider = HackerNewsSpider()
    results = spider.run()
    
    print(f"✅ 爬取完成! 获取 {len(results)} 条新闻")
    
    stats = spider.get_stats()
    print(f"📈 统计: 访问 {stats['pages_visited']} 页, 耗时 {stats.get('duration', 0):.2f}秒")
    
    print("\n📄 爬取结果预览:")
    for item in results[:5]:
        print(f"  - {item['title'][:40]}...")
    
    print("\n📤 发送到飞书...")
    feishu_result = send_to_feishu(results)
    
    if feishu_result.get("StatusCode") == 0:
        print("✅ 发送成功! 请查看飞书消息")
    else:
        print(f"❌ 发送失败: {feishu_result}")
    
    print("\n" + "=" * 60)

import requests
import json
import time
import schedule
import re
from datetime import datetime
from bs4 import BeautifulSoup

# ====================== 【配置区域】 ======================
FEISHU_WEBHOOK = "https://open.feishu.cn/open-apis/bot/v2/hook/dc73bba3-f734-4e99-8dc6-9463450e16ba"
PUSH_TIME = "09:00"
SEARCH_KEYWORDS = ["影视行业", "电影票房", "电视剧", "影视投资", "娱乐产业"]
FILTER_WORDS = ["广告", "推广", "购物", "直播", "带货", "加盟", "代理", "课程", "招聘"]
TOP_N = 10
# ========================================================

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "zh-CN,zh;q=0.9"
}

def get_wechat_hot_articles():
    print("正在抓取影视行业公众号热文...")
    article_counter = {}
    article_data = {}
    
    for keyword in SEARCH_KEYWORDS:
        print(f"  搜索关键词: {keyword}")
        try:
            url = f"https://weixin.sogou.com/weixin?type=2&query={keyword}&ie=utf8"
            resp = requests.get(url, headers=HEADERS, timeout=15)
            resp.encoding = "utf-8"
            soup = BeautifulSoup(resp.text, "lxml")
            article_items = soup.select(".news-list li")
            
            for idx, item in enumerate(article_items):
                title_a = item.select_one(".txt-box h3 a")
                if not title_a:
                    continue
                    
                title = title_a.get_text(strip=True)
                title = re.sub(r'\s+', '', title)
                
                if any(word in title for word in FILTER_WORDS):
                    continue
                
                if len(title) < 8:
                    continue
                
                source_el = item.select_one(".s-p") or item.select_one(".all-time-y2")
                if source_el:
                    source = source_el.get_text(strip=True)
                    source = re.sub(r'\d+', '', source).strip()
                else:
                    source = "影视公众号"
                
                raw_url = title_a.get("href", "")
                if raw_url and not raw_url.startswith("http"):
                    raw_url = "https://weixin.sogou.com" + raw_url
                
                real_url = raw_url
                try:
                    real_resp = requests.get(raw_url, headers=HEADERS, allow_redirects=False, timeout=5)
                    real_url = real_resp.headers.get("Location", raw_url)
                    if real_url and not real_url.startswith("http"):
                        real_url = "https://weixin.sogou.com" + real_url
                except:
                    pass
                
                if title not in article_counter:
                    article_counter[title] = 0
                    article_data[title] = {
                        "source": source,
                        "url": real_url,
                        "positions": []
                    }
                
                article_counter[title] += 1
                article_data[title]["positions"].append(idx + 1)
            
            time.sleep(0.5)
        except Exception as e:
            print(f"  关键词 {keyword} 抓取出错: {e}")
    
    results = []
    for title, count in article_counter.items():
        data = article_data[title]
        avg_position = sum(data["positions"]) / len(data["positions"])
        hot_score = count * 10000 - avg_position * 100
        
        results.append({
            "source": data["source"],
            "title": title,
            "url": data["url"],
            "hot_score": hot_score,
            "appear_count": count
        })
    
    results.sort(key=lambda x: x["hot_score"], reverse=True)
    
    top_articles = results[:TOP_N]
    print(f"  筛选热度 TOP {len(top_articles)} 条")
    
    return top_articles

def send_to_feishu(articles):
    if not articles:
        print("无优质内容可推送")
        return
    
    elements = []
    elements.append({
        "tag": "div",
        "text": {
            "tag": "lark_md",
            "content": f"**🎬 影视行业每日热点简报**\n📅 {datetime.now().strftime('%Y年%m月%d日')}\n🔥 已按热度排序，精选 TOP {len(articles)}"
        }
    })
    elements.append({"tag": "hr"})
    
    elements.append({
        "tag": "div",
        "text": {
            "tag": "lark_md",
            "content": "**🔥 公众号热门文章（按热度排序）**"
        }
    })
    
    for i, art in enumerate(articles, 1):
        hot_label = ""
        if art["appear_count"] >= 4:
            hot_label = "🔥🔥🔥"
        elif art["appear_count"] >= 3:
            hot_label = "🔥🔥"
        elif art["appear_count"] >= 2:
            hot_label = "🔥"
        
        elements.append({
            "tag": "div",
            "text": {
                "tag": "lark_md",
                "content": f"{i}. {hot_label} [{art['title']}]({art['url']})\n   📰 {art['source']} · 出现{art['appear_count']}次"
            }
        })
    
    elements.append({"tag": "hr"})
    elements.append({
        "tag": "note",
        "elements": [{
            "tag": "plain_text",
            "content": "💡 已按热度排序（在多个关键词搜索中出现次数越多排序越靠前），点击标题即可阅读"
        }]
    })
    
    payload = {
        "msg_type": "interactive",
        "card": {
            "elements": elements
        }
    }
    
    try:
        resp = requests.post(FEISHU_WEBHOOK, json=payload, headers=HEADERS, timeout=10)
        if resp.status_code == 200:
            print("✅ 影视热点简报已成功推送！")
        else:
            print(f"❌ 推送失败，状态码：{resp.status_code}")
    except Exception as e:
        print(f"❌ 推送出错：{e}")

def daily_job():
    print(f"\n===== 开始执行影视热点抓取任务 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} =====")
    articles = get_wechat_hot_articles()
    print(f"抓取统计：共筛选 {len(articles)} 条高热度文章")
    send_to_feishu(articles)
    print(f"===== 任务执行完成 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} =====\n")

if __name__ == "__main__":
    print("===== 🎬 影视行业热点推送机器人已启动 =====")
    print(f"📌 每天{PUSH_TIME}自动推送")
    print(f"📌 搜索关键词：{', '.join(SEARCH_KEYWORDS)}")
    print(f"📌 按热度排序，精选 TOP {TOP_N} 条")
    print("===== 保持窗口打开，机器人将持续运行 =====\n")
    schedule.every().day.at(PUSH_TIME).do(daily_job)
    while True:
        schedule.run_pending()
        time.sleep(60)

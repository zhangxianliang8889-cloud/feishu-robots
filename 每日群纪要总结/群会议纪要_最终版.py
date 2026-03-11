#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
群会议纪要AI机器人 - 最终版
机器人名称：群会议纪要
功能：自动生成每日/每周/每月群聊会议纪要并发送到飞书群
支持：配置文件、群组白名单/黑名单、智能过滤、防重复发送
"""

import sys
import os
# 设置UTF-8编码
sys.stdout = open(sys.stdout.fileno(), mode='w', encoding='utf-8', buffering=1)
sys.stderr = open(sys.stderr.fileno(), mode='w', encoding='utf-8', buffering=1)

import requests
import json
import time
import schedule
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    from config import *
except ImportError:
    DAILY_TIME = "21:00"
    WEEKLY_TIME = "09:00"
    MONTHLY_TIME = "09:30"
    SEND_MODE = "all"
    WHITELIST_GROUPS = []
    BLACKLIST_GROUPS = []
    SKIP_EMPTY_GROUPS = True
    MIN_MESSAGE_COUNT = 3
    SKIP_SYSTEM_ONLY = True
    REPORT_FORMAT = "simple"
    SHOW_GENERATE_TIME = True
    SHOW_BOT_SIGNATURE = True
    DEBUG_MODE = False
    DEBUG_GROUP = "张贤良测试群"
    TEST_MODE = False
    TEST_GROUP = "张贤良测试群"
    FEISHU_APP_ID = "cli_a9233dfe18389bde"
    FEISHU_APP_SECRET = "8gvZm8C04sS0GJXtDQdkkeAOJV6gCr4w"

try:
    from smart_summarizer import smart_summarize, extract_complete_sentences, categorize_sentences, generate_coherent_summary
    SMART_SUMMARIZER_AVAILABLE = True
except ImportError:
    SMART_SUMMARIZER_AVAILABLE = False

try:
    from unified_summarizer import (
        is_noise_content, 
        extract_complete_sentences as unified_extract_sentences,
        generate_topic_summary,
        generate_tasks_summary,
        generate_suggestions_summary,
        generate_questions_summary,
        smart_categorize_messages
    )
    UNIFIED_SUMMARIZER_AVAILABLE = True
except ImportError:
    UNIFIED_SUMMARIZER_AVAILABLE = False

try:
    from ai_summarizer import ai_summarize_messages, ai_generate_inspiration, ai_categorize_and_summarize
    AI_SUMMARIZER_AVAILABLE = True
except ImportError:
    AI_SUMMARIZER_AVAILABLE = False

try:
    from concurrent_processor import ConcurrentProcessor, TokenCache, PerformanceMonitor, run_concurrent_tasks
    CONCURRENT_PROCESSOR_AVAILABLE = True
except ImportError:
    CONCURRENT_PROCESSOR_AVAILABLE = False

try:
    from send_check_system import SendCheckSystem, ContentVersionManager
    SEND_CHECK_SYSTEM_AVAILABLE = True
except ImportError:
    SEND_CHECK_SYSTEM_AVAILABLE = False

try:
    from incremental_fetcher import IncrementalMessageFetcher, DistributedLock, RateLimiter
    INCREMENTAL_FETCHER_AVAILABLE = True
except ImportError:
    INCREMENTAL_FETCHER_AVAILABLE = False

try:
    from task_state_manager import TaskStateManager, IdempotentTaskExecutor, TaskStatus
    TASK_STATE_MANAGER_AVAILABLE = True
except ImportError:
    TASK_STATE_MANAGER_AVAILABLE = False

try:
    from enhanced_api_client import EnhancedRetryClient, CircuitBreaker, FeishuAPIClient
    ENHANCED_API_CLIENT_AVAILABLE = True
except ImportError:
    ENHANCED_API_CLIENT_AVAILABLE = False

try:
    from unified_config import ConfigManager, UnifiedLogger, MonitoringSystem
    UNIFIED_CONFIG_AVAILABLE = True
except ImportError:
    UNIFIED_CONFIG_AVAILABLE = False

BOT_NAME = "群会议纪要"
CONTENT_VERSION = "2.0"

NO_PROXY = {}

# 关键词相关的金句和建议映射
INSPIRATION_MAP = {
    "招聘": [
        "📚 德鲁克：管理就是用人之长",
        "💡 建议：建立人才画像标准，统一招聘认知"
    ],
    "人才": [
        "🎯 马云：找对人比做对事更重要",
        "💡 建议：建立人才发展通道，留住优秀人才"
    ],
    "团队": [
        "🌟 孔子：二人同心，其利断金",
        "💡 建议：定期组织团队建设活动，增强凝聚力"
    ],
    "管理": [
        "📈 德鲁克：管理是实践的艺术",
        "💡 建议：建立OKR或KPI体系，明确目标"
    ],
    "学习": [
        "🎨 达芬奇：学习是一辈子的事",
        "💡 建议：建立每周学习分享会，共同成长"
    ],
    "创新": [
        "⚡ 爱因斯坦：创新就是思维的突破",
        "💡 建议：设立创新奖励机制，鼓励尝试"
    ],
    "目标": [
        "🎖️ 拿破仑：明确的目标是成功的一半",
        "💡 建议：将大目标拆解为小任务，逐步实现"
    ],
    "沟通": [
        "💬 卡耐基：沟通是管理的浓缩",
        "💡 建议：建立开放的沟通氛围，鼓励表达"
    ],
    "执行力": [
        "💪 稻盛和夫：现场有神明",
        "💡 建议：建立任务追踪机制，确保落地"
    ],
    "成长": [
        "🚀 乔布斯：Stay hungry, stay foolish",
        "💡 建议：设定个人成长计划，定期复盘"
    ]
}

# 通用金句和建议
GENERAL_INSPIRATIONS = [
    "📚 德鲁克：把事做正确，做正确的事",
    "💡 稻盛和夫：付出不亚于任何人的努力",
    "🎯 张瑞敏：没有成功的企业，只有时代的企业",
    "🚀 贝索斯：我们要做10年不会变的事情",
    "⚡ 马斯克：如果一件事在物理上是可能的，那就去做",
    "🌱 任正非：方向要大致正确，组织要充满活力",
    "💪 马云：今天很残酷，明天更残酷，后天很美好",
    "🎨 乔布斯：Stay hungry, stay foolish",
    "📊 格鲁夫：只有偏执狂才能生存",
    "🌟 盖茨：你的最不愉快的经历，可能是你最宝贵的财富"
]

def get_smart_inspiration(top_keywords):
    """根据关键词智能生成建议或金句"""
    import random
    
    if not top_keywords:
        return random.choice(GENERAL_INSPIRATIONS)
    
    matched_inspirations = []
    for keyword in top_keywords:
        for key, inspirations in INSPIRATION_MAP.items():
            if key in keyword or keyword in key:
                matched_inspirations.extend(inspirations)
    
    if matched_inspirations:
        return random.choice(matched_inspirations)
    else:
        return random.choice(GENERAL_INSPIRATIONS)

SEND_RECORDS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "send_records.json")

# 初始化幂等执行器和分布式锁（如果可用）
_state_manager = None
_lock_manager = None
_idempotent_executor = None
_rate_limiter = None

if TASK_STATE_MANAGER_AVAILABLE:
    _state_manager = TaskStateManager()
    print("✅ 幂等任务管理器已启用")

if INCREMENTAL_FETCHER_AVAILABLE:
    _lock_manager = DistributedLock()
    _rate_limiter = RateLimiter(max_requests=20, window_seconds=1)
    print("✅ 分布式锁和API限流器已启用")

if _state_manager and _lock_manager:
    _idempotent_executor = IdempotentTaskExecutor(_state_manager, _lock_manager)
    print("✅ 幂等任务执行器已启用")

def load_send_records():
    if os.path.exists(SEND_RECORDS_FILE):
        try:
            with open(SEND_RECORDS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            pass
    return {}

def save_send_records(records):
    try:
        with open(SEND_RECORDS_FILE, 'w', encoding='utf-8') as f:
            json.dump(records, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"❌ 保存发送记录失败: {e}")

def is_already_sent(chat_id, summary_type, date_key):
    records = load_send_records()
    record_key = f"{chat_id}_{summary_type}_{date_key}"
    return record_key in records

def mark_as_sent(chat_id, summary_type, date_key, chat_name):
    records = load_send_records()
    record_key = f"{chat_id}_{summary_type}_{date_key}"
    records[record_key] = {
        "chat_name": chat_name,
        "sent_time": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        "summary_type": summary_type,
        "date_key": date_key
    }
    save_send_records(records)
    print(f"📝 已记录发送: {chat_name} - {summary_type} - {date_key}")

def clean_old_records():
    records = load_send_records()
    now = datetime.now()
    keys_to_remove = []
    
    for key, value in records.items():
        try:
            sent_time = datetime.strptime(value.get("sent_time", ""), '%Y-%m-%d %H:%M:%S')
            days_diff = (now - sent_time).days
            if days_diff > 35:
                keys_to_remove.append(key)
        except:
            keys_to_remove.append(key)
    
    for key in keys_to_remove:
        del records[key]
    
    if keys_to_remove:
        save_send_records(records)
        print(f"🧹 已清理 {len(keys_to_remove)} 条过期发送记录")

def is_valid_send_time():
    """
    检查当前时间是否适合发送消息
    禁止时间：23:00-08:30（凌晨和早上太早）
    允许时间：08:30-23:00
    """
    now = datetime.now()
    hour = now.hour
    minute = now.minute
    
    if hour < 8 or (hour == 8 and minute < 30):
        print(f"⚠️ 当前时间 {now.strftime('%H:%M')} 不在发送时间范围内（08:30-23:00），跳过发送")
        return False
    if hour >= 23:
        print(f"⚠️ 当前时间 {now.strftime('%H:%M')} 不在发送时间范围内（08:30-23:00），跳过发送")
        return False
    return True

def check_missed_summaries():
    """检查是否有漏发的会议纪要"""
    missed = []
    now = datetime.now()
    records = load_send_records()
    
    token = get_feishu_token()
    if not token:
        print("❌ Token获取失败，无法检查漏发")
        return missed
    
    groups = get_bot_groups(token)
    filtered_groups = filter_groups(groups)
    
    yesterday = now - timedelta(days=1)
    yesterday_key = yesterday.strftime('%Y-%m-%d')
    
    for group in filtered_groups:
        chat_id = group.get("chat_id")
        chat_name = group.get("name", "未知群")
        record_key = f"{chat_id}_daily_{yesterday_key}"
        if record_key not in records:
            missed.append({
                "type": "daily",
                "date_key": yesterday_key,
                "chat_id": chat_id,
                "chat_name": chat_name,
                "reason": "昨日日报未发送"
            })
    
    if now.weekday() == 0 or now.weekday() == 1:
        monday = now - timedelta(days=now.weekday())
        last_week_start = monday - timedelta(weeks=1)
        week_key = f"{last_week_start.strftime('%Y-%m-%d')}_{(monday - timedelta(days=1)).strftime('%Y-%m-%d')}"
        
        for group in filtered_groups:
            chat_id = group.get("chat_id")
            chat_name = group.get("name", "未知群")
            record_key = f"{chat_id}_weekly_{week_key}"
            if record_key not in records:
                missed.append({
                    "type": "weekly",
                    "date_key": week_key,
                    "chat_id": chat_id,
                    "chat_name": chat_name,
                    "reason": "上周周报未发送"
                })
    
    if now.day <= 3:
        first_of_month = now.replace(day=1)
        last_month_start = (first_of_month - timedelta(days=1)).replace(day=1)
        month_key = last_month_start.strftime('%Y-%m')
        
        for group in filtered_groups:
            chat_id = group.get("chat_id")
            chat_name = group.get("name", "未知群")
            record_key = f"{chat_id}_monthly_{month_key}"
            if record_key not in records:
                missed.append({
                    "type": "monthly",
                    "date_key": month_key,
                    "chat_id": chat_id,
                    "chat_name": chat_name,
                    "reason": "上月月报未发送"
                })
    
    return missed

def send_missed_summaries():
    """补发漏发的会议纪要"""
    if not is_valid_send_time():
        return
    
    missed = check_missed_summaries()
    
    if not missed:
        print("✅ 无漏发会议纪要")
        return
    
    print(f"⚠️ 发现 {len(missed)} 个漏发会议纪要，开始补发...")
    print("=" * 60)
    
    token = get_feishu_token()
    if not token:
        print("❌ Token获取失败，无法补发")
        return
    
    success_count = 0
    fail_count = 0
    
    for item in missed:
        print(f"🔄 补发: {item['chat_name']} - {item['type']} ({item['reason']})")
        
        try:
            result = generate_and_send_summary(token, item["chat_id"], item["chat_name"], item["type"])
            if result == True:
                success_count += 1
            elif result == False:
                fail_count += 1
        except Exception as e:
            print(f"❌ [{item['chat_name']}] 补发失败: {e}")
            fail_count += 1
    
    print("=" * 60)
    print(f"📊 补发完成: ✅ {success_count} ❌ {fail_count}")

def get_feishu_token():
    url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
    data = {"app_id": FEISHU_APP_ID, "app_secret": FEISHU_APP_SECRET}
    try:
        r = requests.post(url, json=data, timeout=10, proxies=NO_PROXY)
        r.raise_for_status()
        response = r.json()
        if "tenant_access_token" in response:
            return response["tenant_access_token"]
        else:
            print(f"❌ 获取Token失败: {response}")
            return None
    except Exception as e:
        print(f"❌ 获取Token时发生错误: {e}")
        return None

def get_bot_groups(token):
    url = "https://open.feishu.cn/open-apis/im/v1/chats"
    headers = {"Authorization": f"Bearer {token}"}
    params = {"page_size": 100}
    
    try:
        r = requests.get(url, headers=headers, params=params, timeout=10, proxies=NO_PROXY)
        r.raise_for_status()
        response = r.json()
        
        if response.get("code") == 0:
            data = response.get("data", {})
            return data.get("items", [])
        else:
            print(f"⚠️ 获取群列表失败: {response}")
            return []
    except Exception as e:
        print(f"⚠️ 获取群列表时发生错误: {e}")
        return []

def filter_groups(groups):
    """根据配置过滤群组"""
    filtered = []
    
    if TEST_MODE:
        for group in groups:
            if group.get("name", "") == TEST_GROUP:
                filtered.append(group)
                break
        return filtered
    
    for group in groups:
        name = group.get("name", "")
        
        if DEBUG_MODE:
            if name == DEBUG_GROUP:
                filtered.append(group)
            continue
        
        if SEND_MODE == "whitelist":
            if name in WHITELIST_GROUPS:
                filtered.append(group)
        elif SEND_MODE == "blacklist":
            if name not in BLACKLIST_GROUPS:
                filtered.append(group)
        else:
            if name not in BLACKLIST_GROUPS:
                filtered.append(group)
    
    return filtered

def get_group_members(token, chat_id):
    if not token or not chat_id:
        return {}
    
    url = f"https://open.feishu.cn/open-apis/im/v1/chats/{chat_id}/members"
    headers = {"Authorization": f"Bearer {token}"}
    params = {"page_size": 100}
    
    members_map = {}
    page_token = None
    
    try:
        while True:
            if page_token:
                params["page_token"] = page_token
            
            r = requests.get(url, headers=headers, params=params, timeout=10, proxies=NO_PROXY)
            r.raise_for_status()
            response = r.json()
            
            if response.get("code") != 0:
                break
            
            data = response.get("data", {})
            members = data.get("items", [])
            
            for member in members:
                user_id = member.get("member_id", "")
                name = member.get("name", user_id[:8])
                if user_id:
                    members_map[user_id] = name
            
            if not data.get("has_more", False):
                break
            
            page_token = data.get("page_token")
            
    except Exception as e:
        print(f"⚠️ 获取群成员时发生错误: {e}")
    
    return members_map

def get_recent_messages(token, chat_id, hours=24):
    if not token or not chat_id:
        return []
    
    now = datetime.now()
    start_time = now - timedelta(hours=hours)
    
    start_ts = int(start_time.timestamp() * 1000)
    end_ts = int(now.timestamp() * 1000)
    
    return get_messages_by_time_range(token, chat_id, start_ts, end_ts)

def get_messages_by_time_range(token, chat_id, start_ts, end_ts):
    if not token or not chat_id:
        return []
    
    url = "https://open.feishu.cn/open-apis/im/v1/messages"
    headers = {"Authorization": f"Bearer {token}"}
    params = {
        "container_id": chat_id,
        "container_id_type": "chat",
        "page_size": 50
    }
    
    all_messages = []
    page_token = None
    
    try:
        while True:
            if page_token:
                params["page_token"] = page_token
            
            r = requests.get(url, headers=headers, params=params, timeout=10, proxies=NO_PROXY)
            r.raise_for_status()
            response = r.json()
            
            if response.get("code") != 0:
                break
            
            data = response.get("data", {})
            messages = data.get("items", [])
            
            for msg in messages:
                create_time = int(msg.get("create_time", 0))
                if start_ts <= create_time <= end_ts:
                    all_messages.append(msg)
            
            if not data.get("has_more", False):
                break
            
            page_token = data.get("page_token")
            
    except Exception as e:
        print(f"❌ 获取消息时发生错误: {e}")
    
    return all_messages

def get_user_name(user_id, members_map):
    if not user_id:
        return "未知"
    return members_map.get(user_id, user_id[:8])

def extract_chat_records(messages, members_map=None):
    if members_map is None:
        members_map = {}
    
    records = []
    for msg in messages:
        msg_type = msg.get("msg_type")
        if msg_type == "text":
            body = msg.get("body", {})
            content_str = body.get("content", "{}")
            try:
                content = json.loads(content_str)
                text = content.get("text", "").strip()
                if text:
                    sender_info = msg.get("sender", {})
                    sender_id = sender_info.get("id", "未知")
                    sender_type = sender_info.get("sender_type", "")
                    sender_name = get_user_name(sender_id, members_map)
                    
                    if sender_type == "app" or sender_id.startswith("cli_") or "机器人" in sender_name or sender_name.startswith("cli_"):
                        continue
                    
                    time_str = datetime.fromtimestamp(int(msg.get("create_time", 0))//1000).strftime("%H:%M")
                    records.append({
                        "time": time_str,
                        "sender": sender_name,
                        "content": text
                    })
            except json.JSONDecodeError:
                text = content_str.strip()
                if text and text != "None":
                    time_str = datetime.fromtimestamp(int(msg.get("create_time", 0))//1000).strftime("%H:%M")
                    records.append({
                        "time": time_str,
                        "sender": "未知",
                        "content": text
                    })
    return records

def format_chat_text(records):
    lines = []
    for record in records:
        lines.append(f"[{record['time']}] {record['sender']}: {record['content']}")
    return "\n".join(lines)

def local_summarize(chat_text, summary_type="daily", chat_name="", date_range="", total_count=0):
    """本地算法智能总结会议纪要 - 支持日报/周报/月报"""
    if not chat_text or chat_text.strip() == "":
        if summary_type == "daily":
            return generate_daily_summary(0, 0, [], [], [], [], [], chat_name, date_range)
        elif summary_type == "weekly":
            return generate_weekly_summary(0, 0, [], [], [], [], [], [], [], set(), chat_name, date_range)
        else:
            return generate_monthly_summary(0, 0, [], [], [], [], [], [], [], set(), chat_name, date_range)
    
    import re
    from collections import Counter, defaultdict
    
    lines = chat_text.strip().split('\n')
    total_messages = len(lines)
    
    participants = set()
    keywords = []
    links = []
    tasks = []
    decisions = []
    important_info = []
    topics = []
    questions = []
    suggestions = []
    
    topic_groups = defaultdict(list)
    all_messages = []
    
    task_patterns = [
        r'需要([^。！？\n]{2,100})',
        r'请([^。！？\n]{2,50})(完成|处理|跟进)',
        r'([^。！？\n]{2,20})负责([^。！？\n]{2,100})',
        r'待办[:：]([^。！？\n]{2,100})',
        r'任务[:：]([^。！？\n]{2,100})',
        r'记得([^。！？\n]{2,100})',
        r'别忘了([^。！？\n]{2,100})',
    ]
    
    decision_patterns = [
        r'决定([^。！？\n]{2,100})',
        r'确定([^。！？\n]{2,100})',
        r'同意([^。！？\n]{2,50})',
        r'确认([^。！？\n]{2,100})',
        r'定下来([^。！？\n]{2,50})',
        r'就这么定了',
        r'通过([^。！？\n]{2,50})',
    ]
    
    important_patterns = [
        r'重要[:：]([^。！？\n]{2,100})',
        r'注意[:：]([^。！？\n]{2,100})',
        r'提醒([^。！？\n]{2,50})',
        r'通知[:：]([^。！？\n]{2,100})',
    ]
    
    question_patterns = [
        r'([^。！？\n]{2,50})\?',
        r'([^。！？\n]{2,50})？',
        r'怎么([^。！？\n]{2,100})',
        r'如何([^。！？\n]{2,100})',
        r'为什么([^。！？\n]{2,100})',
        r'有没有([^。！？\n]{2,100})',
    ]
    
    suggestion_patterns = [
        r'建议([^。！？\n]{2,100})',
        r'可以([^。！？\n]{2,100})',
        r'试试([^。！？\n]{2,100})',
        r'不如([^。！？\n]{2,100})',
        r'推荐([^。！？\n]{2,100})',
    ]
    
    stop_words = {'的', '了', '是', '在', '有', '和', '就', '不', '人', '都', 
                  '一', '一个', '上', '也', '很', '到', '说', '要', '去', '你',
                  '会', '着', '没有', '看', '好', '自己', '这', '那', '什么',
                  '吗', '呢', '吧', '啊', '嗯', '哦', '哈', '呀', '额', '这个',
                  '那个', '可以', '可能', '应该', '还是', '但是', '因为', '所以',
                  '大家', '早上好', '好的', '收到', '谢谢', '感谢', '没问题',
                  '今天', '明天', '昨天', '下午', '上午', '晚上', '几点', '开始',
                  '什么', '怎么', '哪里', '多少', '怎样', '如何', '为什么',
                  '总新闻数', 'AI分析数', '时间', '类型', '简报', '热点早报',
                  '测试推送', '老板专属', '每日资讯', 'This', 'message', 'was',
                  'recalled', '消息撤回'}
    
    topic_keywords_map = {
        '消费理财': ['消费', '收入', '信用卡', '透支', '借钱', '上岸', '余地', '超前'],
        '制度监管': ['制度', '监管', '政策', '税', '法律', '规定', '出台'],
        '泰国文化': ['泰国', '穆斯林', '宗教', '神明', '涅槃', '睡莲', '夜叉', '郑王庙'],
        '个人成长': ['自律', '成长', '读书', '独处', '运动', '复盘', '内向求'],
        '情绪管理': ['愤怒', '情绪', '脾气', '耐心', '磨炼', '平静'],
        '创新思维': ['发呆', '创造力', '创新', '大脑', '思考', '灵感', '留白'],
        '人生哲学': ['人生', '命运', '生命', '相信', '谦虚', '人格', '闭环'],
        '商业管理': ['IP', '设计', '泡泡玛特', '丑萌', '形象'],
        '其他': []
    }
    
    for line in lines:
        match = re.match(r'\[(\d{2}:\d{2})\]\s*(.+?):\s*(.+)', line)
        if match:
            time, sender, content = match.groups()
            participants.add(sender)
            
            all_messages.append({
                'time': time,
                'sender': sender,
                'content': content
            })
            
            for pattern in task_patterns:
                task_match = re.search(pattern, content)
                if task_match:
                    tasks.append(task_match.group(0).strip())
                    break
            
            for pattern in decision_patterns:
                decision_match = re.search(pattern, content)
                if decision_match:
                    decisions.append(decision_match.group(0).strip())
                    break
            
            for pattern in important_patterns:
                info_match = re.search(pattern, content)
                if info_match:
                    important_info.append(info_match.group(0).strip())
                    break
            
            for pattern in question_patterns:
                q_match = re.search(pattern, content)
                if q_match:
                    questions.append(q_match.group(0).strip())
                    break
            
            for pattern in suggestion_patterns:
                s_match = re.search(pattern, content)
                if s_match:
                    suggestions.append(s_match.group(0).strip())
                    break
            
            url_match = re.search(r'https?://[^\s]+', content)
            if url_match:
                links.append(url_match.group(0))
            
            words = re.findall(r'[\u4e00-\u9fa5]{2,8}', content)
            for word in words:
                if (word not in stop_words and 
                    len(word) >= 2 and 
                    not word.startswith('关于') and
                    not re.match(r'^[0-9]+$', word)):
                    keywords.append(word)
            
            if len(content) > 10 and not content.startswith('**') and 'http' not in content:
                clean_content = re.sub(r'[【\[\(].*?[\]\)】]', '', content)
                clean_content = re.sub(r'\*+', '', clean_content)
                clean_content = clean_content.strip()
                if len(clean_content) > 5 and clean_content not in ['This message was recalled']:
                    topics.append(clean_content[:30])
                    
                    matched_topic = '其他'
                    for topic_name, topic_keywords in topic_keywords_map.items():
                        if topic_name == '其他':
                            continue
                        for kw in topic_keywords:
                            if kw in content:
                                matched_topic = topic_name
                                break
                        if matched_topic != '其他':
                            break
                    
                    topic_groups[matched_topic].append(clean_content)
    
    keyword_freq = Counter(keywords).most_common(10)
    top_keywords = [word for word, _ in keyword_freq[:5]]
    
    participant_count = len(participants)
    
    if summary_type == "daily":
        return generate_daily_summary(participant_count, total_messages, topics, top_keywords, decisions, tasks, links, chat_name, date_range, topic_groups, all_messages)
    elif summary_type == "weekly":
        return generate_weekly_summary(participant_count, total_messages, topics, top_keywords, decisions, tasks, links, questions, suggestions, participants, chat_name, date_range, topic_groups, all_messages)
    else:
        return generate_monthly_summary(participant_count, total_messages, topics, top_keywords, decisions, tasks, links, questions, suggestions, participants, chat_name, date_range, topic_groups, all_messages)

def generate_daily_summary(participant_count, total_messages, topics, top_keywords, decisions, tasks, links, chat_name="", date_range="", topic_groups=None, all_messages=None):
    """生成日报格式 - 简洁提炼版（改进版：使用智能总结）"""
    import re
    
    ai_result = {"success": False}
    
    def is_noise_content(text):
        """判断是否是噪音内容"""
        noise_patterns = [
            r'^[好的收到嗯哦]+$',
            r'^[表情图片]+$',
            r'^[\d\s]+$',
            r'^[是的对]+$',
        ]
        for pattern in noise_patterns:
            if re.match(pattern, text):
                return True
        return False
    
    summary_parts = []
    
    if chat_name and date_range:
        summary_parts.append(f"📊 {chat_name} - 群会议纪要日报 ({date_range})")
        summary_parts.append("")
    
    summary_parts.append("═" * 20)
    summary_parts.append(f"📈 今日数据：{total_messages} 条消息 | {participant_count} 人参与")
    summary_parts.append("═" * 20)
    summary_parts.append("")
    
    summary_parts.append("📌 今日要点")
    summary_parts.append("─" * 20)
    
    if AI_SUMMARIZER_AVAILABLE and all_messages:
        ai_result = ai_summarize_messages(all_messages, summary_type="daily")
        
        if ai_result.get("success"):
            categories = ai_result.get("categories", {})
            
            category_icons = {
                "工作讨论": "💼",
                "项目进展": "📊",
                "问题求助": "❓",
                "经验分享": "💡",
                "决策事项": "✅",
                "其他": "📝"
            }
            
            for category, summary_text in categories.items():
                if category == "其他" or not summary_text:
                    continue
                
                icon = category_icons.get(category, "📌")
                summary_parts.append(f"")
                summary_parts.append(f"{icon} {category}")
                summary_parts.append(summary_text[:250])
            
            key_insights = ai_result.get("key_insights", [])
            if key_insights:
                summary_parts.append(f"")
                summary_parts.append("💡 关键洞察")
                for insight in key_insights[:2]:
                    summary_parts.append(f"• {insight[:100]}")
        else:
            summary_parts.append(f"")
            summary_parts.append(ai_result.get("summary", "暂无具体讨论内容"))
    
    elif SMART_SUMMARIZER_AVAILABLE and all_messages:
        smart_result = smart_summarize(all_messages, summary_type="daily")
        
        category_icons = {
            "工作讨论": "💼",
            "项目进展": "📊",
            "问题求助": "❓",
            "经验分享": "💡",
            "决策事项": "✅",
            "其他": "📝"
        }
        
        for category, data in smart_result.get("categories", {}).items():
            if category == "其他" or data.get("count", 0) < 2:
                continue
            
            icon = category_icons.get(category, "📌")
            summary_parts.append(f"")
            summary_parts.append(f"{icon} {category}")
            
            summary_text = data.get("summary", "")
            if summary_text and summary_text != "暂无具体讨论内容。":
                summary_parts.append(summary_text[:200])
    
    elif topic_groups and len(topic_groups) > 0:
        topic_summaries = {
            '消费理财': {'icon': '�', 'title': '消费理财观念'},
            '制度监管': {'icon': '🏛️', 'title': '制度与文化洞察'},
            '泰国文化': {'icon': '🏛️', 'title': '制度与文化洞察'},
            '个人成长': {'icon': '🧘', 'title': '个人成长与自律'},
            '情绪管理': {'icon': '🙏', 'title': '情绪与人生哲学'},
            '创新思维': {'icon': '💭', 'title': '创新思维启示'},
            '人生哲学': {'icon': '�', 'title': '情绪与人生哲学'},
            '商业管理': {'icon': '💼', 'title': '商业洞察'}
        }
        
        used_titles = set()
        
        for topic_name, topic_contents in topic_groups.items():
            if topic_name == '其他' or len(topic_contents) == 0:
                continue
            
            if topic_name not in topic_summaries:
                continue
            
            topic_info = topic_summaries[topic_name]
            title = topic_info['title']
            
            if title in used_titles:
                continue
            used_titles.add(title)
            
            summary_parts.append(f"")
            summary_parts.append(f"{topic_info['icon']} {title}")
            
            complete_sentences = []
            for content in topic_contents[:10]:
                sentences = re.split(r'[。！？\n]', content)
                for s in sentences:
                    s = s.strip()
                    if len(s) > 10 and not is_noise_content(s):
                        complete_sentences.append(s)
            
            unique_sentences = []
            for sentence in complete_sentences[:5]:
                is_dup = False
                for us in unique_sentences:
                    if sentence[:15] in us or us[:15] in sentence:
                        is_dup = True
                        break
                if not is_dup:
                    unique_sentences.append(sentence)
            
            if unique_sentences:
                summary_text = "。".join(unique_sentences[:2]) + "。"
                summary_parts.append(summary_text[:200])
    
    elif topics:
        unique_topics = []
        for t in topics[:10]:
            is_dup = False
            for ut in unique_topics:
                if t[:15] in ut or ut[:15] in t:
                    is_dup = True
                    break
            if not is_dup and len(unique_topics) < 5:
                unique_topics.append(t)
        
        for topic in unique_topics:
            summary_parts.append(f"• {topic}")
    elif top_keywords:
        for kw in top_keywords[:5]:
            summary_parts.append(f"• {kw}")
    else:
        summary_parts.append("• 暂无具体讨论内容")
    summary_parts.append("")
    
    summary_parts.append("✅ 完成事项")
    summary_parts.append("─" * 20)
    if decisions:
        for d in decisions[:3]:
            summary_parts.append(f"• {d}")
    else:
        summary_parts.append("• 暂无")
    summary_parts.append("")
    
    summary_parts.append("📋 待办事项")
    summary_parts.append("─" * 20)
    if tasks:
        for t in tasks[:3]:
            summary_parts.append(f"• {t}")
    else:
        summary_parts.append("• 暂无")
    summary_parts.append("")
    
    summary_parts.append("� AI建议")
    summary_parts.append("─" * 20)
    if isinstance(ai_result, dict) and ai_result.get("success"):
        if ai_result.get("action_items"):
            for item in ai_result.get("action_items", [])[:2]:
                summary_parts.append(f"• {item[:80]}")
        elif ai_result.get("key_insights"):
            for insight in ai_result.get("key_insights", [])[:2]:
                summary_parts.append(f"• {insight[:80]}")
        else:
            summary_parts.append("• 保持积极交流，持续提升协作效率")
    else:
        if participant_count >= 5 and total_messages >= 20:
            summary_parts.append("• 今日讨论活跃，建议保持良好势头")
        elif participant_count >= 3:
            summary_parts.append("• 建议鼓励更多成员分享见解")
        else:
            summary_parts.append("• 建议主动发起话题，带动讨论氛围")
    summary_parts.append("")
    
    summary_parts.append("═" * 20)
    if top_keywords:
        summary_parts.append(f"💡 今日总结：群聊主要围绕「{'、'.join(top_keywords[:3])}」展开，共{participant_count}人参与。")
    else:
        summary_parts.append(f"💡 今日总结：共{participant_count}人参与，产生{total_messages}条消息。")
    summary_parts.append("═" * 20)
    summary_parts.append("")
    
    if total_messages == 0:
        summary_parts.append("🔔 今天有点安静哦，期待大家分享想法和见解！")
    summary_parts.append("")
    summary_parts.append(get_smart_inspiration(top_keywords))
    summary_parts.append("")
    summary_parts.append("💡 AI助手每天为大家总结群聊精华，每天进步一点点，实现复利的力量！")
    summary_parts.append("🌟 鼓励大家多交流、多分享，让智慧在碰撞中涌现！")
    
    return {
        "success": True,
        "content": '\n'.join(summary_parts),
        "ai_used": AI_SUMMARIZER_AVAILABLE and all_messages and ai_result.get("success", False)
    }

def generate_weekly_summary(participant_count, total_messages, topics, top_keywords, decisions, tasks, links, questions, suggestions, participants, chat_name="", date_range="", topic_groups=None, all_messages=None):
    """生成周报格式 - 简洁提炼版（改进版：使用智能总结）"""
    import re
    
    ai_result = {"success": False}
    
    def is_noise_content(text):
        """判断是否是噪音内容"""
        noise_patterns = [
            r'^[好的收到嗯哦]+$',
            r'^[表情图片]+$',
            r'^[\d\s]+$',
            r'^[是的对]+$',
        ]
        for pattern in noise_patterns:
            if re.match(pattern, text):
                return True
        return False
    
    def extract_complete_sentence(text, max_len=150):
        """提取完整句子，不截断"""
        if not text:
            return ""
        
        sentences = re.split(r'([。！？])', text)
        result = ""
        for i in range(0, len(sentences) - 1, 2):
            sentence = sentences[i] + (sentences[i+1] if i+1 < len(sentences) else "")
            if len(result) + len(sentence) <= max_len:
                result += sentence
            else:
                break
        
        if not result and sentences:
            result = sentences[0][:max_len]
        
        return result.strip()
    
    summary_parts = []
    
    if chat_name and date_range:
        summary_parts.append(f"📊 {chat_name} - 群会议纪要周报 ({date_range})")
        summary_parts.append("")
    
    summary_parts.append("═" * 20)
    summary_parts.append(f"📈 本周数据：{total_messages} 条消息 | {participant_count} 人参与 | 日均 {total_messages // 7 if total_messages > 0 else 0} 条")
    summary_parts.append("═" * 20)
    summary_parts.append("")
    
    summary_parts.append("📌 本周重点讨论")
    summary_parts.append("─" * 20)
    
    if AI_SUMMARIZER_AVAILABLE and all_messages:
        ai_result = ai_summarize_messages(all_messages, summary_type="weekly")
        
        if ai_result.get("success"):
            categories = ai_result.get("categories", {})
            
            category_icons = {
                "工作讨论": "💼",
                "项目进展": "📊",
                "问题求助": "❓",
                "经验分享": "💡",
                "决策事项": "✅",
                "其他": "📝"
            }
            
            for category, summary_text in categories.items():
                if category == "其他" or not summary_text:
                    continue
                
                icon = category_icons.get(category, "📌")
                summary_parts.append(f"")
                summary_parts.append(f"{icon} {category}")
                summary_parts.append(summary_text[:300])
            
            key_insights = ai_result.get("key_insights", [])
            if key_insights:
                summary_parts.append(f"")
                summary_parts.append("💡 关键洞察")
                for insight in key_insights[:3]:
                    summary_parts.append(f"• {insight[:120]}")
            
            action_items = ai_result.get("action_items", [])
            if action_items:
                summary_parts.append(f"")
                summary_parts.append("🎯 建议行动")
                for item in action_items[:3]:
                    summary_parts.append(f"• {item[:100]}")
        else:
            summary_parts.append(f"")
            summary_parts.append(ai_result.get("summary", "暂无具体讨论内容"))
    
    elif SMART_SUMMARIZER_AVAILABLE and all_messages:
        smart_result = smart_summarize(all_messages, summary_type="weekly")
        
        category_icons = {
            "工作讨论": "💼",
            "项目进展": "📊",
            "问题求助": "❓",
            "经验分享": "💡",
            "决策事项": "✅",
            "其他": "📝"
        }
        
        for category, data in smart_result.get("categories", {}).items():
            if category == "其他" or data.get("count", 0) < 2:
                continue
            
            icon = category_icons.get(category, "📌")
            summary_parts.append(f"")
            summary_parts.append(f"{icon} {category}")
            
            summary_text = data.get("summary", "")
            if summary_text and summary_text != "暂无具体讨论内容。":
                summary_parts.append(summary_text[:250])
    
    elif topic_groups and len(topic_groups) > 0:
        topic_summaries = {
            '消费理财': {'icon': '�', 'title': '消费理财观念'},
            '制度监管': {'icon': '🏛️', 'title': '制度与文化洞察'},
            '泰国文化': {'icon': '🏛️', 'title': '制度与文化洞察'},
            '个人成长': {'icon': '🧘', 'title': '个人成长与自律'},
            '情绪管理': {'icon': '🙏', 'title': '情绪与人生哲学'},
            '创新思维': {'icon': '💭', 'title': '创新思维启示'},
            '人生哲学': {'icon': '�', 'title': '情绪与人生哲学'},
            '商业管理': {'icon': '💼', 'title': '商业洞察'}
        }
        
        used_titles = set()
        
        for topic_name, topic_contents in topic_groups.items():
            if topic_name == '其他' or len(topic_contents) == 0:
                continue
            
            if topic_name not in topic_summaries:
                continue
            
            topic_info = topic_summaries[topic_name]
            title = topic_info['title']
            
            if title in used_titles:
                continue
            used_titles.add(title)
            
            summary_parts.append(f"")
            summary_parts.append(f"{topic_info['icon']} {title}")
            
            complete_sentences = []
            for content in topic_contents[:15]:
                sentences = re.split(r'[。！？\n]', content)
                for s in sentences:
                    s = s.strip()
                    if len(s) > 10 and not is_noise_content(s):
                        complete_sentences.append(s)
            
            unique_sentences = []
            for sentence in complete_sentences[:8]:
                is_dup = False
                for us in unique_sentences:
                    if sentence[:15] in us or us[:15] in sentence:
                        is_dup = True
                        break
                if not is_dup:
                    unique_sentences.append(sentence)
            
            if unique_sentences:
                summary_text = "。".join(unique_sentences[:3]) + "。"
                summary_parts.append(summary_text[:250])
    
    elif topics:
        unique_topics = []
        for t in topics[:15]:
            is_dup = False
            for ut in unique_topics:
                if t[:15] in ut or ut[:15] in t:
                    is_dup = True
                    break
            if not is_dup and len(unique_topics) < 8:
                unique_topics.append(t)
        
        for topic in unique_topics:
            summary_parts.append(f"• {topic}")
    elif top_keywords:
        for kw in top_keywords[:8]:
            summary_parts.append(f"• {kw}")
    else:
        summary_parts.append("• 暂无具体讨论内容")
    summary_parts.append("")
    
    summary_parts.append("✅ 本周决议")
    summary_parts.append("─" * 20)
    if decisions:
        for d in decisions[:5]:
            summary_parts.append(f"• {d}")
    else:
        summary_parts.append("• 暂无")
    summary_parts.append("")
    
    summary_parts.append("📋 待跟进事项")
    summary_parts.append("─" * 20)
    if tasks:
        for t in tasks[:5]:
            summary_parts.append(f"• {t}")
    else:
        summary_parts.append("• 暂无")
    summary_parts.append("")
    
    summary_parts.append("💡 AI建议与洞察")
    summary_parts.append("─" * 20)
    if isinstance(ai_result, dict) and ai_result.get("success"):
        if ai_result.get("action_items"):
            for item in ai_result.get("action_items", [])[:3]:
                summary_parts.append(f"• {item[:100]}")
        elif ai_result.get("key_insights"):
            for insight in ai_result.get("key_insights", [])[:3]:
                summary_parts.append(f"• {insight[:100]}")
        else:
            summary_parts.append("• 保持积极交流，持续提升团队协作效率")
    else:
        if participant_count >= 5 and total_messages >= 50:
            summary_parts.append("• 团队协作氛围良好，建议保持高频互动")
            summary_parts.append("• 可尝试引入更多深度话题，激发创新思维")
        elif participant_count >= 3:
            summary_parts.append("• 建议鼓励更多成员参与讨论，分享见解")
            summary_parts.append("• 可定期组织主题交流，提升团队凝聚力")
        else:
            summary_parts.append("• 建议主动发起话题，带动群内讨论氛围")
            summary_parts.append("• 分享有价值的内容，激发成员参与热情")
    summary_parts.append("")
    
    summary_parts.append("═" * 20)
    summary_parts.append("📊 本周复盘")
    summary_parts.append("═" * 20)
    
    if participant_count >= 5 and total_messages >= 50:
        summary_parts.append("• 本周交流活跃，团队协作良好")
        summary_parts.append("• 建议继续保持，可尝试更深入的话题讨论")
    elif participant_count >= 3 and total_messages >= 20:
        summary_parts.append("• 本周有一定交流，团队氛围不错")
        summary_parts.append("• 建议鼓励更多成员参与讨论")
    else:
        summary_parts.append("• 本周交流较少，可考虑增加互动话题")
        summary_parts.append("• 建议定期分享有价值的内容，激发讨论")
    
    if len(tasks) > 3:
        summary_parts.append(f"• 有{len(tasks)}项待办事项，建议及时跟进")
    
    summary_parts.append("")
    
    summary_parts.append("═" * 20)
    if top_keywords:
        summary_parts.append(f"🎯 周总结：本周主要围绕「{'、'.join(top_keywords[:3])}」展开讨论。")
    else:
        summary_parts.append(f"🎯 周总结：本周共{participant_count}人参与，产生{total_messages}条消息。")
    summary_parts.append("═" * 20)
    summary_parts.append("")
    
    if total_messages == 0:
        summary_parts.append("🔔 本周有点安静，期待下周大家分享更多见解！")
    summary_parts.append("")
    summary_parts.append(get_smart_inspiration(top_keywords))
    summary_parts.append("")
    summary_parts.append("💡 AI助手每周为大家总结群聊精华，每天进步一点点，实现复利的力量！")
    summary_parts.append("🌟 鼓励大家多交流、多分享，让智慧在碰撞中涌现！")
    
    return {
        "success": True,
        "content": '\n'.join(summary_parts),
        "ai_used": AI_SUMMARIZER_AVAILABLE and all_messages and ai_result.get("success", False)
    }

def generate_monthly_summary(participant_count, total_messages, topics, top_keywords, decisions, tasks, links, questions, suggestions, participants, chat_name="", date_range="", topic_groups=None, all_messages=None):
    """生成月报格式 - 简洁提炼版（改进版：使用智能总结）"""
    import calendar
    import re
    from datetime import datetime
    
    ai_result = {"success": False}
    
    def is_noise_content(text):
        """判断是否是噪音内容"""
        noise_patterns = [
            r'^[好的收到嗯哦]+$',
            r'^[表情图片]+$',
            r'^[\d\s]+$',
            r'^[是的对]+$',
        ]
        for pattern in noise_patterns:
            if re.match(pattern, text):
                return True
        return False
    
    summary_parts = []
    
    now = datetime.now()
    days_in_month = calendar.monthrange(now.year, now.month)[0] if now.month > 1 else calendar.monthrange(now.year - 1, 12)[1]
    
    if chat_name and date_range:
        summary_parts.append(f"📈 {chat_name} - 群会议纪要月报 ({date_range})")
        summary_parts.append("")
    
    summary_parts.append("═" * 20)
    summary_parts.append(f"📈 本月数据：{total_messages} 条消息 | {participant_count} 人参与 | 日均 {total_messages // days_in_month if total_messages > 0 else 0} 条")
    summary_parts.append("═" * 20)
    summary_parts.append("")
    
    summary_parts.append("📌 本月核心话题")
    summary_parts.append("─" * 20)
    
    if AI_SUMMARIZER_AVAILABLE and all_messages:
        ai_result = ai_summarize_messages(all_messages, summary_type="monthly")
        
        if ai_result.get("success"):
            categories = ai_result.get("categories", {})
            
            category_icons = {
                "工作讨论": "💼",
                "项目进展": "📊",
                "问题求助": "❓",
                "经验分享": "💡",
                "决策事项": "✅",
                "其他": "📝"
            }
            
            for category, summary_text in categories.items():
                if category == "其他" or not summary_text:
                    continue
                
                icon = category_icons.get(category, "📌")
                summary_parts.append(f"")
                summary_parts.append(f"{icon} {category}")
                summary_parts.append(summary_text[:300])
            
            key_insights = ai_result.get("key_insights", [])
            if key_insights:
                summary_parts.append(f"")
                summary_parts.append("💡 关键洞察")
                for insight in key_insights[:3]:
                    summary_parts.append(f"• {insight[:120]}")
            
            action_items = ai_result.get("action_items", [])
            if action_items:
                summary_parts.append(f"")
                summary_parts.append("🎯 建议行动")
                for item in action_items[:3]:
                    summary_parts.append(f"• {item[:100]}")
        else:
            summary_parts.append(f"")
            summary_parts.append(ai_result.get("summary", "暂无具体讨论内容"))
    
    elif SMART_SUMMARIZER_AVAILABLE and all_messages:
        smart_result = smart_summarize(all_messages, summary_type="monthly")
        
        category_icons = {
            "工作讨论": "💼",
            "项目进展": "📊",
            "问题求助": "❓",
            "经验分享": "💡",
            "决策事项": "✅",
            "其他": "📝"
        }
        
        for category, data in smart_result.get("categories", {}).items():
            if category == "其他" or data.get("count", 0) < 2:
                continue
            
            icon = category_icons.get(category, "📌")
            summary_parts.append(f"")
            summary_parts.append(f"{icon} {category}")
            
            summary_text = data.get("summary", "")
            if summary_text and summary_text != "暂无具体讨论内容。":
                summary_parts.append(summary_text[:200])
    
    elif topic_groups and len(topic_groups) > 0:
        topic_summaries = {
            '消费理财': {'icon': '�', 'title': '消费理财观念'},
            '制度监管': {'icon': '🏛️', 'title': '制度与文化洞察'},
            '泰国文化': {'icon': '🏛️', 'title': '制度与文化洞察'},
            '个人成长': {'icon': '🧘', 'title': '个人成长与自律'},
            '情绪管理': {'icon': '🙏', 'title': '情绪与人生哲学'},
            '创新思维': {'icon': '💭', 'title': '创新思维启示'},
            '人生哲学': {'icon': '�', 'title': '情绪与人生哲学'},
            '商业管理': {'icon': '💼', 'title': '商业洞察'}
        }
        
        used_titles = set()
        
        for topic_name, topic_contents in topic_groups.items():
            if topic_name == '其他' or len(topic_contents) == 0:
                continue
            
            if topic_name not in topic_summaries:
                continue
            
            topic_info = topic_summaries[topic_name]
            title = topic_info['title']
            
            if title in used_titles:
                continue
            used_titles.add(title)
            
            summary_parts.append(f"")
            summary_parts.append(f"{topic_info['icon']} {title}")
            
            complete_sentences = []
            for content in topic_contents[:10]:
                sentences = re.split(r'[。！？\n]', content)
                for s in sentences:
                    s = s.strip()
                    if len(s) > 15 and not is_noise_content(s):
                        complete_sentences.append(s)
            
            unique_sentences = []
            for sentence in complete_sentences[:5]:
                is_dup = False
                for us in unique_sentences:
                    if sentence[:15] in us or us[:15] in sentence:
                        is_dup = True
                        break
                if not is_dup:
                    unique_sentences.append(sentence)
            
            if unique_sentences:
                summary_text = "。".join(unique_sentences[:2]) + "。"
                summary_parts.append(summary_text[:200])
    
    elif topics:
        unique_topics = []
        for t in topics[:10]:
            is_dup = False
            for ut in unique_topics:
                if t[:15] in ut or ut[:15] in t:
                    is_dup = True
                    break
            if not is_dup and len(unique_topics) < 5:
                unique_topics.append(t)
        
        for topic in unique_topics:
            summary_parts.append(f"• {topic}")
    elif top_keywords:
        for kw in top_keywords[:5]:
            summary_parts.append(f"• {kw}")
    else:
        summary_parts.append("• 暂无具体讨论内容")
    summary_parts.append("")
    
    summary_parts.append("✅ 本月重要决议")
    summary_parts.append("─" * 20)
    if decisions:
        for d in decisions[:5]:
            summary_parts.append(f"• {d}")
    else:
        summary_parts.append("• 暂无")
    summary_parts.append("")
    
    summary_parts.append("📋 待跟进事项")
    summary_parts.append("─" * 20)
    if tasks:
        for t in tasks[:5]:
            summary_parts.append(f"• {t}")
    else:
        summary_parts.append("• 暂无")
    summary_parts.append("")
    
    summary_parts.append("💡 AI建议与洞察")
    summary_parts.append("─" * 20)
    if isinstance(ai_result, dict) and ai_result.get("success"):
        if ai_result.get("action_items"):
            for item in ai_result.get("action_items", [])[:3]:
                summary_parts.append(f"• {item[:100]}")
        elif ai_result.get("key_insights"):
            for insight in ai_result.get("key_insights", [])[:3]:
                summary_parts.append(f"• {insight[:100]}")
        else:
            summary_parts.append("• 保持积极交流，持续提升团队协作效率")
    else:
        avg_daily = total_messages / days_in_month if days_in_month > 0 else 0
        if avg_daily >= 10:
            summary_parts.append("• 本月交流活跃，建议保持良好势头")
            summary_parts.append("• 可尝试更深入的项目讨论，激发创新")
        elif avg_daily >= 5:
            summary_parts.append("• 建议继续鼓励成员分享，提升讨论质量")
            summary_parts.append("• 可定期组织主题交流，增强凝聚力")
        else:
            summary_parts.append("• 建议定期组织话题讨论，激发群智涌现")
            summary_parts.append("• 分享有价值内容，带动讨论氛围")
    summary_parts.append("")
    
    summary_parts.append("═" * 20)
    summary_parts.append("📊 月度复盘")
    summary_parts.append("═" * 20)
    
    avg_daily = total_messages / days_in_month if days_in_month > 0 else 0
    
    if avg_daily >= 10:
        summary_parts.append("• 本月交流非常活跃，团队凝聚力强")
        summary_parts.append("• 建议保持良好势头，可尝试更深入的项目讨论")
    elif avg_daily >= 5:
        summary_parts.append("• 本月交流较为活跃，团队氛围良好")
        summary_parts.append("• 建议继续鼓励成员分享，提升讨论质量")
    elif avg_daily > 0:
        summary_parts.append("• 本月有一定交流，但仍有提升空间")
        summary_parts.append("• 建议定期组织话题讨论，激发群智涌现")
    else:
        summary_parts.append("• 本月交流较少，建议关注团队沟通")
        summary_parts.append("• 可尝试设置固定话题时间，促进交流")
    
    if len(participants) > 0:
        participation_rate = participant_count / len(participants) * 100 if len(participants) > 0 else 0
        if participation_rate < 50:
            summary_parts.append(f"• 参与率为{participation_rate:.0f}%，建议激活沉默成员")
    
    if len(tasks) > 5:
        summary_parts.append(f"• 有{len(tasks)}项待办事项，建议梳理优先级")
    
    summary_parts.append("")
    
    summary_parts.append("═" * 20)
    if top_keywords:
        summary_parts.append(f"🎯 月总结：本月主要围绕「{'、'.join(top_keywords[:5])}」展开讨论。")
    else:
        summary_parts.append(f"🎯 月总结：本月共{participant_count}人参与，产生{total_messages}条消息。")
    summary_parts.append("═" * 20)
    summary_parts.append("")
    
    if total_messages == 0:
        summary_parts.append("🔔 本月有点安静，期待下个月大家分享更多见解！")
    summary_parts.append("")
    summary_parts.append(get_smart_inspiration(top_keywords))
    summary_parts.append("")
    summary_parts.append("🚀 下月展望：期待更多精彩讨论，群智涌现！")
    summary_parts.append("")
    summary_parts.append("💡 AI助手每月为大家总结群聊精华，每天进步一点点，实现复利的力量！")
    summary_parts.append("🌟 鼓励大家多交流、多分享，让智慧在碰撞中涌现！")
    
    return {
        "success": True,
        "content": '\n'.join(summary_parts),
        "ai_used": AI_SUMMARIZER_AVAILABLE and all_messages and ai_result.get("success", False)
    }

def send_message_to_group(token, chat_id, message_content):
    url = "https://open.feishu.cn/open-apis/im/v1/messages"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    params = {
        "receive_id_type": "chat_id"
    }
    
    data = {
        "receive_id": chat_id,
        "msg_type": "text",
        "content": json.dumps({"text": message_content})
    }
    
    try:
        response = requests.post(url, headers=headers, params=params, json=data, timeout=10, proxies=NO_PROXY)
        response.raise_for_status()
        result = response.json()
        
        if result.get("code") == 0:
            return True
        else:
            print(f"❌ 消息发送失败: {result}")
            return False
    except Exception as e:
        print(f"❌ 发送消息时发生错误: {e}")
        return False

def is_system_message(content):
    """判断是否是系统消息"""
    system_keywords = ['This message was recalled', '消息撤回', '**总新闻数**', '**AI分析数**']
    for kw in system_keywords:
        if kw in content:
            return True
    return False

def generate_and_send_summary(token, chat_id, chat_name, summary_type="daily"):
    """生成并发送会议纪要（带完善检查机制 + 幂等保障）"""
    print(f"\n{'='*60}")
    print(f"🚀 处理群：{chat_name}")
    print(f"{'='*60}\n")
    
    now = datetime.now()
    
    if summary_type == "daily":
        start_time = now - timedelta(hours=24)
        end_time = now
        date_key = now.strftime('%Y-%m-%d')
        title = f"📅 每日群会议纪要 ({now.strftime('%Y-%m-%d')})"
        time_desc = "最近24小时"
        date_range = now.strftime('%Y-%m-%d')
    elif summary_type == "weekly":
        monday = now - timedelta(days=now.weekday())
        start_time = monday - timedelta(weeks=1)
        end_time = monday
        date_key = f"{start_time.strftime('%Y-%m-%d')}_{(end_time - timedelta(days=1)).strftime('%Y-%m-%d')}"
        title = f"📊 每周群会议纪要 ({start_time.strftime('%Y-%m-%d')} ~ {(end_time - timedelta(days=1)).strftime('%Y-%m-%d')})"
        time_desc = "上周一至上周日"
        date_range = f"{start_time.strftime('%Y-%m-%d')} ~ {(end_time - timedelta(days=1)).strftime('%Y-%m-%d')}"
    else:
        first_of_month = now.replace(day=1)
        start_time = (first_of_month - timedelta(days=1)).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        end_time = first_of_month
        date_key = start_time.strftime('%Y-%m')
        title = f"📈 每月群会议纪要 ({start_time.strftime('%Y-%m')})"
        time_desc = "上月"
        date_range = start_time.strftime('%Y-%m')
    
    task_id = f"summary_{summary_type}_{date_key}_{chat_id}"
    
    if TASK_STATE_MANAGER_AVAILABLE and _state_manager:
        task_state = _state_manager.get_task_state(task_id)
        if task_state:
            if task_state.get("status") == "completed":
                print(f"⏭️ {chat_name} 的 {summary_type}({date_key}) 已完成，跳过（幂等检查）\n")
                return "already_sent"
            if task_state.get("status") == "running":
                print(f"⏭️ {chat_name} 的 {summary_type}({date_key}) 正在执行中，跳过\n")
                return "running"
        
        _state_manager.create_task(task_id, chat_id, summary_type, date_key)
        _state_manager.update_task_status(task_id, TaskStatus.RUNNING)
    
    if is_already_sent(chat_id, summary_type, date_key):
        print(f"⏭️ {chat_name} 的 {summary_type}({date_key}) 已发送过，跳过\n")
        return "already_sent"
    
    lock_acquired = False
    if INCREMENTAL_FETCHER_AVAILABLE and _lock_manager:
        if not _lock_manager.acquire(task_id, timeout=600):
            print(f"⚠️ {chat_name} 的 {summary_type}({date_key}) 获取锁失败，跳过\n")
            return "locked"
        lock_acquired = True
        print(f"🔒 已获取分布式锁: {task_id}\n")
    
    try:
        if INCREMENTAL_FETCHER_AVAILABLE and _rate_limiter:
            _rate_limiter.wait_if_needed()
        
        members_map = get_group_members(token, chat_id)
        print(f"✅ 获取到 {len(members_map)} 位群成员\n")
        
        start_ts = int(start_time.timestamp() * 1000)
        end_ts = int(end_time.timestamp() * 1000)
        
        messages = get_messages_by_time_range(token, chat_id, start_ts, end_ts)
        print(f"✅ 获取到 {len(messages)} 条消息（{time_desc}）\n")
        
        records = extract_chat_records(messages, members_map)
        print(f"✅ 提取到 {len(records)} 条文本消息\n")
        
        if SKIP_EMPTY_GROUPS and len(records) < MIN_MESSAGE_COUNT:
            print(f"⏭️ 消息数量({len(records)})少于阈值({MIN_MESSAGE_COUNT})，跳过\n")
            return "skipped"
        
        if SKIP_SYSTEM_ONLY:
            human_messages = [r for r in records if not is_system_message(r['content'])]
            if len(human_messages) < MIN_MESSAGE_COUNT:
                print(f"⏭️ 人工消息太少({len(human_messages)}条)，跳过\n")
                return "skipped"
        
        chat_text = format_chat_text(records)
        
        ai_summary_result = local_summarize(chat_text, summary_type, chat_name, date_range, len(records))
        
        if not ai_summary_result:
            print("❌ 总结失败\n")
            return False
        
        if isinstance(ai_summary_result, dict):
            if not ai_summary_result.get("success"):
                print("❌ 总结生成失败，不发送消息\n")
                return False
            
            if AI_SUMMARIZER_AVAILABLE and not ai_summary_result.get("ai_used"):
                print("⚠️ AI总结失败，使用备用总结方式\n")
            
            ai_summary = ai_summary_result.get("content", "")
        else:
            ai_summary = ai_summary_result
        
        if not ai_summary or len(ai_summary) < 50:
            print("❌ 总结内容过短或为空，不发送消息\n")
            return False
        
        if "success" in ai_summary and "content" in ai_summary:
            print("❌ 检测到字典格式错误，不发送消息\n")
            return False
        
        print("✅ 总结成功！\n")
        
        footer_parts = []
        if SHOW_GENERATE_TIME:
            footer_parts.append(f"⏰ 生成时间：{now.strftime('%Y-%m-%d %H:%M:%S')}")
        if SHOW_BOT_SIGNATURE:
            footer_parts.append(f"🤖 由{BOT_NAME}机器人自动生成")
        
        footer = "\n".join(footer_parts) if footer_parts else ""
        
        message_content = f"""{ai_summary}

{footer}
""".strip()
        
        if SEND_CHECK_SYSTEM_AVAILABLE:
            checker = SendCheckSystem(SEND_RECORDS_FILE, CONTENT_VERSION)
            is_valid, reason = checker.validate_content_format(message_content, summary_type)
            if not is_valid:
                print(f"❌ 内容格式验证失败: {reason}\n")
                return False
            print(f"✅ 内容格式验证通过\n")
        
        print("📤 发送会议纪要到群里...")
        if send_message_to_group(token, chat_id, message_content):
            if TASK_STATE_MANAGER_AVAILABLE and _state_manager:
                _state_manager.update_task_status(task_id, TaskStatus.COMPLETED)
            if SEND_CHECK_SYSTEM_AVAILABLE:
                checker = SendCheckSystem(SEND_RECORDS_FILE, CONTENT_VERSION)
                checker.record_send(chat_id, summary_type, date_key, chat_name, message_content, success=True)
            else:
                mark_as_sent(chat_id, summary_type, date_key, chat_name)
            print(f"\n🎉 群 {chat_name} 的会议纪要发送成功！\n")
            return True
        else:
            if TASK_STATE_MANAGER_AVAILABLE and _state_manager:
                _state_manager.update_task_status(task_id, TaskStatus.FAILED, error_msg="发送失败")
            if SEND_CHECK_SYSTEM_AVAILABLE:
                checker = SendCheckSystem(SEND_RECORDS_FILE, CONTENT_VERSION)
                checker.record_send(chat_id, summary_type, date_key, chat_name, message_content, success=False, error_msg="发送失败")
            print(f"\n❌ 群 {chat_name} 的会议纪要发送失败\n")
            return False
    
    except Exception as e:
        print(f"❌ 处理异常: {e}\n")
        if TASK_STATE_MANAGER_AVAILABLE and _state_manager:
            _state_manager.update_task_status(task_id, TaskStatus.FAILED, error_msg=str(e))
        return False
    
    finally:
        if lock_acquired and INCREMENTAL_FETCHER_AVAILABLE and _lock_manager:
            _lock_manager.release(task_id)
            print(f"🔓 已释放分布式锁: {task_id}\n")

def send_daily_summary():
    """发送每日会议纪要（支持并发处理）"""
    if not is_valid_send_time():
        return
    now = datetime.now()
    
    clean_old_records()
    
    print("\n" + "="*60)
    print(f"📅 开始发送每日会议纪要 - {now.strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60 + "\n")
    
    token = get_feishu_token()
    if not token:
        print("❌ Token获取失败")
        return
    print("✅ Token获取成功\n")
    
    groups = get_bot_groups(token)
    print(f"✅ 机器人共在 {len(groups)} 个群中\n")
    
    filtered_groups = filter_groups(groups)
    print(f"✅ 根据配置过滤后，将发送到 {len(filtered_groups)} 个群\n")
    
    if CONCURRENT_PROCESSOR_AVAILABLE and len(filtered_groups) > 1:
        print("🚀 使用并发处理模式\n")
        
        monitor = PerformanceMonitor()
        monitor.start_timer("total")
        
        def process_single_group(group):
            chat_id = group.get("chat_id")
            chat_name = group.get("name", "未知群")
            return generate_and_send_summary(token, chat_id, chat_name, "daily")
        
        results = run_concurrent_tasks(
            [lambda g=group: process_single_group(g) for group in filtered_groups],
            max_workers=5
        )
        
        monitor.end_timer("total")
        
        success_count = sum(1 for r in results if r == True)
        skip_count = sum(1 for r in results if r == "skipped")
        already_sent_count = sum(1 for r in results if r == "already_sent")
        fail_count = len(results) - success_count - skip_count - already_sent_count
        
        print(monitor.get_report())
    else:
        print("📝 使用串行处理模式\n")
        
        success_count = 0
        skip_count = 0
        fail_count = 0
        already_sent_count = 0
        
        for group in filtered_groups:
            chat_id = group.get("chat_id")
            chat_name = group.get("name", "未知群")
            
            result = generate_and_send_summary(token, chat_id, chat_name, "daily")
            if result == True:
                success_count += 1
            elif result == "skipped":
                skip_count += 1
            elif result == "already_sent":
                already_sent_count += 1
            else:
                fail_count += 1
    
    print("\n" + "="*60)
    print(f"📊 每日会议纪要发送完成")
    print(f"   ✅ 成功：{success_count} 个群")
    print(f"   ⏭️ 跳过：{skip_count} 个群")
    print(f"   📝 已发送：{already_sent_count} 个群")
    print(f"   ❌ 失败：{fail_count} 个群")
    print("="*60 + "\n")

def is_sunday():
    """检查今天是否是周日"""
    return datetime.now().weekday() == 6

def is_month_end():
    """检查今天是否是月末最后一天"""
    now = datetime.now()
    if now.month == 12:
        next_month = now.replace(year=now.year + 1, month=1, day=1)
    else:
        next_month = now.replace(month=now.month + 1, day=1)
    last_day = (next_month - timedelta(days=1)).day
    return now.day == last_day

def send_weekly_summary():
    """发送周报"""
    if not is_valid_send_time():
        return
    now = datetime.now()
    
    clean_old_records()
    
    print("\n" + "="*60)
    print(f"📊 开始发送周报 - {now.strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60 + "\n")
    
    token = get_feishu_token()
    if not token:
        print("❌ Token获取失败")
        return
    print("✅ Token获取成功\n")
    
    groups = get_bot_groups(token)
    print(f"✅ 机器人共在 {len(groups)} 个群中\n")
    
    filtered_groups = filter_groups(groups)
    print(f"✅ 根据配置过滤后，将发送到 {len(filtered_groups)} 个群\n")
    
    success_count = 0
    skip_count = 0
    fail_count = 0
    already_sent_count = 0
    
    for group in filtered_groups:
        chat_id = group.get("chat_id")
        chat_name = group.get("name", "未知群")
        
        result = generate_and_send_summary(token, chat_id, chat_name, "weekly")
        if result == True:
            success_count += 1
        elif result == "skipped":
            skip_count += 1
        elif result == "already_sent":
            already_sent_count += 1
        else:
            fail_count += 1
    
    print("\n" + "="*60)
    print(f"📊 周报发送完成")
    print(f"   ✅ 成功：{success_count} 个群")
    print(f"   ⏭️ 跳过：{skip_count} 个群")
    print(f"   📝 已发送：{already_sent_count} 个群")
    print(f"   ❌ 失败：{fail_count} 个群")
    print("="*60 + "\n")

def send_monthly_summary():
    """发送月报"""
    if not is_valid_send_time():
        return
    now = datetime.now()
    
    clean_old_records()
    
    print("\n" + "="*60)
    print(f"📈 开始发送月报 - {now.strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60 + "\n")
    
    token = get_feishu_token()
    if not token:
        print("❌ Token获取失败")
        return
    print("✅ Token获取成功\n")
    
    groups = get_bot_groups(token)
    print(f"✅ 机器人共在 {len(groups)} 个群中\n")
    
    filtered_groups = filter_groups(groups)
    print(f"✅ 根据配置过滤后，将发送到 {len(filtered_groups)} 个群\n")
    
    success_count = 0
    skip_count = 0
    fail_count = 0
    already_sent_count = 0
    
    for group in filtered_groups:
        chat_id = group.get("chat_id")
        chat_name = group.get("name", "未知群")
        
        result = generate_and_send_summary(token, chat_id, chat_name, "monthly")
        if result == True:
            success_count += 1
        elif result == "skipped":
            skip_count += 1
        elif result == "already_sent":
            already_sent_count += 1
        else:
            fail_count += 1
    
    print("\n" + "="*60)
    print(f"📊 月报发送完成")
    print(f"   ✅ 成功：{success_count} 个群")
    print(f"   ⏭️ 跳过：{skip_count} 个群")
    print(f"   📝 已发送：{already_sent_count} 个群")
    print(f"   ❌ 失败：{fail_count} 个群")
    print("="*60 + "\n")

def run_scheduler():
    """运行定时任务调度器"""
    print("\n" + "="*60)
    print("🤖 群会议纪要AI机器人启动（分时段版）")
    print("="*60)
    
    if TEST_MODE:
        print(f"\n🧪 【测试模式】已启用")
        print(f"   测试群：{TEST_GROUP}")
        print(f"   ⚠️ 所有消息只会发送到测试群，不会打扰其他群")
    
    print(f"\n⏰ 定时任务设置（分时段发送）:")
    print(f"   - 每天 {DAILY_TIME} 发送日报（晚上）")
    print(f"   - 每周一 {WEEKLY_TIME} 发送周报（早上）")
    print(f"   - 每月最后一天 {MONTHLY_TIME} 发送月报（早上）")
    print(f"\n📊 分时段优势：")
    print(f"   • 日报晚上发，周报/月报早上发，完全避免冲突")
    print(f"   • 用户不会同时收到多条消息")
    print(f"   • 时间有规律，用户体验好")
    print(f"\n📋 发送配置:")
    print(f"   - 发送模式：{SEND_MODE}")
    print(f"   - 最小消息数：{MIN_MESSAGE_COUNT}")
    print(f"   - 跳过无消息群：{SKIP_EMPTY_GROUPS}")
    print(f"   - 调试模式：{DEBUG_MODE}")
    print(f"\n🔍 漏发检查机制：")
    print(f"   • 启动时自动检查漏发报告")
    print(f"   • 发现漏发自动补发")
    print("\n" + "="*60 + "\n")
    
    print("🔍 启动时检查漏发会议纪要...")
    send_missed_summaries()
    print("")
    
    schedule.every().day.at(DAILY_TIME).do(send_daily_summary)
    schedule.every().monday.at(WEEKLY_TIME).do(send_weekly_summary)
    
    print("✅ 定时任务已设置")
    print("📝 按 Ctrl+C 停止服务\n")
    
    while True:
        now = datetime.now()
        if is_month_end() and now.hour == int(MONTHLY_TIME.split(":")[0]) and now.minute == int(MONTHLY_TIME.split(":")[1]):
            send_monthly_summary()
            time.sleep(60)
        
        schedule.run_pending()
        time.sleep(60)

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--now":
        print("🚀 立即执行模式")
        send_daily_summary()
    else:
        run_scheduler()

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""群消息统计机器人 - 多群定时发送服务（分时段版 + 自动同步 + 日志记录）"""

import sys
import os
# 设置UTF-8编码
sys.stdout = open(sys.stdout.fileno(), mode='w', encoding='utf-8', buffering=1)
sys.stderr = open(sys.stderr.fileno(), mode='w', encoding='utf-8', buffering=1)

import time
import schedule
import requests
import json
import logging
from datetime import datetime, timedelta
import calendar

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import *
from user_name_cache import UserNameCache

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

user_name_cache = UserNameCache()

CONTENT_VERSION = "2.0"

LOG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
os.makedirs(LOG_DIR, exist_ok=True)

LOG_FILE = os.path.join(LOG_DIR, f"stats_bot_{datetime.now().strftime('%Y%m')}.log")

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE, encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

NO_PROXY = {}

STATS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "stats_data.json")

SEND_RECORDS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "send_records.json")

_state_manager = None
_lock_manager = None
_rate_limiter = None

if TASK_STATE_MANAGER_AVAILABLE:
    _state_manager = TaskStateManager()
    logger.info("✅ 幂等任务管理器已启用")

if INCREMENTAL_FETCHER_AVAILABLE:
    _lock_manager = DistributedLock()
    _rate_limiter = RateLimiter(max_requests=20, window_seconds=1)
    logger.info("✅ 分布式锁和API限流器已启用")

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
        logger.error(f"保存发送记录失败: {e}")

def is_already_sent(group_id, report_type, date_key):
    records = load_send_records()
    record_key = f"{group_id}_{report_type}_{date_key}"
    return record_key in records

def mark_as_sent(group_id, report_type, date_key, group_name):
    records = load_send_records()
    record_key = f"{group_id}_{report_type}_{date_key}"
    records[record_key] = {
        "group_name": group_name,
        "sent_time": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        "report_type": report_type,
        "date_key": date_key
    }
    save_send_records(records)
    logger.info(f"📝 已记录发送: {group_name} - {report_type} - {date_key}")

def clean_old_records():
    records = load_send_records()
    now = datetime.now()
    keys_to_remove = []
    
    for key, value in records.items():
        sent_time = datetime.strptime(value.get("sent_time", ""), '%Y-%m-%d %H:%M:%S')
        days_diff = (now - sent_time).days
        if days_diff > 35:
            keys_to_remove.append(key)
    
    for key in keys_to_remove:
        del records[key]
    
    if keys_to_remove:
        save_send_records(records)
        logger.info(f"🧹 已清理 {len(keys_to_remove)} 条过期发送记录")

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
        logger.warning(f"⚠️ 当前时间 {now.strftime('%H:%M')} 不在发送时间范围内（08:30-23:00），跳过发送")
        return False
    if hour >= 23:
        logger.warning(f"⚠️ 当前时间 {now.strftime('%H:%M')} 不在发送时间范围内（08:30-23:00），跳过发送")
        return False
    return True

def check_missed_reports():
    """检查是否有漏发的报告，返回需要补发的报告列表"""
    missed = []
    now = datetime.now()
    records = load_send_records()
    
    yesterday = now - timedelta(days=1)
    yesterday_key = yesterday.strftime('%Y-%m-%d')
    
    filtered_groups = filter_groups()
    for group_name, group_config in filtered_groups:
        group_id = group_config["id"]
        record_key = f"{group_id}_日报_{yesterday_key}"
        if record_key not in records:
            missed.append({
                "type": "日报",
                "date_key": yesterday_key,
                "group_name": group_name,
                "group_id": group_id,
                "reason": "昨日日报未发送"
            })
    
    if now.weekday() == 0 or now.weekday() == 1:
        monday = now - timedelta(days=now.weekday())
        last_week_start = monday - timedelta(weeks=1)
        last_week_end = monday
        week_key = f"{last_week_start.strftime('%Y-%m-%d')}_{(last_week_end - timedelta(days=1)).strftime('%Y-%m-%d')}"
        
        for group_name, group_config in filtered_groups:
            group_id = group_config["id"]
            record_key = f"{group_id}_周报_{week_key}"
            if record_key not in records:
                missed.append({
                    "type": "周报",
                    "date_key": week_key,
                    "group_name": group_name,
                    "group_id": group_id,
                    "reason": "上周周报未发送"
                })
    
    if now.day <= 3:
        first_of_month = now.replace(day=1)
        last_month_start = (first_of_month - timedelta(days=1)).replace(day=1)
        month_key = last_month_start.strftime('%Y-%m')
        
        for group_name, group_config in filtered_groups:
            group_id = group_config["id"]
            record_key = f"{group_id}_月报_{month_key}"
            if record_key not in records:
                missed.append({
                    "type": "月报",
                    "date_key": month_key,
                    "group_name": group_name,
                    "group_id": group_id,
                    "reason": "上月月报未发送"
                })
    
    return missed

def send_missed_reports():
    """补发漏发的报告"""
    if not is_valid_send_time():
        return
    
    missed = check_missed_reports()
    
    if not missed:
        logger.info("✅ 无漏发报告，所有报告已正常发送")
        return
    
    logger.info(f"⚠️ 发现 {len(missed)} 个漏发报告，开始补发...")
    logger.info("=" * 60)
    
    token = get_tenant_token()
    if not token:
        logger.error("❌ Token 获取失败，无法补发")
        return
    
    groups_dict = sync_groups_from_api(token)
    
    success_count = 0
    fail_count = 0
    
    for item in missed:
        logger.info(f"🔄 补发: {item['group_name']} - {item['type']} ({item['reason']})")
        
        try:
            group_config = None
            for g_name, g_config in groups_dict.items():
                if g_config.get("id") == item["group_id"]:
                    group_config = g_config
                    break
            
            if not group_config:
                logger.warning(f"⚠️ 未找到群配置: {item['group_name']}")
                continue
            
            if item["type"] == "日报":
                result = process_group(token, item["group_name"], group_config, "日报", filter_messages_by_day, 1)
            elif item["type"] == "周报":
                result = process_group(token, item["group_name"], group_config, "周报", filter_messages_by_week, 1)
            else:
                result = process_group(token, item["group_name"], group_config, "月报", filter_messages_by_month, 1)
            
            if result == True:
                success_count += 1
            else:
                fail_count += 1
                
        except Exception as e:
            logger.error(f"❌ 补发失败: {item['group_name']} - {e}")
            fail_count += 1
    
    logger.info("=" * 60)
    logger.info(f"📊 补发完成: ✅ {success_count} ❌ {fail_count}")

def load_stats():
    if os.path.exists(STATS_FILE):
        try:
            with open(STATS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            pass
    return {
        "total_sends": 0,
        "success_sends": 0,
        "fail_sends": 0,
        "last_send_time": None,
        "groups": {}
    }

def save_stats(stats):
    try:
        with open(STATS_FILE, 'w', encoding='utf-8') as f:
            json.dump(stats, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"保存统计数据失败: {e}")

def update_stats(group_name, success, report_type):
    stats = load_stats()
    stats["total_sends"] += 1
    if success:
        stats["success_sends"] += 1
    else:
        stats["fail_sends"] += 1
    stats["last_send_time"] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    if group_name not in stats["groups"]:
        stats["groups"][group_name] = {"total": 0, "success": 0, "fail": 0}
    stats["groups"][group_name]["total"] += 1
    if success:
        stats["groups"][group_name]["success"] += 1
    else:
        stats["groups"][group_name]["fail"] += 1
    
    save_stats(stats)

PERSISTENT_GROUPS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "persistent_groups.json")

def is_monday():
    return datetime.now().weekday() == 0

def is_first_day_of_month():
    return datetime.now().day == 1

def get_tenant_token():
    url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
    data = {"app_id": FEISHU_APP_ID, "app_secret": FEISHU_APP_SECRET}
    resp = requests.post(url, json=data, proxies=NO_PROXY).json()
    return resp.get("tenant_access_token")

def get_bot_groups(token):
    """获取机器人所在的所有群列表"""
    url = "https://open.feishu.cn/open-apis/im/v1/chats"
    headers = {"Authorization": f"Bearer {token}"}
    params = {"page_size": 100}
    
    try:
        resp = requests.get(url, headers=headers, params=params, proxies=NO_PROXY).json()
        if resp.get("code") == 0:
            return resp.get("data", {}).get("items", [])
        else:
            logger.warning(f"获取群列表失败: {resp}")
            return []
    except Exception as e:
        logger.error(f"获取群列表时发生错误: {e}")
        return []

def sync_groups_from_api(token):
    """从API获取所有群组（动态模式）"""
    api_groups = get_bot_groups(token)
    
    result_groups = {}
    for group in api_groups:
        chat_id = group.get("chat_id")
        name = group.get("name", "未知群")
        
        if name not in BLACKLIST_GROUPS:
            result_groups[name] = {
                "id": chat_id,
                "enabled": True,
                "auto_added": True
            }
    
    logger.info(f"📋 动态获取到 {len(result_groups)} 个群（排除 {len(BLACKLIST_GROUPS)} 个测试群）")
    
    return result_groups

def get_group_members(token, group_id):
    url = f"https://open.feishu.cn/open-apis/im/v1/chats/{group_id}/members"
    headers = {"Authorization": f"Bearer {token}"}
    params = {"page_size": 100}
    
    all_members = []
    page_token = None
    
    while True:
        if page_token:
            params["page_token"] = page_token
        
        resp = requests.get(url, headers=headers, params=params, proxies=NO_PROXY).json()
        
        if resp.get("code") != 0:
            break
        
        data = resp.get("data", {})
        members = data.get("items", [])
        all_members.extend(members)
        
        if not data.get("has_more", False):
            break
        
        page_token = data.get("page_token")
    
    return all_members

def get_all_messages(token, group_id):
    url = "https://open.feishu.cn/open-apis/im/v1/messages"
    headers = {"Authorization": f"Bearer {token}"}
    
    all_messages = []
    page_token = None
    
    while True:
        params = {
            "container_id_type": "chat",
            "container_id": group_id,
            "page_size": "50"
        }
        
        if page_token:
            params["page_token"] = page_token
        
        resp = requests.get(url, params=params, headers=headers, proxies=NO_PROXY).json()
        
        if resp.get("code") != 0:
            break
        
        data = resp.get("data", {})
        messages = data.get("items", [])
        all_messages.extend(messages)
        
        if not data.get("has_more", False):
            break
        
        page_token = data.get("page_token")
    
    return all_messages

def filter_messages_by_day(messages, days_ago=1):
    now = datetime.now()
    target_date = now - timedelta(days=days_ago)
    start_of_day = target_date.replace(hour=0, minute=0, second=0, microsecond=0)
    end_of_day = start_of_day + timedelta(days=1)
    
    start_ts = int(start_of_day.timestamp() * 1000)
    end_ts = int(end_of_day.timestamp() * 1000)
    
    filtered = []
    for msg in messages:
        create_time = int(msg.get("create_time", 0))
        if start_ts <= create_time < end_ts:
            filtered.append(msg)
    
    return filtered, start_of_day.strftime("%Y-%m-%d")

def filter_messages_by_week(messages, weeks_ago=1):
    now = datetime.now()
    monday = now - timedelta(days=now.weekday())
    start_of_week = monday - timedelta(weeks=weeks_ago)
    end_of_week = start_of_week + timedelta(weeks=1)
    
    start_ts = int(start_of_week.timestamp() * 1000)
    end_ts = int(end_of_week.timestamp() * 1000)
    
    filtered = []
    for msg in messages:
        create_time = int(msg.get("create_time", 0))
        if start_ts <= create_time < end_ts:
            filtered.append(msg)
    
    return filtered, start_of_week.strftime("%Y-%m-%d"), end_of_week.strftime("%Y-%m-%d")

def filter_messages_by_month(messages, months_ago=1):
    now = datetime.now()
    first_day = now.replace(day=1) - timedelta(days=0)
    if months_ago > 0:
        for _ in range(months_ago):
            first_day = first_day.replace(day=1) - timedelta(days=1)
            first_day = first_day.replace(day=1)
    
    next_month = first_day.replace(day=28) + timedelta(days=4)
    next_month = next_month.replace(day=1)
    
    start_ts = int(first_day.timestamp() * 1000)
    end_ts = int(next_month.timestamp() * 1000)
    
    filtered = []
    for msg in messages:
        create_time = int(msg.get("create_time", 0))
        if start_ts <= create_time < end_ts:
            filtered.append(msg)
    
    return filtered, first_day.strftime("%Y-%m")

def count_messages(messages, members):
    member_map = {m.get("member_id"): m.get("name") for m in members}
    
    user_name_cache.update_from_members(members)
    
    count = {}
    for msg in messages:
        sender_info = msg.get("sender", {})
        sender_id = sender_info.get("id", "")
        sender_type = sender_info.get("sender_type", "")
        
        if not sender_id or sender_type == "app" or sender_id.startswith("cli_"):
            continue
        
        sender_name = member_map.get(sender_id)
        if not sender_name:
            sender_name = user_name_cache.get_name(sender_id)
            if not sender_name:
                if sender_id.startswith("ou_"):
                    sender_name = f"已退群用户({sender_id[-8:]})"
                else:
                    sender_name = "未知"
        
        if "机器人" in sender_name or sender_name.startswith("cli_"):
            continue
        
        if sender_name in CEO_LIST:
            continue
            
        count[sender_name] = count.get(sender_name, 0) + 1
    
    return count

def send_message_to_group(token, group_id, text):
    url = "https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type=chat_id"
    headers = {"Authorization": f"Bearer {token}"}
    
    data = {
        "receive_id": group_id,
        "msg_type": "text",
        "content": json.dumps({"text": text})
    }
    
    resp = requests.post(url, json=data, headers=headers, proxies=NO_PROXY).json()
    return resp

def generate_report(count, title, date_range, group_name, members, report_type="daily"):
    all_member_names = {m.get("name", "未知") for m in members if m.get("name") not in CEO_LIST}
    
    full_count = {}
    for name in all_member_names:
        full_count[name] = count.get(name, 0)
    
    sorted_count = sorted(full_count.items(), key=lambda x: x[1], reverse=True)
    
    total = sum(count.values())
    active_count = sum(1 for _, cnt in sorted_count if cnt > 0)
    total_members = len(all_member_names)
    active_rate = (active_count / total_members * 100) if total_members > 0 else 0
    
    if report_type == "daily":
        return generate_daily_report(count, title, date_range, group_name, sorted_count, total, active_count, total_members, active_rate)
    elif report_type == "weekly":
        return generate_weekly_report(count, title, date_range, group_name, sorted_count, total, active_count, total_members, active_rate)
    else:
        return generate_monthly_report(count, title, date_range, group_name, sorted_count, total, active_count, total_members, active_rate)

def generate_daily_report(count, title, date_range, group_name, sorted_count, total, active_count, total_members, active_rate):
    report = f"📊 {group_name} - 群消息日报 ({date_range})\n\n"
    
    report += f"📈 今日数据：{total} 条消息 | {active_count}/{total_members} 人活跃 ({active_rate:.0f}%)\n\n"
    
    if total > 0:
        top3 = sorted_count[:3]
        report += "🏆 今日之星："
        medals = ["🥇", "🥈", "🥉"]
        star_list = [f"{medals[i]}{name}({cnt}条)" for i, (name, cnt) in enumerate(top3) if cnt > 0]
        report += " ".join(star_list) + "\n\n"
    
    report += "📋 全员榜单：\n"
    for i, (name, cnt) in enumerate(sorted_count, 1):
        if cnt > 0:
            emoji = "🔥" if cnt >= 10 else "💬" if cnt >= 5 else "💭"
            report += f"   {i}. {name}: {cnt}条 {emoji}\n"
        else:
            report += f"   {i}. {name}: 0条 💤\n"
    
    # 激励语
    if active_rate >= 80:
        report += "\n🌟 今日群氛围火热！大家交流积极，群智涌现！\n"
    elif active_rate >= 50:
        report += "\n💪 今日交流不错！继续保持，期待更多伙伴加入讨论！\n"
    elif active_rate > 0:
        report += "\n📢 欢迎更多伙伴参与交流，每一条消息都是智慧的火花！\n"
    else:
        report += "\n🔔 今天有点安静哦，期待大家分享想法和见解！\n"
    
    # 💌 期待你的声音
    silent_members = [name for name, cnt in sorted_count if cnt == 0]
    if silent_members:
        report += f"\n💌 期待你的声音：{', '.join(silent_members[:3])}\n"
        report += "   你的想法对我们很重要，期待听到你的分享！\n"
    
    report += "\n🌈 这里是我们灵感碰撞的地方！💪 勇于表达，让群智涌现！\n"
    
    footer_parts = []
    if SHOW_GENERATE_TIME:
        footer_parts.append(f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    if SHOW_BOT_SIGNATURE:
        footer_parts.append(f"🤖 {BOT_NAME}")
    
    if footer_parts:
        report += " | ".join(footer_parts) + "\n"
    
    return report

def generate_weekly_report(count, title, date_range, group_name, sorted_count, total, active_count, total_members, active_rate):
    report = f"📊 {group_name} - 群消息周报 ({date_range})\n\n"
    
    report += f"📈 本周数据：{total} 条消息 | {active_count}/{total_members} 人活跃 ({active_rate:.0f}%) | 日均 {total // 7 if total > 0 else 0} 条\n\n"
    
    if total > 0:
        top5 = [x for x in sorted_count[:5] if x[1] > 0]
        if top5:
            report += "🏆 本周贡献榜："
            medals = ["🥇", "🥈", "🥉", "🏅", "🏅"]
            star_list = [f"{medals[i]}{name}({cnt}条)" for i, (name, cnt) in enumerate(top5)]
            report += " ".join(star_list) + "\n\n"
    
    report += "📋 全员周榜：\n"
    for i, (name, cnt) in enumerate(sorted_count, 1):
        if cnt > 0:
            avg_daily = cnt / 7
            emoji = "🔥" if avg_daily >= 5 else "💬" if avg_daily >= 2 else "💭"
            report += f"   {i}. {name}: {cnt}条 (日均{avg_daily:.1f}) {emoji}\n"
        else:
            report += f"   {i}. {name}: 0条 💤\n"
    
    # 激励语
    if active_rate >= 80:
        report += "\n🌟 本周群氛围超棒！团队协作紧密，群智涌现！\n"
    elif active_rate >= 50:
        report += "\n💪 本周交流活跃！感谢每一位贡献者，下周继续加油！\n"
    elif active_rate > 0:
        report += "\n📢 期待更多伙伴加入讨论，思想的碰撞创造价值！\n"
    else:
        report += "\n🔔 本周有点安静，下周期待大家分享更多见解！\n"
    
    # 💌 期待你的声音
    silent_members = [name for name, cnt in sorted_count if cnt == 0]
    if silent_members:
        report += f"\n💌 期待你的声音：{', '.join(silent_members[:3])}\n"
        report += "   本周没有看到你的发言，期待下周听到你的想法！\n"
    
    # 🎉 感谢活跃成员
    active_members = [name for name, cnt in sorted_count[:3] if cnt > 0]
    if active_members:
        report += f"\n🎉 特别感谢：{', '.join(active_members)}\n"
        report += "   你们的分享让群更有价值！\n"
    
    report += "\n🌈 这里是我们灵感碰撞的地方！💪 勇于表达，让群智涌现！\n"
    
    footer_parts = []
    if SHOW_GENERATE_TIME:
        footer_parts.append(f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    if SHOW_BOT_SIGNATURE:
        footer_parts.append(f"🤖 {BOT_NAME}")
    
    if footer_parts:
        report += " | ".join(footer_parts) + "\n"
    
    return report

def generate_monthly_report(count, title, date_range, group_name, sorted_count, total, active_count, total_members, active_rate):
    report = f"📊 {group_name} - 群消息月报 ({date_range})\n\n"
    
    import calendar
    now = datetime.now()
    days_in_month = calendar.monthrange(now.year, now.month)[0] if now.month > 1 else calendar.monthrange(now.year - 1, 12)[1]
    
    report += f"📈 本月数据：{total} 条消息 | {active_count}/{total_members} 人活跃 ({active_rate:.0f}%) | 日均 {total // days_in_month if total > 0 else 0} 条\n\n"
    
    if total > 0:
        top5 = [x for x in sorted_count[:5] if x[1] > 0]
        if top5:
            report += "🏆 本月贡献榜："
            medals = ["🥇", "🥈", "🥉", "🏅", "🏅"]
            star_list = [f"{medals[i]}{name}({cnt}条)" for i, (name, cnt) in enumerate(top5)]
            report += " ".join(star_list) + "\n\n"
    
    report += "📋 全员月榜：\n"
    for i, (name, cnt) in enumerate(sorted_count, 1):
        if cnt > 0:
            avg_daily = cnt / days_in_month
            emoji = "🔥" if avg_daily >= 3 else "💬" if avg_daily >= 1 else "💭"
            report += f"   {i}. {name}: {cnt}条 (日均{avg_daily:.1f}) {emoji}\n"
        else:
            report += f"   {i}. {name}: 0条 💤\n"
    
    # 激励语
    if active_rate >= 80:
        report += "\n🌟 本月群氛围极佳！团队协作高效，群智涌现！\n"
    elif active_rate >= 50:
        report += "\n💪 本月交流活跃！团队凝聚力强，继续保持！\n"
    elif active_rate > 0:
        report += "\n📢 期待更多伙伴参与，每一条消息都是智慧的火花！\n"
    else:
        report += "\n🔔 本月有点安静，期待下月大家分享更多见解！\n"
    
    # 💌 期待你的声音
    silent_members = [name for name, cnt in sorted_count if cnt == 0]
    if silent_members:
        report += f"\n💌 期待你的声音：{', '.join(silent_members[:3])}\n"
        report += "   本月没有看到你的发言，期待下月听到你的想法！\n"
    
    # 🎉 感谢活跃成员
    active_members = [name for name, cnt in sorted_count[:5] if cnt > 0]
    if active_members:
        report += f"\n🎉 特别感谢：{', '.join(active_members)}\n"
        report += "   你们的分享让群更有价值，感谢你们的付出！\n"
    
    report += "\n🌈 这里是我们灵感碰撞的地方！💪 勇于表达，让群智涌现！\n"
    
    footer_parts = []
    if SHOW_GENERATE_TIME:
        footer_parts.append(f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    if SHOW_BOT_SIGNATURE:
        footer_parts.append(f"🤖 {BOT_NAME}")
    
    if footer_parts:
        report += " | ".join(footer_parts) + "\n"
    
    return report

def send_with_retry(send_func, report_type, group_name):
    for attempt in range(MAX_RETRIES):
        try:
            logger.info(f"🔄 [{group_name}] {report_type} 发送尝试 {attempt + 1}/{MAX_RETRIES}...")
            result = send_func()
            if result:
                logger.info(f"✅ [{group_name}] {report_type} 发送成功!")
                update_stats(group_name, True, report_type)
                return True
            else:
                logger.warning(f"⚠️ [{group_name}] {report_type} 发送失败，准备重试...")
        except Exception as e:
            logger.error(f"❌ [{group_name}] {report_type} 发生错误: {e}")
        
        if attempt < MAX_RETRIES - 1:
            logger.info(f"⏳ {RETRY_INTERVAL//60}分钟后重试...")
            time.sleep(RETRY_INTERVAL)
    
    logger.error(f"❌ [{group_name}] {report_type} 重试{MAX_RETRIES}次后仍失败，放弃发送")
    update_stats(group_name, False, report_type)
    return False

def filter_groups(groups_dict=None):
    if groups_dict is None:
        return []
    
    filtered = []
    
    if TEST_MODE:
        for group_name, group_config in groups_dict.items():
            if group_name == TEST_GROUP:
                filtered.append((group_name, group_config))
                break
        return filtered
    
    for group_name, group_config in groups_dict.items():
        if DEBUG_MODE:
            if group_name == DEBUG_GROUP:
                filtered.append((group_name, group_config))
            continue
        
        if not group_config.get("enabled", True):
            continue
        
        if group_name not in BLACKLIST_GROUPS:
            filtered.append((group_name, group_config))
    
    return filtered

def process_group(token, group_name, group_config, report_type, filter_func, *filter_args):
    if not TEST_MODE and not group_config.get("enabled", True):
        logger.info(f"⏭️ [{group_name}] 已跳过（未启用）")
        return
    
    user_name_cache.set_token(token)
    
    group_id = group_config["id"]
    
    filtered_messages, *date_info = filter_func([], *filter_args)
    
    if report_type == "日报":
        date_key = date_info[0]
    elif report_type == "周报":
        date_key = f"{date_info[0]}_{date_info[1]}"
    else:
        date_key = date_info[0]
    
    task_id = f"stats_{report_type}_{date_key}_{group_id}"
    
    if TASK_STATE_MANAGER_AVAILABLE and _state_manager:
        task_state = _state_manager.get_task_state(task_id)
        if task_state:
            if task_state.get("status") == "completed":
                logger.info(f"⏭️ [{group_name}] {report_type}({date_key}) 已完成，跳过（幂等检查）")
                return None
            if task_state.get("status") == "running":
                logger.info(f"⏭️ [{group_name}] {report_type}({date_key}) 正在执行中，跳过")
                return None
        
        _state_manager.create_task(task_id, group_id, report_type, date_key)
        _state_manager.update_task_status(task_id, TaskStatus.RUNNING)
    
    if is_already_sent(group_id, report_type, date_key):
        logger.info(f"⏭️ [{group_name}] {report_type}({date_key}) 已发送过，跳过")
        return None
    
    lock_acquired = False
    if INCREMENTAL_FETCHER_AVAILABLE and _lock_manager:
        if not _lock_manager.acquire(task_id, timeout=600):
            logger.info(f"⚠️ [{group_name}] {report_type}({date_key}) 获取锁失败，跳过")
            return None
        lock_acquired = True
        logger.info(f"🔒 [{group_name}] 已获取分布式锁")
    
    try:
        if INCREMENTAL_FETCHER_AVAILABLE and _rate_limiter:
            _rate_limiter.wait_if_needed()
        
        members = get_group_members(token, group_id)
        messages = get_all_messages(token, group_id)
        
        filtered_messages, *date_info = filter_func(messages, *filter_args)
        
        if report_type == "日报":
            date_key = date_info[0]
        elif report_type == "周报":
            date_key = f"{date_info[0]}_{date_info[1]}"
        else:
            date_key = date_info[0]
        
        count = count_messages(filtered_messages, members)
        
        if report_type == "日报":
            report = generate_report(count, "群消息日报", date_info[0], group_name, members, "daily")
        elif report_type == "周报":
            report = generate_report(count, "群消息周报", f"{date_info[0]} ~ {date_info[1]}", group_name, members, "weekly")
        else:
            report = generate_report(count, "群消息月报", date_info[0], group_name, members, "monthly")
        
        if SEND_CHECK_SYSTEM_AVAILABLE:
            checker = SendCheckSystem(SEND_RECORDS_FILE, CONTENT_VERSION)
            is_valid, reason = checker.validate_content_format(report, report_type)
            if not is_valid:
                logger.error(f"❌ [{group_name}] 内容格式验证失败: {reason}")
                return False
            logger.info(f"✅ [{group_name}] 内容格式验证通过")
        
        if not report or len(report) < 50:
            logger.error(f"❌ [{group_name}] 报告内容过短或为空")
            return False
        
        if "success" in report and "content" in report:
            logger.error(f"❌ [{group_name}] 检测到字典格式错误")
            return False
        
        def do_send():
            resp = send_message_to_group(token, group_id, report)
            return resp.get("code") == 0
        
        result = send_with_retry(do_send, report_type, group_name)
        
        if result:
            if TASK_STATE_MANAGER_AVAILABLE and _state_manager:
                _state_manager.update_task_status(task_id, TaskStatus.COMPLETED)
            if SEND_CHECK_SYSTEM_AVAILABLE:
                checker = SendCheckSystem(SEND_RECORDS_FILE, CONTENT_VERSION)
                checker.record_send(group_id, report_type, date_key, group_name, report, success=True)
            else:
                mark_as_sent(group_id, report_type, date_key, group_name)
        
        return result
    
    except Exception as e:
        logger.error(f"❌ [{group_name}] 处理失败: {e}")
        if TASK_STATE_MANAGER_AVAILABLE and _state_manager:
            _state_manager.update_task_status(task_id, TaskStatus.FAILED, error_msg=str(e))
        return False
    
    finally:
        if lock_acquired and INCREMENTAL_FETCHER_AVAILABLE and _lock_manager:
            _lock_manager.release(task_id)
            logger.info(f"🔓 [{group_name}] 已释放分布式锁")

def send_daily_report():
    if not is_valid_send_time():
        return
    logger.info(f"📅 开始发送昨日日报...")
    logger.info("=" * 60)
    
    clean_old_records()
    
    token = get_tenant_token()
    if not token:
        logger.error(f"❌ Token 获取失败")
        return
    
    groups_dict = sync_groups_from_api(token)
    
    filtered_groups = filter_groups(groups_dict)
    logger.info(f"📋 将发送到 {len(filtered_groups)} 个群")
    
    success_count = 0
    fail_count = 0
    skip_count = 0
    
    for group_name, group_config in filtered_groups:
        result = process_group(token, group_name, group_config, "日报", filter_messages_by_day, 1)
        if result == True:
            success_count += 1
        elif result == False:
            fail_count += 1
        else:
            skip_count += 1
    
    logger.info("=" * 60)
    logger.info(f"📊 日报发送完成: ✅ {success_count} ❌ {fail_count} ⏭️ {skip_count}")

def send_weekly_report():
    if not is_valid_send_time():
        return
    logger.info(f"📊 开始发送上周周报...")
    logger.info("=" * 60)
    
    clean_old_records()
    
    token = get_tenant_token()
    if not token:
        logger.error(f"❌ Token 获取失败")
        return
    
    groups_dict = sync_groups_from_api(token)
    
    filtered_groups = filter_groups(groups_dict)
    logger.info(f"📋 将发送到 {len(filtered_groups)} 个群")
    
    success_count = 0
    fail_count = 0
    skip_count = 0
    
    for group_name, group_config in filtered_groups:
        result = process_group(token, group_name, group_config, "周报", filter_messages_by_week, 1)
        if result == True:
            success_count += 1
        elif result == False:
            fail_count += 1
        else:
            skip_count += 1
    
    logger.info("=" * 60)
    logger.info(f"📊 周报发送完成: ✅ {success_count} ❌ {fail_count} ⏭️ {skip_count}")

def send_monthly_report():
    if not is_valid_send_time():
        return
    logger.info(f"📈 开始发送上月月报...")
    logger.info("=" * 60)
    
    clean_old_records()
    
    token = get_tenant_token()
    if not token:
        logger.error(f"❌ Token 获取失败")
        return
    
    groups_dict = sync_groups_from_api(token)
    
    filtered_groups = filter_groups(groups_dict)
    logger.info(f"📋 将发送到 {len(filtered_groups)} 个群")
    
    success_count = 0
    fail_count = 0
    skip_count = 0
    
    for group_name, group_config in filtered_groups:
        result = process_group(token, group_name, group_config, "月报", filter_messages_by_month, 1)
        if result == True:
            success_count += 1
        elif result == False:
            fail_count += 1
        else:
            skip_count += 1
    
    logger.info("=" * 60)
    logger.info(f"📊 月报发送完成: ✅ {success_count} ❌ {fail_count} ⏭️ {skip_count}")

def show_status():
    now = datetime.now()
    
    print("=" * 70)
    print("🤖 群消息统计机器人 - 状态信息（分时段版 + 自动同步 + 日志）")
    print("=" * 70)
    print(f"\n⏰ 当前时间：{now.strftime('%Y-%m-%d %H:%M:%S')} 周{'一二三四五六日'[now.weekday()]}")
    print()
    
    print("📋 发送时间配置（分时段，避免冲突）：")
    print("-" * 70)
    print(f"  📅 日报发送时间：每天 {DAILY_TIME}")
    print(f"  📊 周报发送时间：每周一 {WEEKLY_TIME}")
    print(f"  📈 月报发送时间：每月1号 {MONTHLY_TIME}")
    print()
    
    print("📊 分时段发送说明：")
    print("-" * 70)
    print("  • 每天 09:00 → 日报（昨日）")
    print("  • 周一 12:00 → 周报（上周）【额外】")
    print("  • 月初 15:00 → 月报（上月）【额外】")
    print()
    
    print("🔄 自动同步功能：")
    print("-" * 70)
    print("  • 每次发送前自动检测新群")
    print("  • 新添加机器人的群会自动加入发送列表")
    print("  • 黑名单中的群会被自动排除")
    print("  • 新群配置自动持久化保存")
    print()
    
    print("👥 群组配置：")
    print("-" * 70)
    filtered_groups = filter_groups()
    print(f"  启用群数：{len(filtered_groups)} 个")
    for group_name, group_config in filtered_groups:
        auto_mark = " 🆕" if group_config.get("auto_added") else ""
        print(f"  • {group_name}{auto_mark}")
    print()
    
    stats = load_stats()
    print("📊 发送统计：")
    print("-" * 70)
    print(f"  总发送次数：{stats['total_sends']}")
    print(f"  成功次数：{stats['success_sends']}")
    print(f"  失败次数：{stats['fail_sends']}")
    if stats['total_sends'] > 0:
        success_rate = stats['success_sends'] / stats['total_sends'] * 100
        print(f"  成功率：{success_rate:.1f}%")
    if stats['last_send_time']:
        print(f"  最后发送时间：{stats['last_send_time']}")
    print()
    
    print(f"📁 日志文件：{LOG_FILE}")
    print(f"📊 统计文件：{STATS_FILE}")
    print(f"💾 持久化群组：{PERSISTENT_GROUPS_FILE}")
    print()
    
    print("=" * 70)

def show_schedule():
    now = datetime.now()
    
    print("=" * 70)
    print("📅 群消息统计机器人 - 接下来五次发送时间预览（分时段版）")
    print("=" * 70)
    print(f"\n⏰ 当前时间：{now.strftime('%Y-%m-%d %H:%M:%S')} 周{'一二三四五六日'[now.weekday()]}")
    print()
    
    print("📋 发送时间配置（分时段，避免冲突）：")
    print("-" * 70)
    print(f"  📅 日报发送时间：每天 {DAILY_TIME}")
    print(f"  📊 周报发送时间：每周一 {WEEKLY_TIME}")
    print(f"  📈 月报发送时间：每月1号 {MONTHLY_TIME}")
    print()
    
    print("📋 接下来五次发送计划")
    print("-" * 70)
    
    schedules = []
    current = now
    
    while len(schedules) < 10:
        is_mon = current.weekday() == 0
        is_first = current.day == 1
        
        daily_time = current.replace(hour=int(DAILY_TIME.split(":")[0]), minute=int(DAILY_TIME.split(":")[1]), second=0, microsecond=0)
        weekly_time = current.replace(hour=int(WEEKLY_TIME.split(":")[0]), minute=int(WEEKLY_TIME.split(":")[1]), second=0, microsecond=0)
        monthly_time = current.replace(hour=int(MONTHLY_TIME.split(":")[0]), minute=int(MONTHLY_TIME.split(":")[1]), second=0, microsecond=0)
        
        if daily_time > now:
            schedules.append({
                'date': daily_time,
                'type': '日报',
                'desc': '日常'
            })
        
        if is_mon and weekly_time > now:
            schedules.append({
                'date': weekly_time,
                'type': '周报',
                'desc': '周一'
            })
        
        if is_first and monthly_time > now:
            schedules.append({
                'date': monthly_time,
                'type': '月报',
                'desc': '月初'
            })
        
        current = current + timedelta(days=1)
        current = current.replace(hour=0, minute=0, second=0, microsecond=0)
    
    schedules.sort(key=lambda x: x['date'])
    schedules = schedules[:5]
    
    for i, schedule in enumerate(schedules, 1):
        dt = schedule['date']
        weekdays = ['一', '二', '三', '四', '五', '六', '日']
        type_icons = {'日报': '📅', '周报': '📊', '月报': '📈'}
        
        icon = type_icons.get(schedule['type'], '📄')
        is_today = (dt.date() == now.date())
        today_mark = " 【今天】" if is_today else ""
        
        print(f"  第{i}次：{icon} {schedule['type']}: {dt.strftime('%Y-%m-%d %H:%M')} 周{weekdays[dt.weekday()]} ({schedule['desc']}){today_mark}")
    
    print()
    print("=" * 70)

def main():
    if len(sys.argv) > 1:
        arg = sys.argv[1]
        if arg == "--status":
            show_status()
            return
        elif arg == "--schedule":
            show_schedule()
            return
        elif arg == "--now":
            send_daily_report()
            return
        elif arg == "--check-missed":
            missed = check_missed_reports()
            if missed:
                print(f"⚠️ 发现 {len(missed)} 个漏发报告:")
                for item in missed:
                    print(f"  • {item['group_name']} - {item['type']} ({item['reason']})")
            else:
                print("✅ 无漏发报告")
            return
        elif arg == "--send-missed":
            send_missed_reports()
            return
    
    print("=" * 70)
    print("🤖 群消息统计机器人 - 多群定时发送服务（动态群组 + 分时段 + 日志）")
    print("=" * 70)
    print("")
    
    if TEST_MODE:
        print("🧪 【测试模式】已启用")
        print(f"   测试群：{TEST_GROUP}")
        print("   ⚠️ 所有消息只会发送到测试群，不会打扰其他群")
        print("")
    
    token = get_tenant_token()
    if token:
        groups_dict = sync_groups_from_api(token)
        filtered_groups = filter_groups(groups_dict)
        print("📋 监控群组:")
        for group_name, g_config in filtered_groups:
            test_mark = " 🧪" if TEST_MODE else ""
            print(f"  • {group_name}{test_mark}")
    else:
        print("⚠️ 无法获取群组列表（Token获取失败）")
    print("")
    print("📝 定时任务（分时段发送）：")
    print(f"  - 每天 {DAILY_TIME}: 发送昨日日报")
    print(f"  - 每周一 {WEEKLY_TIME}: 发送上周周报")
    print(f"  - 每月1号 {MONTHLY_TIME}: 发送上月月报")
    print("")
    print("📊 分时段优势：")
    print("  • 同一天可发送多种报告，互不冲突")
    print("  • 用户不会同时收到多条消息")
    print("  • 时间有规律，用户体验好")
    print("")
    print("🔄 动态群组管理：")
    print("  • 每次发送前自动获取机器人所在的所有群")
    print("  • 新添加机器人的群会自动加入发送列表")
    print("  • 测试群会被自动排除")
    print("")
    print("🔄 重试机制：")
    print(f"  - 发送失败时，每隔 {RETRY_INTERVAL//60} 分钟重试")
    print(f"  - 最多重试 {MAX_RETRIES} 次")
    print("")
    print("🔍 漏发检查机制：")
    print("  • 启动时自动检查漏发报告")
    print("  • 发现漏发自动补发")
    print("")
    print("📁 日志与统计：")
    print(f"  - 日志文件：{LOG_FILE}")
    print(f"  - 统计文件：{STATS_FILE}")
    print("")
    print("🚀 服务已启动，按 Ctrl+C 停止")
    print("=" * 70)
    
    print("\n🔍 启动时检查漏发报告...")
    send_missed_reports()
    print("")
    
    schedule.every().day.at(DAILY_TIME).do(send_daily_report)
    schedule.every().monday.at(WEEKLY_TIME).do(send_weekly_report)
    schedule.every().day.at(MONTHLY_TIME).do(lambda: send_monthly_report() if is_first_day_of_month() else None)
    
    while True:
        schedule.run_pending()
        time.sleep(30)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n👋 服务已停止")

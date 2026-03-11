#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
统一测试框架 V4 - 项目市场二部群内容测试（真实群测试）
"""

import sys
import os
from datetime import datetime, timedelta
import calendar
from collections import Counter
import requests
import json

NO_PROXY = {}

# 手动定义两个机器人的配置，避免模块导入问题
MEETING_APP_ID = "cli_a9233dfe18389bde"
MEETING_APP_SECRET = "8gvZm8C04sS0GJXtDQdkkeAOJV6gCr4w"

STATS_APP_ID = "cli_a92aab4685f9dbc7"
STATS_APP_SECRET = "kjoKDg6QN3fcR58IvLj8WeK3YwkRwsXO"

def get_meeting_token():
    """获取群会议纪要机器人的token"""
    url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
    data = {"app_id": MEETING_APP_ID, "app_secret": MEETING_APP_SECRET}
    resp = requests.post(url, json=data, proxies=NO_PROXY).json()
    return resp.get("tenant_access_token")

def get_stats_token():
    """获取群消息统计机器人的token"""
    url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
    data = {"app_id": STATS_APP_ID, "app_secret": STATS_APP_SECRET}
    resp = requests.post(url, json=data, proxies=NO_PROXY).json()
    return resp.get("tenant_access_token")

# 导入其他函数
meeting_bot_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "每日群纪要总结")
stats_bot_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "飞书统计群成员消息数")

sys.path.insert(0, meeting_bot_path)
sys.path.insert(0, stats_bot_path)

# 先导入config模块，确保CEO_LIST定义
from config import CEO_LIST

from 群会议纪要_最终版 import (
    get_bot_groups as get_meeting_groups,
    get_messages_by_time_range,
    get_group_members as get_meeting_group_members,
    extract_chat_records as extract_meeting_chat_records,
    format_chat_text,
    local_summarize,
    send_message_to_group as send_meeting_message
)

from 多群统计 import (
    get_bot_groups as get_stats_groups,
    get_group_members as get_stats_group_members,
    generate_daily_report,
    generate_weekly_report,
    generate_monthly_report,
    send_message_to_group as send_stats_message,
    count_messages
)

def get_chat_id_by_name(groups, name):
    """根据群名获取聊天ID"""
    for group in groups:
        if group.get("name") == name:
            return group.get("chat_id")
    return None

def get_messages_by_date_range(token, chat_id, days_back=1):
    """获取指定日期范围的消息"""
    now = datetime.now()
    
    if days_back == 1:
        start_time = now - timedelta(hours=24)
        end_time = now
    elif days_back == 7:
        monday = now - timedelta(days=now.weekday())
        start_time = monday - timedelta(weeks=1)
        end_time = monday
    else:
        first_of_month = now.replace(day=1)
        start_time = (first_of_month - timedelta(days=1)).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        end_time = first_of_month
    
    start_ts = int(start_time.timestamp() * 1000)
    end_ts = int(end_time.timestamp() * 1000)
    
    messages = get_messages_by_time_range(token, chat_id, start_ts, end_ts)
    
    return messages, start_time, end_time

def test_meeting_bot(source_chat_id, source_chat_name, target_chat_id):
    """测试群会议纪要机器人"""
    print("\n" + "=" * 80)
    print("🤖 机器人1：群会议纪要机器人")
    print("=" * 80)
    
    token = get_meeting_token()
    if not token:
        print("❌ 获取token失败")
        return 0
    
    print(f"✅ 获取到Token: {token}")
    
    success_count = 0
    
    for summary_type, days_back in [("daily", 1), ("weekly", 7), ("monthly", 30)]:
        print(f"\n{'='*80}")
        print(f"📊 群会议纪要机器人 - 生成 {summary_type}")
        print(f"   来源群: {source_chat_name}")
        print(f"   目标群: 张贤良测试群")
        print(f"{'='*80}")
        
        messages, start_time, end_time = get_messages_by_date_range(token, source_chat_id, days_back)
        print(f"✅ 获取到 {len(messages)} 条消息")
        
        members_map = get_meeting_group_members(token, source_chat_id)
        print(f"✅ 获取到 {len(members_map)} 位群成员")
        
        records = extract_meeting_chat_records(messages, members_map)
        print(f"✅ 提取到 {len(records)} 条文本消息")
        
        if summary_type == "daily":
            date_range = start_time.strftime('%Y-%m-%d')
        elif summary_type == "weekly":
            date_range = f"{start_time.strftime('%Y-%m-%d')} ~ {(end_time - timedelta(days=1)).strftime('%Y-%m-%d')}"
        else:
            date_range = start_time.strftime('%Y-%m')
        
        chat_text = format_chat_text(records)
        ai_summary_result = local_summarize(chat_text, summary_type, source_chat_name, date_range, len(records))
        
        if not ai_summary_result:
            print("❌ 总结失败")
            continue
        
        if isinstance(ai_summary_result, dict):
            if not ai_summary_result.get("success"):
                print("❌ 总结生成失败")
                continue
            ai_summary = ai_summary_result.get("content", "")
        else:
            ai_summary = ai_summary_result
        
        if not ai_summary or len(ai_summary) < 50:
            print("❌ 总结内容过短或为空")
            continue
        
        footer = f"\n⏰ 生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n🤖 由群会议纪要机器人自动生成（测试版）"
        
        message_content = f"""{ai_summary}
{footer}
""".strip()
        
        print("\n📤 使用【群会议纪要机器人】Token发送消息...")
        if send_meeting_message(token, target_chat_id, message_content):
            print(f"✅ 发送成功！")
            success_count += 1
        else:
            print(f"❌ 发送失败")
    
    return success_count

def test_stats_bot(source_chat_id, source_chat_name, target_chat_id):
    """测试群消息统计机器人"""
    print("\n" + "=" * 80)
    print("🤖 机器人2：群消息统计机器人")
    print("=" * 80)
    
    token = get_stats_token()
    if not token:
        print("❌ 获取token失败")
        return 0
    
    print(f"✅ 获取到Token: {token}")
    
    success_count = 0
    
    for report_type, days_back in [("日报", 1), ("周报", 7), ("月报", 30)]:
        print(f"\n{'='*80}")
        print(f"📊 群消息统计机器人 - 生成 {report_type}")
        print(f"   来源群: {source_chat_name}")
        print(f"   目标群: 张贤良测试群")
        print(f"{'='*80}")
        
        messages, start_time, end_time = get_messages_by_date_range(token, source_chat_id, days_back)
        print(f"✅ 获取到 {len(messages)} 条消息")
        
        members = get_stats_group_members(token, source_chat_id)
        print(f"✅ 获取到 {len(members)} 位群成员")
        
        members_map = {m.get("member_id"): m.get("name") for m in members}
        count = count_messages(messages, members)
        sorted_count = sorted(count.items(), key=lambda x: x[1], reverse=True)
        
        total = sum(count.values())
        active_count = sum(1 for _, cnt in sorted_count if cnt > 0)
        total_members = len(members_map)
        active_rate = (active_count / total_members * 100) if total_members > 0 else 0
        
        if report_type == "日报":
            date_range = start_time.strftime('%Y-%m-%d')
            title = f"群消息日报 ({date_range})"
            report = generate_daily_report(count, title, date_range, source_chat_name, sorted_count, total, active_count, total_members, active_rate)
        elif report_type == "周报":
            date_range = f"{start_time.strftime('%Y-%m-%d')} ~ {(end_time - timedelta(days=1)).strftime('%Y-%m-%d')}"
            title = f"群消息周报 ({date_range})"
            report = generate_weekly_report(count, title, date_range, source_chat_name, sorted_count, total, active_count, total_members, active_rate)
        else:
            date_range = start_time.strftime('%Y-%m')
            title = f"群消息月报 ({date_range})"
            report = generate_monthly_report(count, title, date_range, source_chat_name, sorted_count, total, active_count, total_members, active_rate)
        
        print("\n📤 使用【群消息统计机器人】Token发送消息...")
        if send_stats_message(token, target_chat_id, report):
            print(f"✅ 发送成功！")
            success_count += 1
        else:
            print(f"❌ 发送失败")
    
    return success_count

def main():
    print("=" * 80)
    print("🤖 统一测试框架 V4 - 项目市场二部群内容测试")
    print("   修复模块导入问题，确保使用正确的机器人身份")
    print("=" * 80)
    
    meeting_token = get_meeting_token()
    stats_token = get_stats_token()
    
    if not meeting_token or not stats_token:
        print("❌ 获取token失败")
        return
    
    print(f"\n📋 Token信息：")
    print(f"   群会议纪要Token: {meeting_token}")
    print(f"   群消息统计Token: {stats_token}")
    
    if meeting_token == stats_token:
        print("\n⚠️ 警告：两个Token相同！")
        print("   这意味着两个机器人使用了同一个身份")
    else:
        print("\n✅ 两个Token不同，身份应该正确区分")
    
    meeting_groups = get_meeting_groups(meeting_token)
    stats_groups = get_stats_groups(stats_token)
    
    source_chat_name = "项目市场二部"
    target_chat_name = "张贤良测试群"
    
    source_chat_id = get_chat_id_by_name(meeting_groups, source_chat_name)
    if not source_chat_id:
        print(f"\n❌ 未找到群组：{source_chat_name}")
        return
    
    target_chat_id = get_chat_id_by_name(meeting_groups, target_chat_name)
    if not target_chat_id:
        print(f"\n❌ 未找到群组：{target_chat_name}")
        return
    
    print(f"\n✅ 找到来源群: {source_chat_name}")
    print(f"✅ 找到目标群: {target_chat_name}")
    
    success_count = 0
    
    success_count += test_meeting_bot(source_chat_id, source_chat_name, target_chat_id)
    success_count += test_stats_bot(source_chat_id, source_chat_name, target_chat_id)
    
    print(f"\n{'='*80}")
    print(f"📊 测试完成: ✅ {success_count}/6 个报告发送成功")
    print(f"{'='*80}")

if __name__ == "__main__":
    main()

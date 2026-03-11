#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
手动触发报告发送 - 用于测试
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import requests
import json
from datetime import datetime, timedelta

APP_ID = "cli_a9233dfe18389bde"
APP_SECRET = "8gvZm8C04sS0GJXtDQdkkeAOJV6gCr4w"
NO_PROXY = {}

def get_token():
    url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal/"
    resp = requests.post(url, json={"app_id": APP_ID, "app_secret": APP_SECRET}, timeout=10, proxies=NO_PROXY).json()
    return resp.get("tenant_access_token") if resp.get("code") == 0 else None

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

def filter_by_day(messages, days_ago=1):
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

def filter_by_week(messages, weeks_ago=1):
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

def filter_by_month(messages, months_ago=1):
    now = datetime.now()
    first_day = now.replace(day=1)
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

def get_group_members(token, group_id):
    url = f"https://open.feishu.cn/open-apis/im/v1/chats/{group_id}/members"
    headers = {"Authorization": f"Bearer {token}"}
    members = []
    page_token = None
    
    while True:
        params = {"member_id_type": "open_id", "page_size": 100}
        if page_token:
            params["page_token"] = page_token
        
        resp = requests.get(url, params=params, headers=headers, proxies=NO_PROXY).json()
        if resp.get("code") != 0:
            break
        
        data = resp.get("data", {})
        items = data.get("items", [])
        members.extend(items)
        
        if not data.get("has_more", False):
            break
        page_token = data.get("page_token")
    
    return members

def count_messages(messages, members):
    member_map = {m.get("member_id"): m.get("name") for m in members}
    count = {}
    
    for msg in messages:
        sender_info = msg.get("sender", {})
        sender_id = sender_info.get("id", "")
        sender_type = sender_info.get("sender_type", "")
        
        if not sender_id or sender_type == "app" or sender_id.startswith("cli_"):
            continue
        
        sender_name = member_map.get(sender_id, "未知")
        if "机器人" in sender_name or sender_name.startswith("cli_"):
            continue
        
        count[sender_name] = count.get(sender_name, 0) + 1
    
    return count

def send_message(token, group_id, text):
    url = "https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type=chat_id"
    headers = {"Authorization": f"Bearer {token}"}
    data = {
        "receive_id": group_id,
        "msg_type": "text",
        "content": json.dumps({"text": text})
    }
    resp = requests.post(url, json=data, headers=headers, proxies=NO_PROXY).json()
    return resp.get("code") == 0

def generate_simple_report(count, title, date_range, group_name):
    total = sum(count.values())
    active_count = sum(1 for _, cnt in count.items() if cnt > 0)
    
    report = f"📊 {group_name} - {title} ({date_range})\n\n"
    report += f"📈 数据：{total} 条消息 | {active_count} 人参与\n\n"
    
    if total > 0:
        sorted_count = sorted(count.items(), key=lambda x: x[1], reverse=True)
        report += "📋 榜单：\n"
        for i, (name, cnt) in enumerate(sorted_count[:10], 1):
            if cnt > 0:
                report += f"   {i}. {name}: {cnt}条\n"
    else:
        report += "暂无消息数据\n"
    
    report += "\n🤖 由群消息统计机器人自动生成\n"
    return report

def main():
    print("=" * 60)
    print("手动触发报告发送")
    print("=" * 60)
    
    # 测试群配置
    source_group = "oc_48e2db5c69667ddfe1a50331939f98e1"  # 英璨市场部大群
    target_group = "oc_7a6e1ed6f52c2d6388f0fc7e2b1c9e4f"  # 张贤良测试群
    
    token = get_token()
    if not token:
        print("❌ Token获取失败")
        return
    print("✅ Token获取成功")
    
    # 获取消息
    print("\n获取消息...")
    messages = get_all_messages(token, source_group)
    print(f"✅ 获取到 {len(messages)} 条消息")
    
    # 获取成员
    print("\n获取成员...")
    members = get_group_members(token, source_group)
    print(f"✅ 获取到 {len(members)} 位成员")
    
    # 日报
    print("\n" + "=" * 60)
    print("生成日报...")
    daily_msgs, daily_date = filter_by_day(messages, days_ago=1)
    daily_count = count_messages(daily_msgs, members)
    daily_report = generate_simple_report(daily_count, "群消息日报", daily_date, "英璨市场部大群")
    print(f"日期: {daily_date}, 消息数: {len(daily_msgs)}, 参与人数: {len(daily_count)}")
    
    # 周报
    print("\n生成周报...")
    weekly_msgs, week_start, week_end = filter_by_week(messages, weeks_ago=1)
    weekly_count = count_messages(weekly_msgs, members)
    weekly_report = generate_simple_report(weekly_count, "群消息周报", f"{week_start} ~ {week_end}", "英璨市场部大群")
    print(f"范围: {week_start} ~ {week_end}, 消息数: {len(weekly_msgs)}, 参与人数: {len(weekly_count)}")
    
    # 月报
    print("\n生成月报...")
    monthly_msgs, month_str = filter_by_month(messages, months_ago=1)
    monthly_count = count_messages(monthly_msgs, members)
    monthly_report = generate_simple_report(monthly_count, "群消息月报", month_str, "英璨市场部大群")
    print(f"月份: {month_str}, 消息数: {len(monthly_msgs)}, 参与人数: {len(monthly_count)}")
    
    # 发送报告
    print("\n" + "=" * 60)
    print("发送报告到测试群...")
    
    print("\n发送日报...")
    if send_message(token, target_group, daily_report):
        print("✅ 日报发送成功")
    else:
        print("❌ 日报发送失败")
    
    print("\n发送周报...")
    if send_message(token, target_group, weekly_report):
        print("✅ 周报发送成功")
    else:
        print("❌ 周报发送失败")
    
    print("\n发送月报...")
    if send_message(token, target_group, monthly_report):
        print("✅ 月报发送成功")
    else:
        print("❌ 月报发送失败")
    
    print("\n" + "=" * 60)
    print("完成！")

if __name__ == "__main__":
    main()

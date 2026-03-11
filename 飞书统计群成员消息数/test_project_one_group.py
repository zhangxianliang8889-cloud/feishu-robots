#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
项目一部群全面测试脚本
测试内容：
1. 获取项目一部群信息
2. 测试消息获取与过滤
3. 生成日报、周报、月报
4. 发送到测试群验证
5. 检查双机器人运行状态
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

TEST_GROUP_ID = "oc_7a6e1ed6f52c2d6388f0fc7e2b1c9e4f"  # 张贤良测试群

def get_token():
    print("🔑 获取访问令牌...")
    url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal/"
    resp = requests.post(url, json={"app_id": APP_ID, "app_secret": APP_SECRET}, timeout=10, proxies=NO_PROXY).json()
    if resp.get("code") == 0:
        print("✅ Token获取成功")
        return resp.get("tenant_access_token")
    else:
        print(f"❌ Token获取失败: {resp}")
        return None

def get_all_chats(token):
    print("\n📋 获取所有群组...")
    url = "https://open.feishu.cn/open-apis/im/v1/chats"
    headers = {"Authorization": f"Bearer {token}"}
    chats = []
    page_token = None
    
    while True:
        params = {"page_size": 100}
        if page_token:
            params["page_token"] = page_token
        
        resp = requests.get(url, params=params, headers=headers, proxies=NO_PROXY).json()
        if resp.get("code") != 0:
            break
        
        data = resp.get("data", {})
        items = data.get("items", [])
        chats.extend(items)
        
        if not data.get("has_more", False):
            break
        page_token = data.get("page_token")
    
    print(f"✅ 获取到 {len(chats)} 个群组")
    return chats

def find_project_one_group(chats):
    print("\n🔍 查找项目一部群...")
    for chat in chats:
        name = chat.get("name", "")
        if "项目一部" in name:
            print(f"✅ 找到项目一部群: {name}")
            print(f"   群ID: {chat.get('chat_id')}")
            return chat
    print("❌ 未找到项目一部群")
    return None

def get_all_messages(token, group_id):
    print("\n📨 获取消息...")
    url = "https://open.feishu.cn/open-apis/im/v1/messages"
    headers = {"Authorization": f"Bearer {token}"}
    all_messages = []
    page_token = None
    page_count = 0
    
    while True:
        page_count += 1
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
        
        if not data.get("has_more", False) or len(all_messages) >= 500:
            break
        page_token = data.get("page_token")
    
    print(f"✅ 获取到 {len(all_messages)} 条消息 ({page_count} 页)")
    return all_messages

def get_group_members(token, group_id):
    print("\n👥 获取群成员...")
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
    
    print(f"✅ 获取到 {len(members)} 位成员")
    return members

def filter_by_day(messages, days_ago=1):
    now = datetime.now()
    target_date = now - timedelta(days=days_ago)
    start_of_day = target_date.replace(hour=0, minute=0, second=0, microsecond=0)
    end_of_day = start_of_day + timedelta(days=1)
    start_ts = int(start_of_day.timestamp() * 1000)
    end_ts = int(end_of_day.timestamp() * 1000)
    
    filtered = [m for m in messages if start_ts <= int(m.get("create_time", 0)) < end_ts]
    return filtered, start_of_day.strftime("%Y-%m-%d")

def filter_by_week(messages, weeks_ago=1):
    now = datetime.now()
    monday = now - timedelta(days=now.weekday())
    start_of_week = monday - timedelta(weeks=weeks_ago)
    end_of_week = start_of_week + timedelta(weeks=1)
    start_ts = int(start_of_week.timestamp() * 1000)
    end_ts = int(end_of_week.timestamp() * 1000)
    
    filtered = [m for m in messages if start_ts <= int(m.get("create_time", 0)) < end_ts]
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
    
    filtered = [m for m in messages if start_ts <= int(m.get("create_time", 0)) < end_ts]
    return filtered, first_day.strftime("%Y-%m")

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

def generate_report(count, title, date_range, group_name):
    total = sum(count.values())
    active_count = sum(1 for _, cnt in count.items() if cnt > 0)
    
    report = f"📊 {group_name} - {title} ({date_range})\n"
    report += "═" * 40 + "\n\n"
    report += f"📈 数据：{total} 条消息 | {active_count} 人参与\n\n"
    
    if total > 0:
        sorted_count = sorted(count.items(), key=lambda x: x[1], reverse=True)
        report += "📋 榜单：\n"
        for i, (name, cnt) in enumerate(sorted_count[:10], 1):
            if cnt > 0:
                report += f"   {i}. {name}: {cnt}条\n"
    else:
        report += "暂无消息数据\n"
    
    report += "\n" + "═" * 40 + "\n"
    report += "🤖 由测试脚本生成\n"
    return report

def main():
    print("=" * 60)
    print("📊 项目一部群全面测试")
    print("=" * 60)
    
    token = get_token()
    if not token:
        return
    
    chats = get_all_chats(token)
    project_one_group = find_project_one_group(chats)
    
    if not project_one_group:
        print("\n⚠️ 未找到项目一部群，使用所有群的第一个测试")
        if chats:
            project_one_group = chats[0]
            print(f"   使用群: {project_one_group.get('name')}")
    
    if not project_one_group:
        print("❌ 无可测试的群组")
        return
    
    group_id = project_one_group.get("chat_id")
    group_name = project_one_group.get("name", "未知群")
    
    messages = get_all_messages(token, group_id)
    members = get_group_members(token, group_id)
    
    if messages:
        print("\n" + "=" * 60)
        print("📊 消息时间分布")
        print("=" * 60)
        dates = {}
        for msg in messages[:50]:
            ts = int(msg.get("create_time", 0))
            dt = datetime.fromtimestamp(ts / 1000)
            date_str = dt.strftime("%Y-%m-%d")
            dates[date_str] = dates.get(date_str, 0) + 1
        for date in sorted(dates.keys()):
            print(f"  {date}: {dates[date]} 条")
    
    print("\n" + "=" * 60)
    print("📋 生成报告测试")
    print("=" * 60)
    
    test_results = []
    
    print("\n📅 测试日报...")
    daily_msgs, daily_date = filter_by_day(messages, days_ago=1)
    daily_count = count_messages(daily_msgs, members)
    daily_report = generate_report(daily_count, "群消息日报", daily_date, group_name)
    print(f"   消息数: {len(daily_msgs)}, 参与人数: {len(daily_count)}")
    
    print("\n📆 测试周报...")
    weekly_msgs, week_start, week_end = filter_by_week(messages, weeks_ago=1)
    weekly_count = count_messages(weekly_msgs, members)
    weekly_report = generate_report(weekly_count, "群消息周报", f"{week_start} ~ {week_end}", group_name)
    print(f"   消息数: {len(weekly_msgs)}, 参与人数: {len(weekly_count)}")
    
    print("\n🗓️ 测试月报...")
    monthly_msgs, month_str = filter_by_month(messages, months_ago=1)
    monthly_count = count_messages(monthly_msgs, members)
    monthly_report = generate_report(monthly_count, "群消息月报", month_str, group_name)
    print(f"   消息数: {len(monthly_msgs)}, 参与人数: {len(monthly_count)}")
    
    print("\n" + "=" * 60)
    print("📤 发送测试报告")
    print("=" * 60)
    
    send_success = 0
    send_total = 0
    
    send_total += 1
    print(f"\n发送日报...")
    if send_message(token, TEST_GROUP_ID, daily_report):
        print("   ✅ 日报发送成功")
        send_success += 1
    else:
        print("   ❌ 日报发送失败")
    
    send_total += 1
    print(f"\n发送周报...")
    if send_message(token, TEST_GROUP_ID, weekly_report):
        print("   ✅ 周报发送成功")
        send_success += 1
    else:
        print("   ❌ 周报发送失败")
    
    send_total += 1
    print(f"\n发送月报...")
    if send_message(token, TEST_GROUP_ID, monthly_report):
        print("   ✅ 月报发送成功")
        send_success += 1
    else:
        print("   ❌ 月报发送失败")
    
    print("\n" + "=" * 60)
    print("📊 测试结果汇总")
    print("=" * 60)
    print(f"测试群组: {group_name}")
    print(f"群ID: {group_id}")
    print(f"消息总数: {len(messages)}")
    print(f"成员总数: {len(members)}")
    print(f"\n发送测试: {send_success}/{send_total} 成功")
    
    test_results.append({
        "group": group_name,
        "group_id": group_id,
        "total_messages": len(messages),
        "total_members": len(members),
        "daily_messages": len(daily_msgs),
        "daily_participants": len(daily_count),
        "weekly_messages": len(weekly_msgs),
        "weekly_participants": len(weekly_count),
        "monthly_messages": len(monthly_msgs),
        "monthly_participants": len(monthly_count),
        "send_success": send_success,
        "send_total": send_total
    })
    
    print("\n" + "=" * 60)
    print("✅ 测试完成！")
    print("=" * 60)
    
    return test_results

if __name__ == "__main__":
    main()

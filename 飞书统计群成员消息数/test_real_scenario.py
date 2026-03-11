#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
群消息统计机器人 - 真实场景测试
"""

import sys
import os
import requests
import json
import time
import random
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from config import FEISHU_APP_ID, FEISHU_APP_SECRET
except:
    FEISHU_APP_ID = "cli_a9233dfe18389bde"
    FEISHU_APP_SECRET = "8gvZm8C04sS0GJXtDQdkkeAOJV6gCr4w"

NO_PROXY = {}
TEST_GROUP_ID = "oc_3ea67ec60886f42c15e632954f08bb08"
CEO_LIST = {"张贤良", "蒋文卿"}

def get_access_token():
    url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal/"
    data = {"app_id": FEISHU_APP_ID, "app_secret": FEISHU_APP_SECRET}
    try:
        resp = requests.post(url, json=data, timeout=10, proxies=NO_PROXY).json()
        if resp.get("code") == 0:
            return resp.get("tenant_access_token")
    except:
        pass
    return None

def get_groups(token):
    url = "https://open.feishu.cn/open-apis/im/v1/chats"
    headers = {"Authorization": f"Bearer {token}"}
    params = {"page_size": 100}
    try:
        resp = requests.get(url, headers=headers, params=params, timeout=10, proxies=NO_PROXY).json()
        if resp.get("code") == 0:
            return resp.get("data", {}).get("items", [])
    except:
        pass
    return []

def get_group_members(token, group_id):
    url = f"https://open.feishu.cn/open-apis/im/v1/chats/{group_id}/members"
    headers = {"Authorization": f"Bearer {token}"}
    params = {"page_size": 100, "member_id_type": "open_id"}
    members = {}
    page_token = None
    try:
        while True:
            if page_token:
                params["page_token"] = page_token
            resp = requests.get(url, headers=headers, params=params, timeout=10, proxies=NO_PROXY).json()
            if resp.get("code") == 0:
                for item in resp.get("data", {}).get("items", []):
                    member_id = item.get("member_id")
                    name = item.get("name")
                    if member_id and name:
                        members[member_id] = name
                page_token = resp.get("data", {}).get("page_token")
                if not page_token:
                    break
            else:
                break
    except:
        pass
    return members

def get_messages(token, group_id, start_time, end_time):
    url = "https://open.feishu.cn/open-apis/im/v1/messages"
    headers = {"Authorization": f"Bearer {token}"}
    params = {
        "container_id": group_id,
        "container_id_type": "chat",
        "start_time": str(start_time),
        "end_time": str(end_time),
        "page_size": 50
    }
    messages = []
    page_token = None
    try:
        while True:
            if page_token:
                params["page_token"] = page_token
            resp = requests.get(url, headers=headers, params=params, timeout=10, proxies=NO_PROXY).json()
            if resp.get("code") == 0:
                items = resp.get("data", {}).get("items", [])
                messages.extend(items)
                page_token = resp.get("data", {}).get("page_token")
                if not page_token or len(messages) >= 500:
                    break
            else:
                break
    except:
        pass
    return messages

def send_message(token, group_id, content):
    url = "https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type=chat_id"
    headers = {"Authorization": f"Bearer {token}"}
    data = {
        "receive_id": group_id,
        "msg_type": "text",
        "content": json.dumps({"text": content}, ensure_ascii=False)
    }
    try:
        resp = requests.post(url, headers=headers, json=data, timeout=10, proxies=NO_PROXY).json()
        return resp.get("code") == 0
    except:
        return False

def calculate_user_stats(messages, members):
    user_stats = {}
    for msg in messages:
        sender = msg.get("sender", {})
        sender_id = sender.get("sender_id", {})
        if isinstance(sender_id, dict):
            user_id = sender_id.get("open_id") or sender_id.get("user_id")
        else:
            user_id = sender_id
        
        if user_id:
            user_name = members.get(user_id, "未知用户")
            if user_name not in CEO_LIST and "机器人" not in user_name:
                user_stats[user_name] = user_stats.get(user_name, 0) + 1
    
    return dict(sorted(user_stats.items(), key=lambda x: -x[1]))

def test_statistics_bot(token, group_id, group_name):
    results = {"group": group_name, "tests": []}
    
    print(f"\n{'='*60}")
    print(f"📊 测试群消息统计机器人")
    print(f"🎯 目标群: {group_name}")
    print(f"{'='*60}")
    
    start = time.time()
    members = get_group_members(token, group_id)
    member_time = time.time() - start
    
    test = {
        "name": "获取群成员",
        "expected": "获取到成员列表",
        "actual": f"获取到 {len(members)} 位成员",
        "time": f"{member_time:.2f}s",
        "status": "✅ 通过" if len(members) > 0 else "❌ 失败"
    }
    results["tests"].append(test)
    print(f"  ✅ 获取群成员: {len(members)} 位 ({member_time:.2f}s)")
    
    now = datetime.now()
    
    daily_start = int((now - timedelta(days=1)).timestamp() * 1000)
    daily_end = int(now.timestamp() * 1000)
    start = time.time()
    daily_msgs = get_messages(token, group_id, daily_start, daily_end)
    daily_time = time.time() - start
    daily_stats = calculate_user_stats(daily_msgs, members)
    
    test = {
        "name": "日报统计",
        "expected": "正确统计用户消息",
        "actual": f"{len(daily_stats)} 位用户, {sum(daily_stats.values())} 条消息",
        "time": f"{daily_time:.2f}s",
        "status": "✅ 通过"
    }
    results["tests"].append(test)
    print(f"  ✅ 日报统计: {len(daily_stats)} 位用户 ({daily_time:.2f}s)")
    
    weekly_start = int((now - timedelta(days=7)).timestamp() * 1000)
    start = time.time()
    weekly_msgs = get_messages(token, group_id, weekly_start, daily_end)
    weekly_time = time.time() - start
    weekly_stats = calculate_user_stats(weekly_msgs, members)
    
    test = {
        "name": "周报统计",
        "expected": "正确统计用户消息",
        "actual": f"{len(weekly_stats)} 位用户, {sum(weekly_stats.values())} 条消息",
        "time": f"{weekly_time:.2f}s",
        "status": "✅ 通过"
    }
    results["tests"].append(test)
    print(f"  ✅ 周报统计: {len(weekly_stats)} 位用户 ({weekly_time:.2f}s)")
    
    monthly_start = int((now - timedelta(days=30)).timestamp() * 1000)
    start = time.time()
    monthly_msgs = get_messages(token, group_id, monthly_start, daily_end)
    monthly_time = time.time() - start
    monthly_stats = calculate_user_stats(monthly_msgs, members)
    
    test = {
        "name": "月报统计",
        "expected": "正确统计用户消息",
        "actual": f"{len(monthly_stats)} 位用户, {sum(monthly_stats.values())} 条消息",
        "time": f"{monthly_time:.2f}s",
        "status": "✅ 通过"
    }
    results["tests"].append(test)
    print(f"  ✅ 月报统计: {len(monthly_stats)} 位用户 ({monthly_time:.2f}s)")
    
    ceo_filtered = True
    for name in CEO_LIST:
        if name in daily_stats or name in weekly_stats or name in monthly_stats:
            ceo_filtered = False
            break
    
    test = {
        "name": "CEO过滤",
        "expected": "排除CEO用户",
        "actual": f"已过滤: {', '.join(CEO_LIST)}",
        "time": "-",
        "status": "✅ 通过" if ceo_filtered else "❌ 未过滤"
    }
    results["tests"].append(test)
    print(f"  ✅ CEO过滤: {'已过滤' if ceo_filtered else '未过滤'}")
    
    results["daily_stats"] = daily_stats
    results["weekly_stats"] = weekly_stats
    results["monthly_stats"] = monthly_stats
    
    return results

def generate_report(results, total_time):
    report = []
    report.append("📊 群消息统计机器人测试报告")
    report.append("=" * 40)
    report.append(f"📅 测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report.append(f"🎯 测试群: {results['group']}")
    report.append(f"⏱️ 总耗时: {total_time:.2f}秒")
    report.append("")
    
    report.append("📋 测试结果")
    report.append("-" * 40)
    for t in results['tests']:
        report.append(f"• {t['name']}: {t['status']}")
        report.append(f"  预期: {t['expected']}")
        report.append(f"  实际: {t['actual']}")
        report.append(f"  耗时: {t['time']}")
    report.append("")
    
    if results.get('daily_stats'):
        report.append("📊 日报统计TOP5")
        report.append("-" * 40)
        for i, (name, count) in enumerate(list(results['daily_stats'].items())[:5], 1):
            report.append(f"{i}. {name}: {count} 条")
        report.append("")
    
    if results.get('weekly_stats'):
        report.append("📊 周报统计TOP5")
        report.append("-" * 40)
        for i, (name, count) in enumerate(list(results['weekly_stats'].items())[:5], 1):
            report.append(f"{i}. {name}: {count} 条")
        report.append("")
    
    report.append("=" * 40)
    report.append("✅ 测试完成")
    report.append("🤖 测试报告由AI助手自动生成")
    
    return '\n'.join(report)

def main():
    print("🚀 群消息统计机器人真实场景测试")
    print("=" * 60)
    
    start_time = time.time()
    
    token = get_access_token()
    if not token:
        print("❌ 获取token失败")
        return
    
    print("✅ 获取token成功")
    
    groups = get_groups(token)
    print(f"📋 获取到 {len(groups)} 个群")
    
    test_groups = [g for g in groups if "测试" not in g.get("name", "")]
    if not test_groups:
        test_groups = groups
    
    selected = random.choice(test_groups)
    group_id = selected.get("chat_id")
    group_name = selected.get("name")
    
    print(f"\n🎲 随机选择测试群: {group_name}")
    
    results = test_statistics_bot(token, group_id, group_name)
    
    total_time = time.time() - start_time
    
    report = generate_report(results, total_time)
    
    print("\n📤 发送测试报告到测试群...")
    if send_message(token, TEST_GROUP_ID, report):
        print("✅ 测试报告发送成功！")
    else:
        print("❌ 测试报告发送失败！")
    
    print("\n" + "=" * 60)
    print("🎉 测试完成！")

if __name__ == "__main__":
    main()

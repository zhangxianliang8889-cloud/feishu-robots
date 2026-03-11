#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试群消息统计机器人 - 发送真实报告到测试群
"""

import sys
import os
import requests
import json
import time
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import *

NO_PROXY = {}
TEST_GROUP_ID = "oc_3ea67ec60886f42c15e632954f08bb08"
TARGET_GROUP_ID = "oc_48e2db5c69667ddfe1a50331939f98e1"
TARGET_GROUP_NAME = "英璨市场部大群"
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
                for msg in items:
                    create_time = int(msg.get("create_time", 0))
                    if start_time <= create_time <= end_time:
                        messages.append(msg)
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

def generate_daily_report(messages, members, date_str):
    stats = calculate_user_stats(messages, members)
    total = sum(stats.values())
    
    report = []
    report.append(f"📊 {TARGET_GROUP_NAME} - 群消息统计日报")
    report.append(f"📅 {date_str}")
    report.append("═" * 30)
    report.append("")
    report.append(f"📈 今日数据：{total} 条消息 | {len(stats)} 人参与")
    report.append("─" * 30)
    report.append("")
    
    if stats:
        report.append("🏆 消息数量排名")
        for i, (name, count) in enumerate(list(stats.items())[:10], 1):
            medal = "🥇" if i == 1 else ("🥈" if i == 2 else ("🥉" if i == 3 else f"{i}."))
            report.append(f"{medal} {name}: {count} 条")
    else:
        report.append("暂无消息数据")
    
    report.append("")
    report.append("═" * 30)
    report.append("🤖 由群消息统计机器人自动生成")
    
    return '\n'.join(report)

def generate_weekly_report(messages, members, start_date, end_date):
    stats = calculate_user_stats(messages, members)
    total = sum(stats.values())
    days = 7
    
    report = []
    report.append(f"📊 {TARGET_GROUP_NAME} - 群消息统计周报")
    report.append(f"📅 {start_date} ~ {end_date}")
    report.append("═" * 30)
    report.append("")
    report.append(f"📈 本周数据：{total} 条消息 | {len(stats)} 人参与 | 日均 {total // days if total > 0 else 0} 条")
    report.append("─" * 30)
    report.append("")
    
    if stats:
        report.append("🏆 本周活跃榜 TOP10")
        for i, (name, count) in enumerate(list(stats.items())[:10], 1):
            medal = "🥇" if i == 1 else ("🥈" if i == 2 else ("🥉" if i == 3 else f"{i}."))
            report.append(f"{medal} {name}: {count} 条")
    else:
        report.append("暂无消息数据")
    
    report.append("")
    report.append("═" * 30)
    report.append("🤖 由群消息统计机器人自动生成")
    
    return '\n'.join(report)

def generate_monthly_report(messages, members, start_date, end_date):
    stats = calculate_user_stats(messages, members)
    total = sum(stats.values())
    days = 30
    
    report = []
    report.append(f"📊 {TARGET_GROUP_NAME} - 群消息统计月报")
    report.append(f"📅 {start_date} ~ {end_date}")
    report.append("═" * 30)
    report.append("")
    report.append(f"📈 本月数据：{total} 条消息 | {len(stats)} 人参与 | 日均 {total // days if total > 0 else 0} 条")
    report.append("─" * 30)
    report.append("")
    
    if stats:
        report.append("🏆 本月活跃榜 TOP10")
        for i, (name, count) in enumerate(list(stats.items())[:10], 1):
            medal = "🥇" if i == 1 else ("🥈" if i == 2 else ("🥉" if i == 3 else f"{i}."))
            report.append(f"{medal} {name}: {count} 条")
    else:
        report.append("暂无消息数据")
    
    report.append("")
    report.append("═" * 30)
    report.append("🤖 由群消息统计机器人自动生成")
    
    return '\n'.join(report)

def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--send', action='store_true', help='实际发送到测试群')
    parser.add_argument('--type', choices=['daily', 'weekly', 'monthly', 'all'], default='all')
    args = parser.parse_args()
    
    print("🚀 测试群消息统计机器人")
    print("=" * 60)
    print(f"\n🎯 目标群：{TARGET_GROUP_NAME}")
    print(f"📧 发送到：张贤良测试群")
    print("=" * 60)
    
    token = get_access_token()
    if not token:
        print("❌ 获取token失败")
        return
    
    print("✅ 获取token成功")
    
    members = get_group_members(token, TARGET_GROUP_ID)
    print(f"✅ 获取群成员: {len(members)} 位")
    
    now = datetime.now()
    today_str = now.strftime("%Y-%m-%d")
    week_start_str = (now - timedelta(days=7)).strftime("%Y-%m-%d")
    month_start_str = (now - timedelta(days=30)).strftime("%Y-%m-%d")
    
    if args.type in ['daily', 'all']:
        print("\n📅 测试日报")
        print("=" * 60)
        daily_start = int((now - timedelta(days=1)).timestamp() * 1000)
        daily_end = int(now.timestamp() * 1000)
        daily_msgs = get_messages(token, TARGET_GROUP_ID, daily_start, daily_end)
        print(f"✅ 获取消息: {len(daily_msgs)} 条")
        
        report = generate_daily_report(daily_msgs, members, today_str)
        if args.send:
            if send_message(token, TEST_GROUP_ID, report):
                print("✅ 日报发送成功！")
            else:
                print("❌ 日报发送失败！")
        else:
            print("\n" + report)
    
    if args.type in ['weekly', 'all']:
        print("\n📅 测试周报")
        print("=" * 60)
        weekly_start = int((now - timedelta(days=7)).timestamp() * 1000)
        weekly_end = int(now.timestamp() * 1000)
        weekly_msgs = get_messages(token, TARGET_GROUP_ID, weekly_start, weekly_end)
        print(f"✅ 获取消息: {len(weekly_msgs)} 条")
        
        report = generate_weekly_report(weekly_msgs, members, week_start_str, today_str)
        if args.send:
            if send_message(token, TEST_GROUP_ID, report):
                print("✅ 周报发送成功！")
            else:
                print("❌ 周报发送失败！")
        else:
            print("\n" + report)
    
    if args.type in ['monthly', 'all']:
        print("\n📅 测试月报")
        print("=" * 60)
        monthly_start = int((now - timedelta(days=30)).timestamp() * 1000)
        monthly_end = int(now.timestamp() * 1000)
        monthly_msgs = get_messages(token, TARGET_GROUP_ID, monthly_start, monthly_end)
        print(f"✅ 获取消息: {len(monthly_msgs)} 条")
        
        report = generate_monthly_report(monthly_msgs, members, month_start_str, today_str)
        if args.send:
            if send_message(token, TEST_GROUP_ID, report):
                print("✅ 月报发送成功！")
            else:
                print("❌ 月报发送失败！")
        else:
            print("\n" + report)
    
    print("\n" + "=" * 60)
    print("🎉 测试完成！")

if __name__ == "__main__":
    main()

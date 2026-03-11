#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
为策划二部生成真实报告
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

def extract_text_content(msg):
    content = msg.get("body", {}).get("content", "")
    try:
        data = json.loads(content)
        return data.get("text", "")
    except:
        return content

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

def generate_daily_stats_report(messages, members, date_str):
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

def generate_weekly_stats_report(messages, members, start_date, end_date):
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

def generate_monthly_stats_report(messages, members, start_date, end_date):
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

def generate_daily_meeting_report(messages, members, date_str):
    text_messages = [m for m in messages if m.get("msg_type") == "text"]
    stats = calculate_user_stats(messages, members)
    total = len(text_messages)
    
    topics = []
    for msg in text_messages[:20]:
        text = extract_text_content(msg)
        if text and len(text) > 10:
            topics.append(text[:50])
    
    report = []
    report.append(f"📊 {TARGET_GROUP_NAME} - 群会议纪要日报")
    report.append(f"📅 {date_str}")
    report.append("═" * 30)
    report.append("")
    report.append(f"📈 今日数据：{total} 条消息 | {len(stats)} 人参与")
    report.append("─" * 30)
    report.append("")
    
    if topics:
        report.append("📌 今日讨论话题")
        for i, topic in enumerate(topics[:5], 1):
            report.append(f"• {topic}")
    else:
        report.append("📌 今日讨论话题")
        report.append("• 暂无")
    
    report.append("")
    report.append("─" * 30)
    report.append("📋 待办事项")
    report.append("• 暂无")
    report.append("")
    report.append("💡 AI建议")
    if total >= 20:
        report.append("• 今日讨论活跃，建议保持良好势头")
    elif total >= 10:
        report.append("• 建议鼓励更多成员分享见解")
    else:
        report.append("• 建议主动发起话题，带动讨论氛围")
    
    report.append("")
    report.append("═" * 30)
    report.append(f"💡 今日总结：共{len(stats)}人参与，产生{total}条消息。")
    report.append("═" * 30)
    report.append("")
    report.append("🤖 由群会议纪要机器人自动生成")
    
    return '\n'.join(report)

def generate_weekly_meeting_report(messages, members, start_date, end_date):
    text_messages = [m for m in messages if m.get("msg_type") == "text"]
    stats = calculate_user_stats(messages, members)
    total = len(text_messages)
    days = 7
    
    topics = []
    for msg in text_messages[:30]:
        text = extract_text_content(msg)
        if text and len(text) > 10:
            topics.append(text[:50])
    
    report = []
    report.append(f"📊 {TARGET_GROUP_NAME} - 群会议纪要周报")
    report.append(f"📅 {start_date} ~ {end_date}")
    report.append("═" * 30)
    report.append("")
    report.append(f"📈 本周数据：{total} 条消息 | {len(stats)} 人参与 | 日均 {total // days if total > 0 else 0} 条")
    report.append("─" * 30)
    report.append("")
    
    if topics:
        report.append("📌 本周重点讨论")
        for i, topic in enumerate(topics[:7], 1):
            report.append(f"• {topic}")
    else:
        report.append("📌 本周重点讨论")
        report.append("• 暂无")
    
    report.append("")
    report.append("─" * 30)
    report.append("✅ 本周决议")
    report.append("• 暂无")
    report.append("")
    report.append("─" * 30)
    report.append("📋 待跟进事项")
    report.append("• 暂无")
    report.append("")
    report.append("💡 AI建议与洞察")
    if total >= 50:
        report.append("• 本周交流活跃，建议保持良好势头")
        report.append("• 可尝试更深入的项目讨论，激发创新")
    elif total >= 20:
        report.append("• 建议继续鼓励成员分享，提升讨论质量")
        report.append("• 可定期组织主题交流，增强凝聚力")
    else:
        report.append("• 建议定期组织话题讨论，激发群智涌现")
    
    report.append("")
    report.append("═" * 30)
    report.append("📊 本周复盘")
    report.append("═" * 30)
    report.append(f"• 本周共{len(stats)}人参与，产生{total}条消息")
    report.append("")
    report.append("═" * 30)
    report.append(f"🎯 周总结：本周共{len(stats)}人参与讨论。")
    report.append("═" * 30)
    report.append("")
    report.append("🚀 贝索斯：我们要做10年不会变的事情")
    report.append("")
    report.append("🤖 由群会议纪要机器人自动生成")
    
    return '\n'.join(report)

def generate_monthly_meeting_report(messages, members, start_date, end_date):
    text_messages = [m for m in messages if m.get("msg_type") == "text"]
    stats = calculate_user_stats(messages, members)
    total = len(text_messages)
    days = 30
    
    topics = []
    for msg in text_messages[:50]:
        text = extract_text_content(msg)
        if text and len(text) > 10:
            topics.append(text[:50])
    
    report = []
    report.append(f"📊 {TARGET_GROUP_NAME} - 群会议纪要月报")
    report.append(f"📅 {start_date} ~ {end_date}")
    report.append("═" * 30)
    report.append("")
    report.append(f"📈 本月数据：{total} 条消息 | {len(stats)} 人参与 | 日均 {total // days if total > 0 else 0} 条")
    report.append("─" * 30)
    report.append("")
    
    if topics:
        report.append("📌 本月核心话题")
        for i, topic in enumerate(topics[:10], 1):
            report.append(f"• {topic}")
    else:
        report.append("📌 本月核心话题")
        report.append("• 暂无")
    
    report.append("")
    report.append("─" * 30)
    report.append("✅ 本月重要决议")
    report.append("• 暂无")
    report.append("")
    report.append("─" * 30)
    report.append("📋 待跟进事项")
    report.append("• 暂无")
    report.append("")
    report.append("💡 AI建议与洞察")
    avg_daily = total / days if days > 0 else 0
    if avg_daily >= 10:
        report.append("• 本月交流活跃，建议保持良好势头")
        report.append("• 可尝试更深入的项目讨论，激发创新")
    elif avg_daily >= 5:
        report.append("• 建议继续鼓励成员分享，提升讨论质量")
        report.append("• 可定期组织主题交流，增强凝聚力")
    else:
        report.append("• 建议定期组织话题讨论，激发群智涌现")
        report.append("• 分享有价值内容，带动讨论氛围")
    
    report.append("")
    report.append("═" * 30)
    report.append("📊 月度复盘")
    report.append("═" * 30)
    report.append(f"• 本月共{len(stats)}人参与，产生{total}条消息")
    report.append("")
    report.append("═" * 30)
    report.append(f"🎯 月总结：本月共{len(stats)}人参与讨论。")
    report.append("═" * 30)
    report.append("")
    report.append("🚀 下月展望：期待更多精彩讨论，群智涌现！")
    report.append("")
    report.append("🤖 由群会议纪要机器人自动生成")
    
    return '\n'.join(report)

def main():
    print("🚀 为策划二部生成真实报告")
    print("=" * 60)
    
    token = get_access_token()
    if not token:
        print("❌ 获取token失败")
        return
    
    print("✅ 获取token成功")
    
    members = get_group_members(token, TARGET_GROUP_ID)
    print(f"✅ 获取群成员: {len(members)} 位")
    
    now = datetime.now()
    
    daily_start = int((now - timedelta(days=1)).timestamp() * 1000)
    daily_end = int(now.timestamp() * 1000)
    daily_msgs = get_messages(token, TARGET_GROUP_ID, daily_start, daily_end)
    print(f"✅ 获取日报消息: {len(daily_msgs)} 条")
    
    weekly_start = int((now - timedelta(days=7)).timestamp() * 1000)
    weekly_msgs = get_messages(token, TARGET_GROUP_ID, weekly_start, daily_end)
    print(f"✅ 获取周报消息: {len(weekly_msgs)} 条")
    
    monthly_start = int((now - timedelta(days=30)).timestamp() * 1000)
    monthly_msgs = get_messages(token, TARGET_GROUP_ID, monthly_start, daily_end)
    print(f"✅ 获取月报消息: {len(monthly_msgs)} 条")
    
    today_str = now.strftime("%Y-%m-%d")
    week_start_str = (now - timedelta(days=7)).strftime("%Y-%m-%d")
    month_start_str = (now - timedelta(days=30)).strftime("%Y-%m-%d")
    
    print("\n📊 生成群消息统计报告...")
    daily_stats = generate_daily_stats_report(daily_msgs, members, today_str)
    weekly_stats = generate_weekly_stats_report(weekly_msgs, members, week_start_str, today_str)
    monthly_stats = generate_monthly_stats_report(monthly_msgs, members, month_start_str, today_str)
    
    print("📊 生成群会议纪要报告...")
    daily_meeting = generate_daily_meeting_report(daily_msgs, members, today_str)
    weekly_meeting = generate_weekly_meeting_report(weekly_msgs, members, week_start_str, today_str)
    monthly_meeting = generate_monthly_meeting_report(monthly_msgs, members, month_start_str, today_str)
    
    print("\n📤 发送报告到测试群...")
    
    reports = [
        ("群消息统计日报", daily_stats),
        ("群消息统计周报", weekly_stats),
        ("群消息统计月报", monthly_stats),
        ("群会议纪要日报", daily_meeting),
        ("群会议纪要周报", weekly_meeting),
        ("群会议纪要月报", monthly_meeting),
    ]
    
    for name, report in reports:
        if send_message(token, TEST_GROUP_ID, report):
            print(f"  ✅ {name} 发送成功")
        else:
            print(f"  ❌ {name} 发送失败")
        time.sleep(1)
    
    print("\n" + "=" * 60)
    print("🎉 所有报告发送完成！")

if __name__ == "__main__":
    main()

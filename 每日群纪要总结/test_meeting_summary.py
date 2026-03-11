#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试群会议纪要机器人的日报、周报、月报功能
使用英璨市场部大群的真实数据，发送到张贤良测试群
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from 群会议纪要_最终版 import *

def generate_meeting_summary(token, chat_id, chat_name, summary_type="daily"):
    """生成会议纪要，使用正确的格式"""
    print(f"\n{'='*60}")
    print(f"🚀 处理群：{chat_name}")
    print(f"{'='*60}\n")
    
    members_map = get_group_members(token, chat_id)
    print(f"✅ 获取到 {len(members_map)} 位群成员\n")
    
    now = datetime.now()
    
    if summary_type == "daily":
        start_time = now - timedelta(hours=24)
        end_time = now
        title = f"📅 每日群会议纪要 ({now.strftime('%Y-%m-%d')})"
        time_desc = "最近24小时"
        date_range = now.strftime('%Y-%m-%d')
    elif summary_type == "weekly":
        start_time = now - timedelta(days=7)
        end_time = now
        title = f"📊 每周群会议纪要 ({(now - timedelta(days=7)).strftime('%Y-%m-%d')} ~ {now.strftime('%Y-%m-%d')})"
        time_desc = "最近7天"
        date_range = f"{(now - timedelta(days=7)).strftime('%Y-%m-%d')} ~ {now.strftime('%Y-%m-%d')}"
    else:
        start_time = now - timedelta(days=30)
        end_time = now
        title = f"📈 每月群会议纪要 ({(now - timedelta(days=30)).strftime('%Y-%m')})"
        time_desc = "最近30天"
        date_range = (now - timedelta(days=30)).strftime('%Y-%m')
    
    start_ts = int(start_time.timestamp() * 1000)
    end_ts = int(end_time.timestamp() * 1000)
    
    messages = get_messages_by_time_range(token, chat_id, start_ts, end_ts)
    print(f"✅ 获取到 {len(messages)} 条消息（{time_desc}）\n")
    
    records = extract_chat_records(messages, members_map)
    print(f"✅ 提取到 {len(records)} 条文本消息\n")
    
    if len(records) < 3:
        print(f"⏭️ 消息数量({len(records)})少于阈值(3)，跳过\n")
        return None
    
    # 使用local_summarize生成正确的会议纪要格式
    chat_text = format_chat_text(records)
    ai_summary_result = local_summarize(chat_text, summary_type, chat_name, date_range, len(records))
    
    if not ai_summary_result:
        print("❌ 总结失败\n")
        return None
    
    if isinstance(ai_summary_result, dict):
        if not ai_summary_result.get("success"):
            print("❌ 总结生成失败\n")
            return None
        ai_summary = ai_summary_result.get("content", "")
    else:
        ai_summary = ai_summary_result
    
    if not ai_summary or len(ai_summary) < 50:
        print("❌ 总结内容过短或为空\n")
        return None
    
    print("✅ 总结成功！\n")
    
    footer = f"⏰ 生成时间：{now.strftime('%Y-%m-%d %H:%M:%S')}\n🤖 由{BOT_NAME}机器人自动生成"
    
    message_content = f"""{title}

{ai_summary}

{footer}"""
    
    return message_content

def test_meeting_summary():
    """测试会议纪要功能"""
    print("🚀 测试群会议纪要机器人")
    print("=" * 60)
    
    # 获取token
    token = get_feishu_token()
    if not token:
        print("❌ 获取token失败")
        return
    
    # 目标群：英璨市场部大群
    target_group_id = "oc_48e2db5c69667ddfe1a50331939f98e1"
    target_group_name = "英璨市场部大群"
    
    # 测试群：张贤良测试群
    test_group_id = "oc_3ea67ec60886f42c15e632954f08bb08"
    test_group_name = "张贤良测试群"
    
    print(f"\n🎯 目标群：{target_group_name}")
    print(f"📧 发送到：{test_group_name}")
    
    # 测试日报
    print("\n" + "="*60)
    print("📅 测试日报")
    print("="*60)
    
    summary = generate_meeting_summary(token, target_group_id, target_group_name, "daily")
    if summary:
        print(f"\n📤 发送日报到测试群...")
        success = send_message_to_group(token, test_group_id, summary)
        if success:
            print("✅ 日报发送成功！")
        else:
            print("❌ 日报发送失败！")
    else:
        print("⏭️ 日报生成失败")
    
    # 测试周报
    print("\n" + "="*60)
    print("📅 测试周报")
    print("="*60)
    
    summary = generate_meeting_summary(token, target_group_id, target_group_name, "weekly")
    if summary:
        print(f"\n📤 发送周到测试群...")
        success = send_message_to_group(token, test_group_id, summary)
        if success:
            print("✅ 周报发送成功！")
        else:
            print("❌ 周报发送失败！")
    else:
        print("⏭️ 周报生成失败")
    
    # 测试月报
    print("\n" + "="*60)
    print("📅 测试月报")
    print("="*60)
    
    summary = generate_meeting_summary(token, target_group_id, target_group_name, "monthly")
    if summary:
        print(f"\n📤 发送月报到测试群...")
        success = send_message_to_group(token, test_group_id, summary)
        if success:
            print("✅ 月报发送成功！")
        else:
            print("❌ 月报发送失败！")
    else:
        print("⏭️ 月报生成失败")
    
    print("\n" + "="*60)
    print("🎉 测试完成！")
    print("="*60)

if __name__ == "__main__":
    test_meeting_summary()

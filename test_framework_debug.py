#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
调试版本 - 检查两个机器人的token和身份
"""

import sys
import os

meeting_bot_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "每日群纪要总结")
stats_bot_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "飞书统计群成员消息数")

sys.path.insert(0, meeting_bot_path)
sys.path.insert(0, stats_bot_path)

# 导入两个机器人的配置
from 每日群纪要总结 import config as meeting_config
from 飞书统计群成员消息数 import config as stats_config

from 群会议纪要_最终版 import get_feishu_token as get_meeting_token
from 多群统计 import get_tenant_token as get_stats_token

print("=" * 80)
print("🔍 调试：检查两个机器人的配置和Token")
print("=" * 80)

print("\n📋 群会议纪要机器人配置：")
print(f"   App ID: {meeting_config.FEISHU_APP_ID}")
print(f"   App Secret: {meeting_config.FEISHU_APP_SECRET[:10]}...")

print("\n📋 群消息统计机器人配置：")
print(f"   App ID: {stats_config.FEISHU_APP_ID}")
print(f"   App Secret: {stats_config.FEISHU_APP_SECRET[:10]}...")

print("\n" + "=" * 80)
print("🔍 获取Token并验证")
print("=" * 80)

meeting_token = get_meeting_token()
if meeting_token:
    print(f"\n✅ 群会议纪要机器人Token获取成功")
    print(f"   Token: {meeting_token[:20]}...")
else:
    print(f"\n❌ 群会议纪要机器人Token获取失败")

stats_token = get_stats_token()
if stats_token:
    print(f"\n✅ 群消息统计机器人Token获取成功")
    print(f"   Token: {stats_token[:20]}...")
else:
    print(f"\n❌ 群消息统计机器人Token获取失败")

print("\n" + "=" * 80)
print("🔍 检查两个Token是否相同")
print("=" * 80)

if meeting_token and stats_token:
    if meeting_token == stats_token:
        print("\n⚠️ 警告：两个Token相同！")
        print("   这意味着两个机器人使用了同一个身份")
    else:
        print("\n✅ 两个Token不同，身份正确区分")
        print(f"   群会议纪要Token前20位: {meeting_token[:20]}...")
        print(f"   群消息统计Token前20位: {stats_token[:20]}...")

print("\n" + "=" * 80)
print("🔍 建议检查")
print("=" * 80)
print("""
如果两个Token不同，但消息仍显示同一个机器人发送，请检查：

1. 群消息统计机器人是否已加入"张贤良测试群"
   - 在飞书群中查看机器人列表
   - 确认"群消息统计"机器人在群中

2. 群消息统计机器人的权限
   - 检查机器人是否有发送消息权限
   - 检查机器人是否被禁言

3. 飞书API缓存
   - 可能需要等待几分钟
   - 或者重新添加机器人到群中

4. 正式版本检查
   - 检查正式版本是否也存在同样问题
   - 如果正式版本正常，只是测试版本有问题，可能是测试环境问题
""")

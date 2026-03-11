#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
验证两个机器人应用的信息
"""

import requests
import json

NO_PROXY = {}

# 群会议纪要机器人
MEETING_APP_ID = "cli_a9233dfe18389bde"
MEETING_APP_SECRET = "8gvZm8C04sS0GJXtDQdkkeAOJV6gCr4w"

# 群消息统计机器人
STATS_APP_ID = "cli_a92aab4685f9dbc7"
STATS_APP_SECRET = "kjoKDg6QN3fcR58IvLj8WeK3YwkRwsXO"

def get_app_info(app_id, app_secret):
    """获取应用信息"""
    url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
    data = {"app_id": app_id, "app_secret": app_secret}
    resp = requests.post(url, json=data, proxies=NO_PROXY).json()
    return resp

def get_bot_info(token):
    """获取机器人信息"""
    url = "https://open.feishu.cn/open-apis/bot/v3/info"
    headers = {"Authorization": f"Bearer {token}"}
    resp = requests.get(url, headers=headers, proxies=NO_PROXY).json()
    return resp

print("=" * 80)
print("🔍 验证两个机器人应用")
print("=" * 80)

print("\n📋 群会议纪要机器人：")
print(f"   App ID: {MEETING_APP_ID}")
meeting_resp = get_app_info(MEETING_APP_ID, MEETING_APP_SECRET)
print(f"   响应: {json.dumps(meeting_resp, indent=2, ensure_ascii=False)}")

print("\n📋 群消息统计机器人：")
print(f"   App ID: {STATS_APP_ID}")
stats_resp = get_app_info(STATS_APP_ID, STATS_APP_SECRET)
print(f"   响应: {json.dumps(stats_resp, indent=2, ensure_ascii=False)}")

print("\n" + "=" * 80)
print("🔍 获取机器人信息")
print("=" * 80)

if meeting_resp.get("tenant_access_token"):
    meeting_token = meeting_resp["tenant_access_token"]
    print("\n📋 群会议纪要机器人信息：")
    meeting_bot_info = get_bot_info(meeting_token)
    print(f"   {json.dumps(meeting_bot_info, indent=2, ensure_ascii=False)}")

if stats_resp.get("tenant_access_token"):
    stats_token = stats_resp["tenant_access_token"]
    print("\n📋 群消息统计机器人信息：")
    stats_bot_info = get_bot_info(stats_token)
    print(f"   {json.dumps(stats_bot_info, indent=2, ensure_ascii=False)}")

print("\n" + "=" * 80)
print("🔍 结论")
print("=" * 80)

if meeting_resp.get("tenant_access_token") == stats_resp.get("tenant_access_token"):
    print("""
⚠️ 两个应用获取到的token相同！

这是飞书API的正常行为：
- tenant_access_token是基于租户（企业）的，不是基于应用的
- 同一个企业下的所有应用，获取到的tenant_access_token是相同的

但是，不同的应用应该有不同的机器人身份。
如果消息都显示同一个机器人发送，可能原因：

1. 两个应用实际上是同一个机器人
2. 群消息统计机器人没有正确添加到测试群
3. 飞书后台配置问题

建议检查：
1. 在飞书开放平台确认两个App ID对应不同的应用
2. 在测试群中确认两个机器人都已添加
3. 检查飞书后台的机器人配置
""")
else:
    print("✅ 两个应用获取到的token不同，身份应该正确区分")

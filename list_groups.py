#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
查看两个机器人加入的群列表
"""

import sys
import os
import requests
import json

NO_PROXY = {}

# 机器人配置
MEETING_APP_ID = "cli_a9233dfe18389bde"
MEETING_APP_SECRET = "8gvZm8C04sS0GJXtDQdkkeAOJV6gCr4w"

STATS_APP_ID = "cli_a92aab4685f9dbc7"
STATS_APP_SECRET = "kjoKDg6QN3fcR58IvLj8WeK3YwkRwsXO"

def get_token(app_id, app_secret):
    url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
    data = {"app_id": app_id, "app_secret": app_secret}
    resp = requests.post(url, json=data, proxies=NO_PROXY).json()
    return resp.get("tenant_access_token")

def get_bot_groups(token):
    url = "https://open.feishu.cn/open-apis/im/v1/chats"
    headers = {"Authorization": f"Bearer {token}"}
    params = {"page_size": 100}
    resp = requests.get(url, headers=headers, params=params, proxies=NO_PROXY).json()
    return resp.get("data", {}).get("items", [])

def main():
    print("=" * 80)
    print("🤖 查看两个机器人加入的群列表")
    print("=" * 80)
    
    # 获取群会议纪要机器人的群列表
    print("\n" + "=" * 80)
    print("📋 群会议纪要机器人加入的群列表")
    print("=" * 80)
    
    meeting_token = get_token(MEETING_APP_ID, MEETING_APP_SECRET)
    if meeting_token:
        meeting_groups = get_bot_groups(meeting_token)
        print(f"✅ 共加入 {len(meeting_groups)} 个群\n")
        for i, group in enumerate(meeting_groups, 1):
            print(f"  {i}. {group.get('name', '未知群')}")
            print(f"     群ID: {group.get('chat_id', 'N/A')}")
            print()
    else:
        print("❌ 获取token失败")
    
    # 获取群消息统计机器人的群列表
    print("\n" + "=" * 80)
    print("📋 群消息统计机器人加入的群列表")
    print("=" * 80)
    
    stats_token = get_token(STATS_APP_ID, STATS_APP_SECRET)
    if stats_token:
        stats_groups = get_bot_groups(stats_token)
        print(f"✅ 共加入 {len(stats_groups)} 个群\n")
        for i, group in enumerate(stats_groups, 1):
            print(f"  {i}. {group.get('name', '未知群')}")
            print(f"     群ID: {group.get('chat_id', 'N/A')}")
            print()
    else:
        print("❌ 获取token失败")

if __name__ == "__main__":
    main()

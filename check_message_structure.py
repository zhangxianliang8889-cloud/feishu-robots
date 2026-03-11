#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
检查消息数据结构，看看是否包含发送者名称
"""

import sys
import os
import requests
import json

NO_PROXY = {}

# 使用群消息统计机器人的token
STATS_APP_ID = "cli_a92aab4685f9dbc7"
STATS_APP_SECRET = "kjoKDg6QN3fcR58IvLj8WeK3YwkRwsXO"

def get_token():
    url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
    data = {"app_id": STATS_APP_ID, "app_secret": STATS_APP_SECRET}
    resp = requests.post(url, json=data, proxies=NO_PROXY).json()
    return resp.get("tenant_access_token")

def get_bot_groups(token):
    url = "https://open.feishu.cn/open-apis/im/v1/chats"
    headers = {"Authorization": f"Bearer {token}"}
    params = {"page_size": 100}
    resp = requests.get(url, headers=headers, params=params, proxies=NO_PROXY).json()
    return resp.get("data", {}).get("items", [])

def get_messages(token, group_id, limit=10):
    url = "https://open.feishu.cn/open-apis/im/v1/messages"
    headers = {"Authorization": f"Bearer {token}"}
    params = {
        "container_id_type": "chat",
        "container_id": group_id,
        "page_size": str(limit)
    }
    resp = requests.get(url, headers=headers, params=params, proxies=NO_PROXY).json()
    return resp.get("data", {}).get("items", [])

def main():
    print("=" * 80)
    print("🔍 检查消息数据结构")
    print("=" * 80)
    
    token = get_token()
    if not token:
        print("❌ 获取token失败")
        return
    
    groups = get_bot_groups(token)
    
    # 找到项目市场二部群
    target_group_id = None
    for group in groups:
        if group.get("name") == "项目市场二部":
            target_group_id = group.get("chat_id")
            break
    
    if not target_group_id:
        print("❌ 未找到项目市场二部群")
        return
    
    print(f"\n✅ 找到项目市场二部群: {target_group_id}")
    
    # 获取消息
    messages = get_messages(token, target_group_id, limit=20)
    
    print(f"\n✅ 获取到 {len(messages)} 条消息")
    
    # 检查消息结构
    print("\n" + "=" * 80)
    print("📋 消息数据结构示例")
    print("=" * 80)
    
    for i, msg in enumerate(messages[:5], 1):
        print(f"\n消息 {i}:")
        print(f"  完整消息结构: {json.dumps(msg, indent=2, ensure_ascii=False)}")
        
        sender_info = msg.get("sender", {})
        print(f"\n  sender字段: {json.dumps(sender_info, indent=2, ensure_ascii=False)}")
        
        # 检查是否有其他字段包含用户名
        print(f"\n  所有字段: {list(msg.keys())}")

if __name__ == "__main__":
    main()

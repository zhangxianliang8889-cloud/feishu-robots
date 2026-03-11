#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
调试：检查群成员信息和消息发送者ID的格式
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

def get_group_members(token, group_id):
    url = f"https://open.feishu.cn/open-apis/im/v1/chats/{group_id}/members"
    headers = {"Authorization": f"Bearer {token}"}
    params = {"page_size": 100}
    resp = requests.get(url, headers=headers, params=params, proxies=NO_PROXY).json()
    return resp.get("data", {}).get("items", [])

def get_messages(token, group_id):
    url = "https://open.feishu.cn/open-apis/im/v1/messages"
    headers = {"Authorization": f"Bearer {token}"}
    params = {
        "container_id_type": "chat",
        "container_id": group_id,
        "page_size": "10"
    }
    resp = requests.get(url, headers=headers, params=params, proxies=NO_PROXY).json()
    return resp.get("data", {}).get("items", [])

def main():
    print("=" * 80)
    print("🔍 调试：检查群成员信息和消息发送者ID的格式")
    print("=" * 80)
    
    token = get_token()
    if not token:
        print("❌ 获取token失败")
        return
    
    groups = get_bot_groups(token)
    
    # 找到策划二部群
    target_group_id = None
    for group in groups:
        if group.get("name") == "策划二部":
            target_group_id = group.get("chat_id")
            break
    
    if not target_group_id:
        print("❌ 未找到策划二部群")
        return
    
    print(f"\n✅ 找到策划二部群: {target_group_id}")
    
    # 获取群成员信息
    print("\n" + "=" * 80)
    print("📋 群成员信息示例（前5个）")
    print("=" * 80)
    
    members = get_group_members(token, target_group_id)
    for i, member in enumerate(members[:5]):
        print(f"\n成员 {i+1}:")
        print(f"  完整信息: {json.dumps(member, indent=2, ensure_ascii=False)}")
        print(f"  member_id: {member.get('member_id', 'N/A')}")
        print(f"  name: {member.get('name', 'N/A')}")
    
    # 获取消息信息
    print("\n" + "=" * 80)
    print("📋 消息发送者信息示例（前5条）")
    print("=" * 80)
    
    messages = get_messages(token, target_group_id)
    for i, msg in enumerate(messages[:5]):
        sender_info = msg.get("sender", {})
        print(f"\n消息 {i+1}:")
        print(f"  sender完整信息: {json.dumps(sender_info, indent=2, ensure_ascii=False)}")
        print(f"  sender_id: {sender_info.get('id', 'N/A')}")
        print(f"  sender_type: {sender_info.get('sender_type', 'N/A')}")
    
    # 对比分析
    print("\n" + "=" * 80)
    print("🔍 对比分析")
    print("=" * 80)
    
    member_ids = [m.get("member_id") for m in members]
    sender_ids = [msg.get("sender", {}).get("id") for msg in messages]
    
    print(f"\n群成员ID格式示例: {member_ids[:3]}")
    print(f"消息发送者ID格式示例: {sender_ids[:3]}")
    
    # 检查是否匹配
    matched = 0
    for sender_id in sender_ids:
        if sender_id in member_ids:
            matched += 1
    
    print(f"\n匹配情况: {matched}/{len(sender_ids)} 个发送者ID能在成员列表中找到")
    
    if matched == 0:
        print("\n⚠️ 问题：发送者ID和成员ID格式不匹配！")
        print("   可能原因：")
        print("   1. 成员列表返回的是member_id")
        print("   2. 消息发送者返回的是open_id")
        print("   3. 需要使用open_id作为key来匹配")
    else:
        print("\n✅ 发送者ID和成员ID格式匹配")

if __name__ == "__main__":
    main()

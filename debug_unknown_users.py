#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
调试：检查未知用户的完整信息
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
    
    all_members = []
    page_token = None
    
    while True:
        if page_token:
            params["page_token"] = page_token
        
        resp = requests.get(url, headers=headers, params=params, proxies=NO_PROXY).json()
        
        if resp.get("code") != 0:
            break
        
        data = resp.get("data", {})
        members = data.get("items", [])
        all_members.extend(members)
        
        if not data.get("has_more", False):
            break
        
        page_token = data.get("page_token")
    
    return all_members

def get_messages(token, group_id, limit=50):
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
    print("🔍 调试：检查未知用户的完整信息")
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
    members = get_group_members(token, target_group_id)
    member_map = {m.get("member_id"): m.get("name") for m in members}
    
    print(f"\n✅ 获取到 {len(members)} 位群成员")
    
    # 获取消息信息
    messages = get_messages(token, target_group_id, limit=50)
    
    print(f"✅ 获取到 {len(messages)} 条消息")
    
    # 找出所有不在成员列表中的发送者
    print("\n" + "=" * 80)
    print("🔍 检查不在成员列表中的发送者")
    print("=" * 80)
    
    unknown_senders = set()
    for msg in messages:
        sender_info = msg.get("sender", {})
        sender_id = sender_info.get("id", "")
        sender_type = sender_info.get("sender_type", "")
        
        if not sender_id or sender_type == "app" or sender_id.startswith("cli_"):
            continue
        
        if sender_id not in member_map:
            unknown_senders.add((sender_id, sender_type))
    
    if unknown_senders:
        print(f"\n⚠️ 发现 {len(unknown_senders)} 个不在成员列表中的发送者：")
        for sender_id, sender_type in unknown_senders:
            print(f"\n  发送者ID: {sender_id}")
            print(f"  发送者类型: {sender_type}")
            print(f"  是否以ou_开头: {sender_id.startswith('ou_')}")
            
            # 尝试获取用户信息
            if sender_id.startswith("ou_"):
                print(f"  这是一个open_id格式的用户ID")
                print(f"  可能是已退群用户或外部用户")
    else:
        print("\n✅ 所有发送者都在成员列表中")

if __name__ == "__main__":
    main()

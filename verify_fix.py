#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
验证修复：检查成员列表是否完整
"""

import sys
import os
import requests
import json
from collections import Counter

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

def count_messages(messages, members):
    member_map = {m.get("member_id"): m.get("name") for m in members}
    
    count = {}
    for msg in messages:
        sender_info = msg.get("sender", {})
        sender_id = sender_info.get("id", "")
        sender_type = sender_info.get("sender_type", "")
        
        if not sender_id or sender_type == "app" or sender_id.startswith("cli_"):
            continue
        
        sender_name = member_map.get(sender_id)
        if not sender_name:
            if sender_id.startswith("ou_"):
                sender_name = f"未知用户({sender_id[-8:]})"
            else:
                sender_name = "未知"
        
        if "机器人" in sender_name or sender_name.startswith("cli_"):
            continue
        
        count[sender_name] = count.get(sender_name, 0) + 1
    
    return count

def main():
    print("=" * 80)
    print("🔍 验证修复：检查成员列表是否完整")
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
    print("📋 群成员信息")
    print("=" * 80)
    
    members = get_group_members(token, target_group_id)
    print(f"✅ 获取到 {len(members)} 位群成员")
    
    member_map = {m.get("member_id"): m.get("name") for m in members}
    
    print("\n成员列表：")
    for i, (member_id, name) in enumerate(member_map.items(), 1):
        print(f"  {i}. {name} ({member_id})")
    
    # 获取消息信息
    print("\n" + "=" * 80)
    print("📋 消息统计")
    print("=" * 80)
    
    messages = get_messages(token, target_group_id, limit=50)
    print(f"✅ 获取到 {len(messages)} 条消息")
    
    count = count_messages(messages, members)
    sorted_count = sorted(count.items(), key=lambda x: x[1], reverse=True)
    
    print("\n消息统计：")
    for i, (name, cnt) in enumerate(sorted_count, 1):
        print(f"  {i}. {name}: {cnt}条")
    
    # 检查是否有未知用户
    print("\n" + "=" * 80)
    print("🔍 检查是否有未知用户")
    print("=" * 80)
    
    unknown_users = [name for name in count.keys() if "未知用户" in name or name == "未知"]
    
    if unknown_users:
        print(f"⚠️ 发现 {len(unknown_users)} 个未知用户：")
        for user in unknown_users:
            print(f"  - {user}")
    else:
        print("✅ 没有未知用户，所有发送者都能正确匹配到成员名")

if __name__ == "__main__":
    main()

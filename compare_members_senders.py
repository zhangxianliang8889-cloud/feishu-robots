#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
详细对比成员列表和发送者列表
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

def get_all_messages(token, group_id):
    """获取所有消息"""
    url = "https://open.feishu.cn/open-apis/im/v1/messages"
    headers = {"Authorization": f"Bearer {token}"}
    
    all_messages = []
    page_token = None
    
    while True:
        params = {
            "container_id_type": "chat",
            "container_id": group_id,
            "page_size": "50"
        }
        
        if page_token:
            params["page_token"] = page_token
        
        resp = requests.get(url, headers=headers, params=params, proxies=NO_PROXY).json()
        
        if resp.get("code") != 0:
            break
        
        data = resp.get("data", {})
        messages = data.get("items", [])
        all_messages.extend(messages)
        
        if not data.get("has_more", False):
            break
        
        page_token = data.get("page_token")
    
    return all_messages

def main():
    print("=" * 80)
    print("🔍 详细对比成员列表和发送者列表")
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
    
    # 获取群成员信息
    print("\n" + "=" * 80)
    print("📋 群成员信息")
    print("=" * 80)
    
    members = get_group_members(token, target_group_id)
    member_map = {m.get("member_id"): m.get("name") for m in members}
    
    print(f"✅ 获取到 {len(members)} 位群成员\n")
    
    for i, (member_id, name) in enumerate(member_map.items(), 1):
        print(f"  {i}. {name} ({member_id})")
    
    # 获取所有消息
    print("\n" + "=" * 80)
    print("📋 获取所有消息")
    print("=" * 80)
    
    messages = get_all_messages(token, target_group_id)
    print(f"✅ 获取到 {len(messages)} 条消息")
    
    # 统计发送者
    print("\n" + "=" * 80)
    print("📊 发送者统计")
    print("=" * 80)
    
    sender_count = Counter()
    unknown_senders = {}
    
    for msg in messages:
        sender_info = msg.get("sender", {})
        sender_id = sender_info.get("id", "")
        sender_type = sender_info.get("sender_type", "")
        
        if not sender_id or sender_type == "app" or sender_id.startswith("cli_"):
            continue
        
        sender_name = member_map.get(sender_id)
        if sender_name:
            sender_count[sender_name] += 1
        else:
            if sender_id not in unknown_senders:
                unknown_senders[sender_id] = 0
            unknown_senders[sender_id] += 1
    
    # 显示已知用户
    print("\n✅ 已知用户：")
    for i, (name, count) in enumerate(sender_count.most_common(), 1):
        print(f"  {i}. {name}: {count}条")
    
    # 显示未知用户
    print(f"\n⚠️ 未知用户（{len(unknown_senders)}个）：")
    for i, (sender_id, count) in enumerate(sorted(unknown_senders.items(), key=lambda x: x[1], reverse=True), 1):
        print(f"  {i}. {sender_id}: {count}条")
    
    # 检查成员列表是否完整
    print("\n" + "=" * 80)
    print("🔍 检查成员列表是否完整")
    print("=" * 80)
    
    # 检查是否有分页
    url = f"https://open.feishu.cn/open-apis/im/v1/chats/{target_group_id}/members"
    headers = {"Authorization": f"Bearer {token}"}
    params = {"page_size": 100}
    
    resp = requests.get(url, headers=headers, params=params, proxies=NO_PROXY).json()
    
    print(f"\nAPI响应：")
    print(f"  code: {resp.get('code')}")
    print(f"  msg: {resp.get('msg')}")
    print(f"  has_more: {resp.get('data', {}).get('has_more', False)}")
    print(f"  返回成员数: {len(resp.get('data', {}).get('items', []))}")
    
    # 检查是否有更多成员
    if resp.get('data', {}).get('has_more', False):
        print("\n⚠️ 成员列表有更多数据，需要分页获取！")
    else:
        print("\n✅ 成员列表已完整获取")

if __name__ == "__main__":
    main()

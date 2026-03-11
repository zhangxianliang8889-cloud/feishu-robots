#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
深度调试：获取未知用户的真实身份
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

def get_user_info(token, user_id):
    """获取用户详细信息"""
    url = "https://open.feishu.cn/open-apis/contact/v3/users/batch_get_id"
    headers = {"Authorization": f"Bearer {token}"}
    params = {
        "emails": "",
        "mobiles": "",
        "user_ids": user_id
    }
    resp = requests.get(url, headers=headers, params=params, proxies=NO_PROXY).json()
    return resp

def get_user_info_by_open_id(token, open_id):
    """通过open_id获取用户信息"""
    url = f"https://open.feishu.cn/open-apis/contact/v3/users/{open_id}"
    headers = {"Authorization": f"Bearer {token}"}
    params = {"user_id_type": "open_id"}
    resp = requests.get(url, headers=headers, params=params, proxies=NO_PROXY).json()
    return resp

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
    print("🔍 深度调试：获取未知用户的真实身份")
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
    
    print(f"✅ 获取到 {len(members)} 位群成员")
    
    # 获取所有消息
    print("\n" + "=" * 80)
    print("📋 获取所有消息")
    print("=" * 80)
    
    messages = get_all_messages(token, target_group_id)
    print(f"✅ 获取到 {len(messages)} 条消息")
    
    # 找出所有不在成员列表中的发送者
    print("\n" + "=" * 80)
    print("🔍 检查不在成员列表中的发送者")
    print("=" * 80)
    
    unknown_senders = {}
    for msg in messages:
        sender_info = msg.get("sender", {})
        sender_id = sender_info.get("id", "")
        sender_type = sender_info.get("sender_type", "")
        
        if not sender_id or sender_type == "app" or sender_id.startswith("cli_"):
            continue
        
        if sender_id not in member_map:
            if sender_id not in unknown_senders:
                unknown_senders[sender_id] = 0
            unknown_senders[sender_id] += 1
    
    if unknown_senders:
        print(f"\n⚠️ 发现 {len(unknown_senders)} 个不在成员列表中的发送者：\n")
        
        for i, (sender_id, count) in enumerate(unknown_senders.items(), 1):
            print(f"{i}. 发送者ID: {sender_id}")
            print(f"   消息数: {count}条")
            
            # 尝试获取用户信息
            print(f"   正在获取用户信息...")
            user_info = get_user_info_by_open_id(token, sender_id)
            
            if user_info.get("code") == 0:
                user_data = user_info.get("data", {}).get("user", {})
                user_name = user_data.get("name", "未知")
                print(f"   ✅ 用户名: {user_name}")
                print(f"   用户详细信息: {json.dumps(user_data, indent=2, ensure_ascii=False)}")
            else:
                print(f"   ❌ 获取失败: {user_info.get('msg', '未知错误')}")
                print(f"   错误详情: {json.dumps(user_info, indent=2, ensure_ascii=False)}")
            
            print()
    else:
        print("\n✅ 所有发送者都在成员列表中")

if __name__ == "__main__":
    main()

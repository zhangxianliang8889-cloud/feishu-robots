#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
从系统消息中提取用户名
"""

import sys
import os
import requests
import json
from datetime import datetime

NO_PROXY = {}

# 使用群消息统计机器人的token
STATS_APP_ID = "cli_a92aab4685f9dbc7"
STATS_APP_SECRET = "kjoKDg6QN3fcR58IvLj8WeK3YwkRwsXO"

# 未知用户列表
unknown_users = [
    "ou_7b676a09e299759b0b9a1bcb9abf03e5",
    "ou_bf1ac932c4ed35a0182854860b3533a2",
    "ou_8b66227bbe65f564292bed7df60635f9",
    "ou_e290b3293228299ff50e3c6794aa2a23",
    "ou_499438af277a590126e8e037f977afbe"
]

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

def find_user_in_messages(messages, target_user_id):
    """在消息中查找用户"""
    for msg in messages:
        sender_info = msg.get("sender", {})
        sender_id = sender_info.get("id", "")
        
        if sender_id == target_user_id:
            return msg
    
    return None

def main():
    print("=" * 80)
    print("🔍 从系统消息中提取用户名")
    print("=" * 80)
    
    token = get_token()
    if not token:
        print("❌ 获取token失败")
        return
    
    groups = get_bot_groups(token)
    
    for user_id in unknown_users:
        print(f"\n{'='*80}")
        print(f"🔍 查找用户: {user_id}")
        print(f"{'='*80}")
        
        found = False
        for group in groups:
            group_name = group.get("name")
            group_id = group.get("chat_id")
            
            messages = get_all_messages(token, group_id)
            msg = find_user_in_messages(messages, user_id)
            
            if msg:
                print(f"\n✅ 在群【{group_name}】中找到该用户的消息")
                print(f"   消息类型: {msg.get('msg_type')}")
                print(f"   消息内容: {msg.get('body', {}).get('content', '')[:100]}")
                print(f"   发送时间: {datetime.fromtimestamp(int(msg.get('create_time', 0))//1000).strftime('%Y-%m-%d %H:%M:%S')}")
                found = True
                break
        
        if not found:
            print(f"\n❌ 在所有群中都没有找到该用户的消息")

if __name__ == "__main__":
    main()

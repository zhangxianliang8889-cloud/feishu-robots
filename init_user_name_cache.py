#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
初始化用户名缓存 - 从历史消息中提取用户名
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

def extract_user_names_from_messages(messages):
    """从消息中提取用户名"""
    user_names = {}
    
    for msg in messages:
        msg_type = msg.get("msg_type")
        body = msg.get("body", {})
        content_str = body.get("content", "{}")
        
        if msg_type == "system":
            try:
                content = json.loads(content_str)
                from_user = content.get("from_user", [])
                
                for user_name in from_user:
                    if user_name and user_name not in ["未知", ""]:
                        user_names[user_name] = {
                            "name": user_name,
                            "last_seen": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                            "status": "active",
                            "source": "system_message"
                        }
            except:
                pass
    
    return user_names

def main():
    print("=" * 80)
    print("🔍 初始化用户名缓存 - 从历史消息中提取用户名")
    print("=" * 80)
    
    token = get_token()
    if not token:
        print("❌ 获取token失败")
        return
    
    groups = get_bot_groups(token)
    
    all_user_names = {}
    
    for group in groups:
        group_name = group.get("name")
        group_id = group.get("chat_id")
        
        print(f"\n处理群组: {group_name}")
        
        messages = get_all_messages(token, group_id)
        print(f"  获取到 {len(messages)} 条消息")
        
        user_names = extract_user_names_from_messages(messages)
        print(f"  提取到 {len(user_names)} 个用户名")
        
        all_user_names.update(user_names)
    
    # 保存缓存
    cache_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "飞书统计群成员消息数", "user_name_cache.json")
    
    with open(cache_file, 'w', encoding='utf-8') as f:
        json.dump(all_user_names, f, ensure_ascii=False, indent=2)
    
    print(f"\n✅ 缓存已保存到: {cache_file}")
    print(f"✅ 共提取到 {len(all_user_names)} 个用户名")
    
    print("\n用户名列表：")
    for i, (user_id, info) in enumerate(all_user_names.items(), 1):
        print(f"  {i}. {info.get('name')}")

if __name__ == "__main__":
    main()

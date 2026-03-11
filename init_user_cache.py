#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
初始化用户名缓存 - 从所有群的成员列表中收集
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

def main():
    print("=" * 80)
    print("🔍 初始化用户名缓存 - 从所有群的成员列表中收集")
    print("=" * 80)
    
    token = get_token()
    if not token:
        print("❌ 获取token失败")
        return
    
    groups = get_bot_groups(token)
    
    all_users = {}
    
    for group in groups:
        group_name = group.get("name")
        group_id = group.get("chat_id")
        
        print(f"\n处理群组: {group_name}")
        
        members = get_group_members(token, group_id)
        print(f"  获取到 {len(members)} 位成员")
        
        for member in members:
            member_id = member.get("member_id", "")
            name = member.get("name", "")
            
            if member_id and name:
                all_users[member_id] = {
                    "name": name,
                    "last_seen": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    "status": "active",
                    "source_group": group_name
                }
    
    # 保存缓存
    cache_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "飞书统计群成员消息数")
    cache_file = os.path.join(cache_dir, "user_name_cache.json")
    
    os.makedirs(cache_dir, exist_ok=True)
    
    with open(cache_file, 'w', encoding='utf-8') as f:
        json.dump(all_users, f, ensure_ascii=False, indent=2)
    
    print(f"\n{'='*80}")
    print(f"✅ 缓存已保存到: {cache_file}")
    print(f"✅ 共收集到 {len(all_users)} 个用户")
    print(f"{'='*80}")
    
    print("\n用户名列表：")
    for i, (user_id, info) in enumerate(all_users.items(), 1):
        print(f"  {i}. {info.get('name')} ({user_id}) - 来源: {info.get('source_group')}")

if __name__ == "__main__":
    main()

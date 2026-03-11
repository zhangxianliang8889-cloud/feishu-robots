#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
获取机器人所在的群列表
"""

import requests
import json
import time

# 飞书API相关
APP_ID = "cli_a9233dfe18389bde"
APP_SECRET = "8gvZm8C04sS0GJXtDQdkkeAOJV6gCr4w"

def get_access_token():
    """获取飞书访问令牌"""
    url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal/"
    headers = {
        "Content-Type": "application/json"
    }
    data = {
        "app_id": APP_ID,
        "app_secret": APP_SECRET
    }
    
    try:
        response = requests.post(url, headers=headers, json=data, timeout=10)
        result = response.json()
        if result.get("code") == 0:
            return result.get("tenant_access_token")
        else:
            print(f"获取access_token失败: {result.get('msg')}")
            return None
    except Exception as e:
        print(f"获取access_token异常: {e}")
        return None

def get_groups():
    """获取机器人所在的群列表"""
    token = get_access_token()
    if not token:
        return []
    
    url = "https://open.feishu.cn/open-apis/im/v1/chats"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    params = {
        "page_size": 100,
        "page_token": ""
    }
    
    groups = []
    try:
        response = requests.get(url, headers=headers, params=params, timeout=10)
        result = response.json()
        if result.get("code") == 0:
            groups = result.get("data", {}).get("items", [])
    except Exception as e:
        print(f"获取群列表异常: {e}")
    
    return groups

def main():
    """主函数"""
    print("🚀 获取群列表...")
    groups = get_groups()
    print(f"📋 找到 {len(groups)} 个群")
    
    print("\n可用的群：")
    for i, group in enumerate(groups, 1):
        name = group.get("name")
        chat_id = group.get("chat_id")
        print(f"{i}. {name} (ID: {chat_id})")

if __name__ == "__main__":
    main()

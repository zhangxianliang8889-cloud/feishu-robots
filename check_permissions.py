#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
检查群会议纪要机器人是否有权限获取用户信息
"""

import sys
import os
import requests
import json

NO_PROXY = {}

# 群会议纪要机器人配置
MEETING_APP_ID = "cli_a9233dfe18389bde"
MEETING_APP_SECRET = "8gvZm8C04sS0GJXtDQdkkeAOJV6gCr4w"

# 群消息统计机器人配置
STATS_APP_ID = "cli_a92aab4685f9dbc7"
STATS_APP_SECRET = "kjoKDg6QN3fcR58IvLj8WeK3YwkRwsXO"

def get_token(app_id, app_secret):
    url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
    data = {"app_id": app_id, "app_secret": app_secret}
    resp = requests.post(url, json=data, proxies=NO_PROXY).json()
    return resp.get("tenant_access_token")

def get_user_info_by_open_id(token, open_id):
    """通过open_id获取用户信息"""
    url = f"https://open.feishu.cn/open-apis/contact/v3/users/{open_id}"
    headers = {"Authorization": f"Bearer {token}"}
    params = {"user_id_type": "open_id"}
    resp = requests.get(url, headers=headers, params=params, proxies=NO_PROXY).json()
    return resp

def main():
    print("=" * 80)
    print("🔍 检查两个机器人是否有权限获取用户信息")
    print("=" * 80)
    
    # 测试一个未知用户的open_id
    test_user_id = "ou_499438af277a590126e8e037f977afbe"
    
    # 测试群会议纪要机器人
    print("\n" + "=" * 80)
    print("🤖 测试群会议纪要机器人")
    print("=" * 80)
    
    meeting_token = get_token(MEETING_APP_ID, MEETING_APP_SECRET)
    if meeting_token:
        print(f"✅ 获取到Token: {meeting_token[:30]}...")
        
        user_info = get_user_info_by_open_id(meeting_token, test_user_id)
        
        if user_info.get("code") == 0:
            user_data = user_info.get("data", {}).get("user", {})
            user_name = user_data.get("name", "未知")
            print(f"✅ 成功获取用户信息: {user_name}")
            print(f"   用户详细信息: {json.dumps(user_data, indent=2, ensure_ascii=False)}")
        else:
            print(f"❌ 获取失败: {user_info.get('msg', '未知错误')}")
    else:
        print("❌ 获取token失败")
    
    # 测试群消息统计机器人
    print("\n" + "=" * 80)
    print("🤖 测试群消息统计机器人")
    print("=" * 80)
    
    stats_token = get_token(STATS_APP_ID, STATS_APP_SECRET)
    if stats_token:
        print(f"✅ 获取到Token: {stats_token[:30]}...")
        
        user_info = get_user_info_by_open_id(stats_token, test_user_id)
        
        if user_info.get("code") == 0:
            user_data = user_info.get("data", {}).get("user", {})
            user_name = user_data.get("name", "未知")
            print(f"✅ 成功获取用户信息: {user_name}")
            print(f"   用户详细信息: {json.dumps(user_data, indent=2, ensure_ascii=False)}")
        else:
            print(f"❌ 获取失败: {user_info.get('msg', '未知错误')}")
    else:
        print("❌ 获取token失败")

if __name__ == "__main__":
    main()

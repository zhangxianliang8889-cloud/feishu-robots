#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
检查API返回的完整用户信息
"""

import requests
import json

NO_PROXY = {}

# 群消息统计机器人配置
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

def get_user_info(token, open_id):
    """通过open_id获取用户信息"""
    url = f"https://open.feishu.cn/open-apis/contact/v3/users/{open_id}"
    headers = {"Authorization": f"Bearer {token}"}
    params = {"user_id_type": "open_id"}
    resp = requests.get(url, headers=headers, params=params, proxies=NO_PROXY).json()
    return resp

def main():
    print("=" * 80)
    print("🔍 检查API返回的完整用户信息")
    print("=" * 80)
    
    token = get_token()
    if not token:
        print("❌ 获取token失败")
        return
    
    print(f"✅ 获取到Token: {token[:30]}...\n")
    
    for i, user_id in enumerate(unknown_users[:2], 1):  # 只测试前2个
        print(f"\n{'='*80}")
        print(f"{i}. 用户ID: {user_id}")
        print(f"{'='*80}")
        
        user_info = get_user_info(token, user_id)
        
        print(f"\n完整响应:")
        print(json.dumps(user_info, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()

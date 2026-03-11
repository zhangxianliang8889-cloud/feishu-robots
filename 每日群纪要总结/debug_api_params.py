#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
调试脚本 - 检查API参数问题
"""

import sys
import os
import requests
import json
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import *

NO_PROXY = {}

def get_access_token():
    url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal/"
    data = {"app_id": FEISHU_APP_ID, "app_secret": FEISHU_APP_SECRET}
    try:
        resp = requests.post(url, json=data, timeout=10, proxies=NO_PROXY).json()
        if resp.get("code") == 0:
            return resp.get("tenant_access_token")
    except Exception as e:
        print(f"获取token失败: {e}")
    return None

def test_api_with_params(token, group_id):
    """测试不同的API参数组合"""
    
    now = datetime.now()
    start_ts = int((now - timedelta(days=7)).timestamp() * 1000)
    end_ts = int(now.timestamp() * 1000)
    
    url = "https://open.feishu.cn/open-apis/im/v1/messages"
    headers = {"Authorization": f"Bearer {token}"}
    
    print("=" * 60)
    print("测试1: 不带时间参数（获取所有消息）")
    print("=" * 60)
    
    params1 = {
        "container_id": group_id,
        "container_id_type": "chat",
        "page_size": 50
    }
    
    resp1 = requests.get(url, headers=headers, params=params1, timeout=10, proxies=NO_PROXY).json()
    print(f"code: {resp1.get('code')}")
    print(f"msg: {resp1.get('msg')}")
    print(f"items: {len(resp1.get('data', {}).get('items', []))}")
    
    print("\n" + "=" * 60)
    print("测试2: 带start_time和end_time参数")
    print("=" * 60)
    
    params2 = {
        "container_id": group_id,
        "container_id_type": "chat",
        "start_time": str(start_ts),
        "end_time": str(end_ts),
        "page_size": 50
    }
    
    print(f"start_time: {start_ts}")
    print(f"end_time: {end_ts}")
    
    resp2 = requests.get(url, headers=headers, params=params2, timeout=10, proxies=NO_PROXY).json()
    print(f"code: {resp2.get('code')}")
    print(f"msg: {resp2.get('msg')}")
    print(f"items: {len(resp2.get('data', {}).get('items', []))}")
    
    print("\n" + "=" * 60)
    print("测试3: 只带start_time参数")
    print("=" * 60)
    
    params3 = {
        "container_id": group_id,
        "container_id_type": "chat",
        "start_time": str(start_ts),
        "page_size": 50
    }
    
    resp3 = requests.get(url, headers=headers, params=params3, timeout=10, proxies=NO_PROXY).json()
    print(f"code: {resp3.get('code')}")
    print(f"msg: {resp3.get('msg')}")
    print(f"items: {len(resp3.get('data', {}).get('items', []))}")
    
    if resp3.get("code") == 0:
        items = resp3.get('data', {}).get('items', [])
        if items:
            print("\n前3条消息:")
            for i, msg in enumerate(items[:3], 1):
                create_time = msg.get("create_time")
                if create_time:
                    dt = datetime.fromtimestamp(int(create_time)/1000)
                    msg_type = msg.get("msg_type")
                    print(f"  {i}. [{msg_type}] {dt.strftime('%Y-%m-%d %H:%M:%S')}")

def main():
    print("🔍 API参数调试")
    print("=" * 60)
    
    token = get_access_token()
    if not token:
        print("❌ 获取token失败")
        return
    
    print("✅ 获取token成功")
    
    group_id = "oc_48e2db5c69667ddfe1a50331939f98e1"
    print(f"\n🎯 测试群: 英璨市场部大群")
    
    test_api_with_params(token, group_id)

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
调试脚本 - 检查消息时间
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

def main():
    print("🔍 消息时间分析")
    print("=" * 60)
    
    token = get_access_token()
    if not token:
        print("❌ 获取token失败")
        return
    
    print("✅ 获取token成功")
    
    group_id = "oc_48e2db5c69667ddfe1a50331939f98e1"
    
    url = "https://open.feishu.cn/open-apis/im/v1/messages"
    headers = {"Authorization": f"Bearer {token}"}
    params = {
        "container_id": group_id,
        "container_id_type": "chat",
        "page_size": 50
    }
    
    resp = requests.get(url, headers=headers, params=params, timeout=10, proxies=NO_PROXY).json()
    
    if resp.get("code") == 0:
        items = resp.get('data', {}).get('items', [])
        print(f"\n📊 获取到 {len(items)} 条消息")
        
        if items:
            print("\n📅 消息时间分布:")
            
            times = []
            for msg in items:
                create_time = msg.get("create_time")
                if create_time:
                    times.append(int(create_time))
            
            if times:
                times.sort()
                
                oldest = datetime.fromtimestamp(min(times)/1000)
                newest = datetime.fromtimestamp(max(times)/1000)
                
                print(f"  最早消息: {oldest.strftime('%Y-%m-%d %H:%M:%S')}")
                print(f"  最新消息: {newest.strftime('%Y-%m-%d %H:%M:%S')}")
                
                now = datetime.now()
                print(f"\n  当前时间: {now.strftime('%Y-%m-%d %H:%M:%S')}")
                
                print(f"\n  时间戳对比:")
                print(f"    最早消息时间戳: {min(times)}")
                print(f"    最新消息时间戳: {max(times)}")
                print(f"    7天前时间戳: {int((now - timedelta(days=7)).timestamp() * 1000)}")
                print(f"    当前时间戳: {int(now.timestamp() * 1000)}")
                
                print(f"\n  前10条消息详情:")
                for i, msg in enumerate(items[:10], 1):
                    create_time = msg.get("create_time")
                    msg_type = msg.get("msg_type")
                    if create_time:
                        dt = datetime.fromtimestamp(int(create_time)/1000)
                        print(f"    {i}. [{msg_type}] {dt.strftime('%Y-%m-%d %H:%M:%S')} (ts: {create_time})")

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
调试脚本 - 检查消息获取问题
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

def get_messages_debug(token, group_id, start_time, end_time):
    url = "https://open.feishu.cn/open-apis/im/v1/messages"
    headers = {"Authorization": f"Bearer {token}"}
    params = {
        "container_id": group_id,
        "container_id_type": "chat",
        "start_time": str(start_time),
        "end_time": str(end_time),
        "page_size": 50
    }
    
    print(f"\n🔍 API请求参数:")
    print(f"  URL: {url}")
    print(f"  container_id: {group_id}")
    print(f"  start_time: {start_time} ({datetime.fromtimestamp(start_time/1000)})")
    print(f"  end_time: {end_time} ({datetime.fromtimestamp(end_time/1000)})")
    
    messages = []
    page_token = None
    try:
        while True:
            if page_token:
                params["page_token"] = page_token
            resp = requests.get(url, headers=headers, params=params, timeout=10, proxies=NO_PROXY).json()
            
            print(f"\n📡 API响应:")
            print(f"  code: {resp.get('code')}")
            print(f"  msg: {resp.get('msg')}")
            
            if resp.get("code") == 0:
                items = resp.get("data", {}).get("items", [])
                print(f"  items count: {len(items)}")
                messages.extend(items)
                page_token = resp.get("data", {}).get("page_token")
                if not page_token or len(messages) >= 500:
                    break
            else:
                print(f"  错误详情: {json.dumps(resp, ensure_ascii=False, indent=2)}")
                break
    except Exception as e:
        print(f"请求异常: {e}")
    
    return messages

def main():
    print("🔍 消息获取调试工具")
    print("=" * 60)
    
    token = get_access_token()
    if not token:
        print("❌ 获取token失败")
        return
    
    print("✅ 获取token成功")
    
    group_id = "oc_25f38870e584f38e574f8cb3d2b4e032"
    group_name = "策划二部"
    
    print(f"\n🎯 目标群: {group_name}")
    print(f"   群ID: {group_id}")
    
    now = datetime.now()
    print(f"\n⏰ 当前时间: {now.strftime('%Y-%m-%d %H:%M:%S')}")
    
    print("\n" + "=" * 60)
    print("📅 测试1: 过去7天消息")
    print("=" * 60)
    
    start_time = int((now - timedelta(days=7)).timestamp() * 1000)
    end_time = int(now.timestamp() * 1000)
    
    messages = get_messages_debug(token, group_id, start_time, end_time)
    print(f"\n📊 结果: 获取到 {len(messages)} 条消息")
    
    if messages:
        print("\n📝 前3条消息预览:")
        for i, msg in enumerate(messages[:3], 1):
            msg_type = msg.get("msg_type")
            create_time = msg.get("create_time")
            if create_time:
                dt = datetime.fromtimestamp(int(create_time)/1000)
                print(f"  {i}. [{msg_type}] {dt.strftime('%Y-%m-%d %H:%M')}")
    
    print("\n" + "=" * 60)
    print("📅 测试2: 过去30天消息")
    print("=" * 60)
    
    start_time = int((now - timedelta(days=30)).timestamp() * 1000)
    end_time = int(now.timestamp() * 1000)
    
    messages = get_messages_debug(token, group_id, start_time, end_time)
    print(f"\n📊 结果: 获取到 {len(messages)} 条消息")
    
    print("\n" + "=" * 60)
    print("📅 测试3: 昨天00:00-23:59")
    print("=" * 60)
    
    yesterday = now - timedelta(days=1)
    start_of_yesterday = datetime(yesterday.year, yesterday.month, yesterday.day, 0, 0, 0)
    end_of_yesterday = datetime(yesterday.year, yesterday.month, yesterday.day, 23, 59, 59)
    
    start_time = int(start_of_yesterday.timestamp() * 1000)
    end_time = int(end_of_yesterday.timestamp() * 1000)
    
    print(f"  开始: {start_of_yesterday}")
    print(f"  结束: {end_of_yesterday}")
    
    messages = get_messages_debug(token, group_id, start_time, end_time)
    print(f"\n📊 结果: 获取到 {len(messages)} 条消息")
    
    print("\n" + "=" * 60)
    print("📅 测试4: 英璨市场部大群（对比测试）")
    print("=" * 60)
    
    group_id_2 = "oc_48e2db5c69667ddfe1a50331939f98e1"
    start_time = int((now - timedelta(days=7)).timestamp() * 1000)
    end_time = int(now.timestamp() * 1000)
    
    messages = get_messages_debug(token, group_id_2, start_time, end_time)
    print(f"\n📊 结果: 获取到 {len(messages)} 条消息")
    
    if messages:
        print("\n📝 前3条消息预览:")
        for i, msg in enumerate(messages[:3], 1):
            msg_type = msg.get("msg_type")
            create_time = msg.get("create_time")
            if create_time:
                dt = datetime.fromtimestamp(int(create_time)/1000)
                print(f"  {i}. [{msg_type}] {dt.strftime('%Y-%m-%d %H:%M')}")

if __name__ == "__main__":
    main()

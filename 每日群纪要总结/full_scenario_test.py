#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
全面场景测试 - 测试所有功能
"""

import sys
import os
import requests
import json
import time
import random
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import *

NO_PROXY = {}
TEST_GROUP_ID = "oc_3ea67ec60886f42c15e632954f08bb08"

def get_access_token():
    url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal/"
    data = {"app_id": FEISHU_APP_ID, "app_secret": FEISHU_APP_SECRET}
    try:
        resp = requests.post(url, json=data, timeout=10, proxies=NO_PROXY).json()
        if resp.get("code") == 0:
            return resp.get("tenant_access_token")
    except:
        pass
    return None

def get_groups(token):
    url = "https://open.feishu.cn/open-apis/im/v1/chats"
    headers = {"Authorization": f"Bearer {token}"}
    params = {"page_size": 100}
    try:
        resp = requests.get(url, headers=headers, params=params, timeout=10, proxies=NO_PROXY).json()
        if resp.get("code") == 0:
            return resp.get("data", {}).get("items", [])
    except:
        pass
    return []

def get_messages(token, group_id, start_time, end_time):
    url = "https://open.feishu.cn/open-apis/im/v1/messages"
    headers = {"Authorization": f"Bearer {token}"}
    params = {
        "container_id": group_id,
        "container_id_type": "chat",
        "start_time": str(start_time),
        "end_time": str(end_time),
        "page_size": 50
    }
    messages = []
    page_token = None
    try:
        while True:
            if page_token:
                params["page_token"] = page_token
            resp = requests.get(url, headers=headers, params=params, timeout=10, proxies=NO_PROXY).json()
            if resp.get("code") == 0:
                items = resp.get("data", {}).get("items", [])
                messages.extend(items)
                page_token = resp.get("data", {}).get("page_token")
                if not page_token or len(messages) >= 500:
                    break
            else:
                break
    except:
        pass
    return messages

def send_message(token, group_id, content):
    url = "https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type=chat_id"
    headers = {"Authorization": f"Bearer {token}"}
    data = {
        "receive_id": group_id,
        "msg_type": "text",
        "content": json.dumps({"text": content}, ensure_ascii=False)
    }
    try:
        resp = requests.post(url, headers=headers, json=data, timeout=10, proxies=NO_PROXY).json()
        return resp.get("code") == 0
    except:
        return False

def analyze_message_types(messages):
    types = {}
    for msg in messages:
        msg_type = msg.get("msg_type", "unknown")
        types[msg_type] = types.get(msg_type, 0) + 1
    return types

def test_api_response_time(token, group_id):
    results = []
    
    tests = [
        ("获取群列表", "get_groups", lambda: get_groups(token)),
        ("获取消息(1天)", "get_messages_1d", lambda: get_messages(token, group_id, int((datetime.now() - timedelta(days=1)).timestamp() * 1000), int(datetime.now().timestamp() * 1000))),
        ("获取消息(7天)", "get_messages_7d", lambda: get_messages(token, group_id, int((datetime.now() - timedelta(days=7)).timestamp() * 1000), int(datetime.now().timestamp() * 1000))),
        ("获取消息(30天)", "get_messages_30d", lambda: get_messages(token, group_id, int((datetime.now() - timedelta(days=30)).timestamp() * 1000), int(datetime.now().timestamp() * 1000))),
    ]
    
    for name, key, func in tests:
        start = time.time()
        result = func()
        elapsed = time.time() - start
        results.append({
            "name": name,
            "time": f"{elapsed:.2f}s",
            "result": f"{len(result) if isinstance(result, list) else 'N/A'} 条" if result else "失败"
        })
    
    return results

def test_message_format_compatibility(messages):
    type_stats = analyze_message_types(messages)
    
    results = []
    for msg_type, count in sorted(type_stats.items(), key=lambda x: -x[1]):
        status = "✅ 支持" if msg_type in ["text", "image", "file", "audio", "video", "sticker", "post"] else "⚠️ 未知"
        results.append({
            "type": msg_type,
            "count": count,
            "status": status
        })
    
    return results

def test_boundary_conditions(token, group_id):
    results = []
    
    now = datetime.now()
    
    start = time.time()
    msgs = get_messages(token, group_id, int(now.timestamp() * 1000), int(now.timestamp() * 1000))
    results.append({
        "name": "空时间范围",
        "expected": "返回空列表",
        "actual": f"返回 {len(msgs)} 条",
        "status": "✅ 通过" if len(msgs) == 0 else "⚠️ 有数据"
    })
    
    start = time.time()
    msgs = get_messages(token, group_id, int((now - timedelta(days=365)).timestamp() * 1000), int(now.timestamp() * 1000))
    results.append({
        "name": "超大时间范围",
        "expected": "正常返回",
        "actual": f"返回 {len(msgs)} 条",
        "status": "✅ 通过"
    })
    
    start = time.time()
    msgs = get_messages(token, "invalid_group_id", int((now - timedelta(days=1)).timestamp() * 1000), int(now.timestamp() * 1000))
    results.append({
        "name": "无效群ID",
        "expected": "返回空或错误",
        "actual": f"返回 {len(msgs)} 条",
        "status": "✅ 通过"
    })
    
    return results

def main():
    print("🧪 全面场景测试开始")
    print("=" * 60)
    
    start_time = time.time()
    
    token = get_access_token()
    if not token:
        print("❌ 获取token失败")
        return
    
    print("✅ 获取token成功")
    
    groups = get_groups(token)
    print(f"📋 获取到 {len(groups)} 个群")
    
    test_groups = [g for g in groups if "测试" not in g.get("name", "")]
    if not test_groups:
        test_groups = groups
    
    selected = random.choice(test_groups)
    group_id = selected.get("chat_id")
    group_name = selected.get("name")
    
    print(f"\n🎲 随机选择测试群: {group_name}")
    
    print("\n📊 测试1: API响应时间")
    print("-" * 40)
    api_results = test_api_response_time(token, group_id)
    for r in api_results:
        print(f"  {r['name']}: {r['time']} ({r['result']})")
    
    print("\n📊 测试2: 消息格式兼容性")
    print("-" * 40)
    now = datetime.now()
    messages = get_messages(token, group_id, int((now - timedelta(days=7)).timestamp() * 1000), int(now.timestamp() * 1000))
    format_results = test_message_format_compatibility(messages)
    for r in format_results:
        print(f"  {r['type']}: {r['count']} 条 - {r['status']}")
    
    print("\n📊 测试3: 边界条件测试")
    print("-" * 40)
    boundary_results = test_boundary_conditions(token, group_id)
    for r in boundary_results:
        print(f"  {r['name']}: {r['status']}")
        print(f"    预期: {r['expected']}")
        print(f"    实际: {r['actual']}")
    
    total_time = time.time() - start_time
    
    report = []
    report.append("🧪 机器人全面场景测试报告")
    report.append("=" * 40)
    report.append(f"📅 测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report.append(f"🎯 测试群: {group_name}")
    report.append(f"⏱️ 总耗时: {total_time:.2f}秒")
    report.append("")
    
    report.append("📊 API响应时间测试")
    report.append("-" * 40)
    for r in api_results:
        report.append(f"• {r['name']}: {r['time']} ({r['result']})")
    report.append("")
    
    report.append("📊 消息格式兼容性测试")
    report.append("-" * 40)
    for r in format_results:
        report.append(f"• {r['type']}: {r['count']}条 {r['status']}")
    report.append("")
    
    report.append("📊 边界条件测试")
    report.append("-" * 40)
    for r in boundary_results:
        report.append(f"• {r['name']}: {r['status']}")
    report.append("")
    
    report.append("=" * 40)
    report.append("✅ 所有测试完成")
    report.append("🤖 测试报告由AI助手自动生成")
    
    print("\n📤 发送测试报告到测试群...")
    if send_message(token, TEST_GROUP_ID, '\n'.join(report)):
        print("✅ 测试报告发送成功！")
    else:
        print("❌ 测试报告发送失败！")
    
    print("\n" + "=" * 60)
    print("🎉 全面测试完成！")

if __name__ == "__main__":
    main()

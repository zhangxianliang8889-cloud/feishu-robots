#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import requests
import json
from datetime import datetime, timedelta

APP_ID = "cli_a9233dfe18389bde"
APP_SECRET = "8gvZm8C04sS0GJXtDQdkkeAOJV6gCr4w"
NO_PROXY = {}

def get_token():
    url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal/"
    resp = requests.post(url, json={"app_id": APP_ID, "app_secret": APP_SECRET}, timeout=10, proxies=NO_PROXY).json()
    return resp.get("tenant_access_token") if resp.get("code") == 0 else None

def get_all_messages(token, group_id):
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
        
        resp = requests.get(url, params=params, headers=headers, proxies=NO_PROXY).json()
        if resp.get("code") != 0:
            print(f"API Error: {resp}")
            break
        
        data = resp.get("data", {})
        messages = data.get("items", [])
        all_messages.extend(messages)
        
        if not data.get("has_more", False):
            break
        page_token = data.get("page_token")
    
    return all_messages

def get_group_members(token, group_id):
    url = f"https://open.feishu.cn/open-apis/im/v1/chats/{group_id}/members"
    headers = {"Authorization": f"Bearer {token}"}
    members = []
    page_token = None
    
    while True:
        params = {"member_id_type": "open_id", "page_size": 100}
        if page_token:
            params["page_token"] = page_token
        
        resp = requests.get(url, params=params, headers=headers, proxies=NO_PROXY).json()
        if resp.get("code") != 0:
            print(f"Members API Error: {resp}")
            break
        
        data = resp.get("data", {})
        items = data.get("items", [])
        members.extend(items)
        
        if not data.get("has_more", False):
            break
        page_token = data.get("page_token")
    
    return members

def filter_by_day(messages, days_ago=1):
    now = datetime.now()
    target_date = now - timedelta(days=days_ago)
    start_of_day = target_date.replace(hour=0, minute=0, second=0, microsecond=0)
    end_of_day = start_of_day + timedelta(days=1)
    start_ts = int(start_of_day.timestamp() * 1000)
    end_ts = int(end_of_day.timestamp() * 1000)
    
    print(f"Day filter: {start_of_day} ~ {end_of_day}")
    print(f"Timestamps: {start_ts} ~ {end_ts}")
    
    filtered = []
    for msg in messages:
        create_time = int(msg.get("create_time", 0))
        if start_ts <= create_time < end_ts:
            filtered.append(msg)
    
    return filtered

def count_messages_debug(messages, members):
    print(f"\nMembers count: {len(members)}")
    print("Member IDs:")
    for m in members[:5]:
        print(f"  {m.get('member_id')} -> {m.get('name')}")
    
    member_map = {m.get("member_id"): m.get("name") for m in members}
    count = {}
    
    print(f"\nProcessing {len(messages)} messages...")
    for i, msg in enumerate(messages[:5]):
        sender_info = msg.get("sender", {})
        sender_id = sender_info.get("id", "")
        sender_type = sender_info.get("sender_type", "")
        
        print(f"\nMessage {i+1}:")
        print(f"  Sender ID: {sender_id}")
        print(f"  Sender Type: {sender_type}")
        
        if not sender_id:
            print("  -> Skipped: No sender_id")
            continue
        if sender_type == "app":
            print("  -> Skipped: App sender")
            continue
        if sender_id.startswith("cli_"):
            print("  -> Skipped: cli_ prefix")
            continue
        
        sender_name = member_map.get(sender_id)
        print(f"  Sender Name: {sender_name}")
        
        if not sender_name:
            print("  -> Warning: Name not found in member_map")
        else:
            count[sender_name] = count.get(sender_name, 0) + 1
    
    return count

def main():
    print("=" * 60)
    print("Full Debug")
    print("=" * 60)
    
    source_group = "oc_48e2db5c69667ddfe1a50331939f98e1"
    
    token = get_token()
    if not token:
        print("❌ Token failed")
        return
    print("✅ Token OK")
    
    print("\nGetting messages...")
    messages = get_all_messages(token, source_group)
    print(f"✅ Got {len(messages)} messages")
    
    print("\nGetting members...")
    members = get_group_members(token, source_group)
    print(f"✅ Got {len(members)} members")
    
    print("\n" + "=" * 60)
    print("Filtering daily messages...")
    daily_msgs = filter_by_day(messages, days_ago=1)
    print(f"Daily messages: {len(daily_msgs)}")
    
    print("\n" + "=" * 60)
    print("Counting messages...")
    count = count_messages_debug(daily_msgs, members)
    print(f"\nFinal count: {count}")

if __name__ == "__main__":
    main()

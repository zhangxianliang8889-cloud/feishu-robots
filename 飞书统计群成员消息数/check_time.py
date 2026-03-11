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

def get_messages(token, group_id):
    url = "https://open.feishu.cn/open-apis/im/v1/messages"
    headers = {"Authorization": f"Bearer {token}"}
    params = {"container_id_type": "chat", "container_id": group_id, "page_size": "50"}
    resp = requests.get(url, params=params, headers=headers, proxies=NO_PROXY).json()
    if resp.get("code") == 0:
        return resp.get("data", {}).get("items", [])
    return []

def main():
    print("Checking message times...")
    token = get_token()
    if not token:
        print("Token failed")
        return
    
    messages = get_messages(token, "oc_48e2db5c69667ddfe1a50331939f98e1")
    print(f"Total messages: {len(messages)}")
    
    now = datetime.now()
    print(f"\nCurrent time: {now}")
    
    # Check yesterday
    yesterday = now - timedelta(days=1)
    start_of_yesterday = yesterday.replace(hour=0, minute=0, second=0, microsecond=0)
    end_of_yesterday = start_of_yesterday + timedelta(days=1)
    start_ts = int(start_of_yesterday.timestamp() * 1000)
    end_ts = int(end_of_yesterday.timestamp() * 1000)
    
    print(f"\nYesterday ({yesterday.strftime('%Y-%m-%d')}):")
    print(f"  Start: {start_of_yesterday} (ts: {start_ts})")
    print(f"  End: {end_of_yesterday} (ts: {end_ts})")
    
    yesterday_count = 0
    for msg in messages:
        create_time = int(msg.get("create_time", 0))
        if start_ts <= create_time < end_ts:
            yesterday_count += 1
    
    print(f"  Messages in range: {yesterday_count}")
    
    # Check past 7 days
    week_start = now - timedelta(days=7)
    week_start_ts = int(week_start.timestamp() * 1000)
    week_end_ts = int(now.timestamp() * 1000)
    
    print(f"\nPast 7 days ({week_start.strftime('%Y-%m-%d')} to {now.strftime('%Y-%m-%d')}):")
    print(f"  Start ts: {week_start_ts}")
    print(f"  End ts: {week_end_ts}")
    
    week_count = 0
    for msg in messages:
        create_time = int(msg.get("create_time", 0))
        if week_start_ts <= create_time <= week_end_ts:
            week_count += 1
    
    print(f"  Messages in range: {week_count}")
    
    # Show first 5 message times
    print(f"\nFirst 5 message times:")
    for i, msg in enumerate(messages[:5], 1):
        create_time = int(msg.get("create_time", 0))
        dt = datetime.fromtimestamp(create_time / 1000)
        print(f"  {i}. {dt.strftime('%Y-%m-%d %H:%M:%S')} (ts: {create_time})")

if __name__ == "__main__":
    main()

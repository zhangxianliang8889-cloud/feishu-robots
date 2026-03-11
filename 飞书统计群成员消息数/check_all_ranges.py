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

def filter_by_day(messages, days_ago=1):
    now = datetime.now()
    target_date = now - timedelta(days=days_ago)
    start_of_day = target_date.replace(hour=0, minute=0, second=0, microsecond=0)
    end_of_day = start_of_day + timedelta(days=1)
    start_ts = int(start_of_day.timestamp() * 1000)
    end_ts = int(end_of_day.timestamp() * 1000)
    
    filtered = [m for m in messages if start_ts <= int(m.get("create_time", 0)) < end_ts]
    return filtered, start_of_day.strftime("%Y-%m-%d")

def filter_by_week(messages, weeks_ago=1):
    now = datetime.now()
    monday = now - timedelta(days=now.weekday())
    start_of_week = monday - timedelta(weeks=weeks_ago)
    end_of_week = start_of_week + timedelta(weeks=1)
    start_ts = int(start_of_week.timestamp() * 1000)
    end_ts = int(end_of_week.timestamp() * 1000)
    
    filtered = [m for m in messages if start_ts <= int(m.get("create_time", 0)) < end_ts]
    return filtered, start_of_week.strftime("%Y-%m-%d"), end_of_week.strftime("%Y-%m-%d")

def filter_by_month(messages, months_ago=1):
    now = datetime.now()
    first_day = now.replace(day=1)
    if months_ago > 0:
        for _ in range(months_ago):
            first_day = first_day.replace(day=1) - timedelta(days=1)
            first_day = first_day.replace(day=1)
    start_of_month = first_day
    end_of_month = (start_of_month.replace(day=28) + timedelta(days=4)).replace(day=1)
    start_ts = int(start_of_month.timestamp() * 1000)
    end_ts = int(end_of_month.timestamp() * 1000)
    
    filtered = [m for m in messages if start_ts <= int(m.get("create_time", 0)) < end_ts]
    return filtered, start_of_month.strftime("%Y-%m-%d"), end_of_month.strftime("%Y-%m-%d")

def main():
    print("=" * 60)
    print("Checking all time ranges...")
    print("=" * 60)
    
    token = get_token()
    if not token:
        print("Token failed")
        return
    
    messages = get_messages(token, "oc_48e2db5c69667ddfe1a50331939f98e1")
    print(f"\nTotal messages available: {len(messages)}")
    
    now = datetime.now()
    print(f"Current time: {now.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Current weekday: {now.strftime('%A')}")
    
    # Daily
    print("\n" + "=" * 60)
    print("DAILY REPORT (Yesterday)")
    print("=" * 60)
    daily_msgs, daily_date = filter_by_day(messages, days_ago=1)
    print(f"Date: {daily_date}")
    print(f"Messages: {len(daily_msgs)}")
    
    # Weekly
    print("\n" + "=" * 60)
    print("WEEKLY REPORT (Last Week)")
    print("=" * 60)
    weekly_msgs, week_start, week_end = filter_by_week(messages, weeks_ago=1)
    print(f"Range: {week_start} ~ {week_end}")
    print(f"Messages: {len(weekly_msgs)}")
    
    # Monthly
    print("\n" + "=" * 60)
    print("MONTHLY REPORT (Last Month)")
    print("=" * 60)
    monthly_msgs, month_start, month_end = filter_by_month(messages, months_ago=1)
    print(f"Range: {month_start} ~ {month_end}")
    print(f"Messages: {len(monthly_msgs)}")
    
    # Check all message dates
    print("\n" + "=" * 60)
    print("ALL MESSAGE DATES")
    print("=" * 60)
    dates = {}
    for msg in messages:
        ts = int(msg.get("create_time", 0))
        dt = datetime.fromtimestamp(ts / 1000)
        date_str = dt.strftime("%Y-%m-%d")
        dates[date_str] = dates.get(date_str, 0) + 1
    
    for date in sorted(dates.keys()):
        print(f"  {date}: {dates[date]} messages")

if __name__ == "__main__":
    main()

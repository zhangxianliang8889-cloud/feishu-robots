#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""发送计划查询工具 - 查看接下来的发送计划"""

import sys
import os
from datetime import datetime, timedelta
import calendar

def is_first_day_of_month():
    now = datetime.now()
    return now.day == 1

def is_month_end():
    now = datetime.now()
    next_day = (now + timedelta(days=1))
    return next_day.day == 1

def get_next_sends(limit=10):
    now = datetime.now()
    sends = []
    
    current = now
    
    while len(sends) < limit:
        current += timedelta(minutes=1)
        
        hour = current.hour
        minute = current.minute
        weekday = current.weekday()
        day = current.day
        
        if hour == 9 and minute == 0:
            sends.append({
                "time": current.strftime('%Y-%m-%d %H:%M:%S'),
                "type": "群消息统计 - 日报",
                "desc": "发送昨日日报"
            })
        
        if hour == 12 and minute == 0 and weekday == 0:
            sends.append({
                "time": current.strftime('%Y-%m-%d %H:%M:%S'),
                "type": "群消息统计 - 周报",
                "desc": "发送上周周报"
            })
        
        if hour == 15 and minute == 0 and day == 1:
            sends.append({
                "time": current.strftime('%Y-%m-%d %H:%M:%S'),
                "type": "群消息统计 - 月报",
                "desc": "发送上月月报"
            })
        
        if hour == 21 and minute == 0:
            sends.append({
                "time": current.strftime('%Y-%m-%d %H:%M:%S'),
                "type": "群会议纪要 - 日报",
                "desc": "发送当日日报"
            })
        
        if hour == 9 and minute == 0 and weekday == 0:
            sends.append({
                "time": current.strftime('%Y-%m-%d %H:%M:%S'),
                "type": "群会议纪要 - 周报",
                "desc": "发送上周周报"
            })
        
        if hour == 9 and minute == 30 and is_month_end():
            sends.append({
                "time": current.strftime('%Y-%m-%d %H:%M:%S'),
                "type": "群会议纪要 - 月报",
                "desc": "发送上月月报"
            })
    
    return sends[:limit]

def main():
    print("\n" + "=" * 80)
    print("🤖 发送计划查询工具")
    print("=" * 80)
    print("⏰ 当前时间: " + datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    print("📋 接下来 10 次发送计划：\n")
    
    sends = get_next_sends(10)
    
    for idx, send in enumerate(sends, 1):
        print(f"  {idx:2d}. [{send['time']}] {send['type']}")
        print(f"      {send['desc']}")
    
    print("\n" + "=" * 80 + "\n")

if __name__ == "__main__":
    main()

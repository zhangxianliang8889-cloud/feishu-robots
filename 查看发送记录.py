#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""发送记录查询工具 - 快速查看最近发送记录"""

import json
import os
from datetime import datetime
from collections import OrderedDict

STATS_BOT_RECORDS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "飞书统计群成员消息数", "send_records.json")
SUMMARY_BOT_RECORDS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "每日群纪要总结", "send_records.json")

def load_records(file_path):
    if os.path.exists(file_path):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"❌ 读取文件失败: {e}")
            return {}
    return {}

def get_recent_records(records, limit=10):
    sorted_records = sorted(
        records.items(),
        key=lambda x: x[1].get('sent_time', ''),
        reverse=True
    )
    return sorted_records[:limit]

def display_records(title, records, limit=10):
    print("=" * 80)
    print(f"📊 {title}")
    print("=" * 80)
    
    if not records:
        print("  (暂无记录)")
        return
    
    recent = get_recent_records(records, limit)
    
    print(f"\n📋 最近 {len(recent)} 次发送记录：\n")
    
    for idx, (key, record) in enumerate(recent, 1):
        group_name = record.get('group_name', record.get('chat_name', '未知'))
        report_type = record.get('report_type', record.get('summary_type', '未知'))
        date_key = record.get('date_key', '未知')
        sent_time = record.get('sent_time', '未知')
        
        print(f"  {idx:2d}. [{sent_time}] {group_name} - {report_type} ({date_key})")
    
    print(f"\n{'=' * 80}\n")

def main():
    print("\n" + "=" * 80)
    print("🤖 发送记录查询工具")
    print("=" * 80)
    print(f"⏰ 查询时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    stats_records = load_records(STATS_BOT_RECORDS)
    display_records("群消息统计机器人 - 发送记录", stats_records, 10)
    
    summary_records = load_records(SUMMARY_BOT_RECORDS)
    display_records("群会议纪要机器人 - 发送记录", summary_records, 10)

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
预防机制：定期检查未知用户并更新缓存
"""

import os
import json
import requests
from datetime import datetime
from collections import Counter

NO_PROXY = {}

class UnknownUserDetector:
    """未知用户检测器"""
    
    def __init__(self, cache_dir):
        self.cache_dir = cache_dir
        self.unknown_users_file = os.path.join(cache_dir, "unknown_users_log.json")
        self.unknown_users = self.load_unknown_users()
    
    def load_unknown_users(self):
        """加载未知用户记录"""
        if os.path.exists(self.unknown_users_file):
            try:
                with open(self.unknown_users_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return {}
        return {}
    
    def save_unknown_users(self):
        """保存未知用户记录"""
        try:
            with open(self.unknown_users_file, 'w', encoding='utf-8') as f:
                json.dump(self.unknown_users, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"⚠️ 保存未知用户记录失败: {e}")
    
    def record_unknown_user(self, user_id, group_name, message_count):
        """记录未知用户"""
        if user_id not in self.unknown_users:
            self.unknown_users[user_id] = {
                "first_seen": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                "groups": {},
                "total_messages": 0
            }
        
        self.unknown_users[user_id]["last_seen"] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        self.unknown_users[user_id]["total_messages"] += message_count
        
        if group_name not in self.unknown_users[user_id]["groups"]:
            self.unknown_users[user_id]["groups"][group_name] = 0
        self.unknown_users[user_id]["groups"][group_name] += message_count
        
        self.save_unknown_users()
    
    def get_unknown_users_report(self):
        """获取未知用户报告"""
        return self.unknown_users

def check_and_report_unknown_users(token, cache, detector, group_id, group_name, messages, members):
    """检查并报告未知用户"""
    member_map = {m.get("member_id"): m.get("name") for m in members}
    cache.update_from_members(members, group_name)
    
    unknown_count = Counter()
    
    for msg in messages:
        sender_info = msg.get("sender", {})
        sender_id = sender_info.get("id", "")
        sender_type = sender_info.get("sender_type", "")
        
        if not sender_id or sender_type == "app" or sender_id.startswith("cli_"):
            continue
        
        sender_name = member_map.get(sender_id)
        if not sender_name:
            sender_name = cache.get_name(sender_id)
        
        if not sender_name:
            unknown_count[sender_id] += 1
    
    for user_id, count in unknown_count.items():
        detector.record_unknown_user(user_id, group_name, count)
    
    return unknown_count

if __name__ == "__main__":
    print("=" * 80)
    print("🔍 预防机制：未知用户检测器")
    print("=" * 80)
    print("\n功能说明：")
    print("1. 自动检测不在成员列表中的用户")
    print("2. 记录未知用户的出现时间和消息数")
    print("3. 支持手动维护已退群用户映射")
    print("\n使用方法：")
    print("1. 查看 unknown_users_log.json 了解未知用户情况")
    print("2. 在 left_users_mapping.json 中填写已知退群用户的姓名")
    print("3. 系统会自动从API获取用户信息并缓存")

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
用户名缓存管理器 - 改进版
支持从多个群收集用户信息
"""

import os
import json
from datetime import datetime

class UserNameCache:
    def __init__(self, cache_file="user_name_cache.json"):
        self.cache_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "飞书统计群成员消息数")
        self.cache_file = os.path.join(self.cache_dir, cache_file)
        self.cache = self.load_cache()
    
    def load_cache(self):
        """加载缓存"""
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return {}
        return {}
    
    def save_cache(self):
        """保存缓存"""
        try:
            os.makedirs(self.cache_dir, exist_ok=True)
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(self.cache, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"⚠️ 保存缓存失败: {e}")
    
    def update_from_members(self, members, group_name=""):
        """从成员列表更新缓存"""
        updated = False
        for member in members:
            member_id = member.get("member_id", "")
            name = member.get("name", "")
            if member_id and name:
                if member_id not in self.cache or self.cache[member_id].get("name") != name:
                    self.cache[member_id] = {
                        "name": name,
                        "last_seen": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                        "status": "active",
                        "source_group": group_name
                    }
                    updated = True
        
        if updated:
            self.save_cache()
        
        return updated
    
    def get_name(self, user_id):
        """获取用户名"""
        if user_id in self.cache:
            return self.cache[user_id].get("name", None)
        return None
    
    def mark_as_left(self, user_id):
        """标记用户已退群"""
        if user_id in self.cache:
            self.cache[user_id]["status"] = "left"
            self.cache[user_id]["left_time"] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            self.save_cache()
    
    def get_all_users(self):
        """获取所有用户"""
        return self.cache

if __name__ == "__main__":
    # 测试缓存管理器
    cache = UserNameCache()
    print(f"当前缓存: {json.dumps(cache.cache, indent=2, ensure_ascii=False)}")

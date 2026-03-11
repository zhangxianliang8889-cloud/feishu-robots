#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
用户名缓存管理器 - 完整版
支持：群成员列表 + 缓存 + API查询 + 手动维护
"""

import os
import json
import requests
from datetime import datetime

NO_PROXY = {}

class UserNameCache:
    def __init__(self, cache_file="user_name_cache.json", left_users_file="left_users_mapping.json"):
        self.cache_dir = os.path.dirname(os.path.abspath(__file__))
        self.cache_file = os.path.join(self.cache_dir, cache_file)
        self.left_users_file = os.path.join(self.cache_dir, left_users_file)
        
        self.cache = self.load_cache()
        self.left_users = self.load_left_users()
        self.api_cache = {}  # API查询缓存，避免重复查询
        self.token = None
    
    def set_token(self, token):
        """设置API访问token"""
        self.token = token
    
    def load_cache(self):
        """加载缓存"""
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return {}
        return {}
    
    def load_left_users(self):
        """加载手动维护的已退群用户映射"""
        if os.path.exists(self.left_users_file):
            try:
                with open(self.left_users_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return {}
        return {}
    
    def save_cache(self):
        """保存缓存"""
        try:
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
    
    def get_user_from_api(self, user_id):
        """从API获取用户信息"""
        if not self.token:
            return None
        
        if user_id in self.api_cache:
            return self.api_cache[user_id]
        
        try:
            url = f"https://open.feishu.cn/open-apis/contact/v3/users/{user_id}"
            headers = {"Authorization": f"Bearer {self.token}"}
            params = {"user_id_type": "open_id"}
            resp = requests.get(url, headers=headers, params=params, proxies=NO_PROXY, timeout=5).json()
            
            if resp.get("code") == 0:
                user_data = resp.get("data", {}).get("user", {})
                name = user_data.get("name", "")
                
                if name:
                    self.api_cache[user_id] = name
                    return name
                else:
                    self.api_cache[user_id] = None
                    return None
            else:
                self.api_cache[user_id] = None
                return None
        except Exception as e:
            return None
    
    def get_name(self, user_id):
        """
        获取用户名（多层获取机制）
        1. 从当前群成员列表（由调用方传入）
        2. 从缓存获取
        3. 从API获取
        4. 从手动维护的映射获取
        """
        if user_id in self.cache:
            return self.cache[user_id].get("name", None)
        
        if user_id in self.api_cache:
            return self.api_cache[user_id]
        
        api_name = self.get_user_from_api(user_id)
        if api_name:
            self.cache[user_id] = {
                "name": api_name,
                "last_seen": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                "status": "api_fetched",
                "source": "api"
            }
            self.save_cache()
            return api_name
        
        if user_id in self.left_users:
            name = self.left_users[user_id].get("name", None)
            if name and name != "请手动填写":
                return name
        
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
    cache = UserNameCache()
    print(f"当前缓存: {json.dumps(cache.cache, indent=2, ensure_ascii=False)}")

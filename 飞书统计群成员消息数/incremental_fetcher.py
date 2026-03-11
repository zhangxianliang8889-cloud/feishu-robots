#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
增量消息获取器 - 行业最优方案
使用消息ID游标实现增量拉取，避免全量扫描
"""

import os
import json
import time
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

class IncrementalMessageFetcher:
    """增量消息获取器"""
    
    def __init__(self, cursor_file: str = None):
        """
        初始化增量消息获取器
        
        Args:
            cursor_file: 游标存储文件路径
        """
        if cursor_file is None:
            cursor_file = os.path.join(
                os.path.dirname(os.path.abspath(__file__)), 
                "message_cursors.json"
            )
        self.cursor_file = cursor_file
        self.cursors = self._load_cursors()
    
    def _load_cursors(self) -> Dict:
        """加载游标数据"""
        if os.path.exists(self.cursor_file):
            try:
                with open(self.cursor_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return {}
        return {}
    
    def _save_cursors(self):
        """保存游标数据"""
        try:
            with open(self.cursor_file, 'w', encoding='utf-8') as f:
                json.dump(self.cursors, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"❌ 保存游标失败: {e}")
    
    def _get_cursor_key(self, group_id: str) -> str:
        """获取游标键"""
        return f"cursor_{group_id}"
    
    def get_last_message_id(self, group_id: str) -> Optional[str]:
        """
        获取上次拉取的最后消息ID
        
        Args:
            group_id: 群ID
        
        Returns:
            Optional[str]: 消息ID，不存在返回None
        """
        key = self._get_cursor_key(group_id)
        cursor_data = self.cursors.get(key, {})
        return cursor_data.get("last_message_id")
    
    def update_cursor(self, group_id: str, last_message_id: str, last_time: str = None):
        """
        更新游标
        
        Args:
            group_id: 群ID
            last_message_id: 最后消息ID
            last_time: 最后时间
        """
        key = self._get_cursor_key(group_id)
        self.cursors[key] = {
            "last_message_id": last_message_id,
            "last_time": last_time or datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            "update_time": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        self._save_cursors()
    
    def fetch_messages_incremental(
        self, 
        token: str, 
        group_id: str, 
        page_size: int = 50,
        max_messages: int = 1000
    ) -> Tuple[List[Dict], bool]:
        """
        增量拉取消息（只拉取新消息）
        
        Args:
            token: 飞书Token
            group_id: 群ID
            page_size: 每页大小
            max_messages: 最大消息数
        
        Returns:
            Tuple[List[Dict], bool]: (消息列表, 是否有更多)
        """
        url = f"https://open.feishu.cn/open-apis/im/v1/messages"
        headers = {"Authorization": f"Bearer {token}"}
        
        all_messages = []
        page_token = None
        last_message_id = self.get_last_message_id(group_id)
        found_last = False
        has_more = False
        
        print(f"📥 增量拉取消息 - 群: {group_id}")
        if last_message_id:
            print(f"   游标: {last_message_id}")
        else:
            print(f"   游标: 无（首次拉取）")
        
        while len(all_messages) < max_messages:
            params = {
                "receive_id_type": "chat_id",
                "page_size": page_size
            }
            
            if page_token:
                params["page_token"] = page_token
            
            try:
                resp = requests.get(url, headers=headers, params=params, proxies={}).json()
                
                if resp.get("code") != 0:
                    print(f"❌ 获取消息失败: {resp.get('msg')}")
                    break
                
                data = resp.get("data", {})
                messages = data.get("items", [])
                
                if not messages:
                    break
                
                for msg in messages:
                    msg_id = msg.get("message_id")
                    
                    if last_message_id and msg_id == last_message_id:
                        found_last = True
                        break
                    
                    all_messages.append(msg)
                
                if found_last:
                    break
                
                has_more = data.get("has_more", False)
                page_token = data.get("page_token")
                
                if not has_more or not page_token:
                    break
                    
            except Exception as e:
                print(f"❌ 拉取消息异常: {e}")
                break
        
        if all_messages:
            newest_msg = all_messages[0]
            newest_id = newest_msg.get("message_id")
            newest_time = datetime.fromtimestamp(
                int(newest_msg.get("create_time", 0)) / 1000
            ).strftime('%Y-%m-%d %H:%M:%S')
            self.update_cursor(group_id, newest_id, newest_time)
            print(f"✅ 拉取 {len(all_messages)} 条新消息，更新游标: {newest_id}")
        else:
            print(f"ℹ️ 无新消息")
        
        return all_messages, has_more
    
    def fetch_messages_by_time_range(
        self,
        token: str,
        group_id: str,
        start_time: datetime,
        end_time: datetime,
        page_size: int = 50
    ) -> List[Dict]:
        """
        按时间范围拉取消息（兼容旧逻辑）
        
        Args:
            token: 飞书Token
            group_id: 群ID
            start_time: 开始时间
            end_time: 结束时间
            page_size: 每页大小
        
        Returns:
            List[Dict]: 消息列表
        """
        url = f"https://open.feishu.cn/open-apis/im/v1/messages"
        headers = {"Authorization": f"Bearer {token}"}
        
        start_ts = int(start_time.timestamp() * 1000)
        end_ts = int(end_time.timestamp() * 1000)
        
        all_messages = []
        page_token = None
        
        while True:
            params = {
                "receive_id_type": "chat_id",
                "page_size": page_size,
                "start_time": start_ts,
                "end_time": end_ts
            }
            
            if page_token:
                params["page_token"] = page_token
            
            try:
                resp = requests.get(url, headers=headers, params=params, proxies={}).json()
                
                if resp.get("code") != 0:
                    break
                
                data = resp.get("data", {})
                messages = data.get("items", [])
                all_messages.extend(messages)
                
                has_more = data.get("has_more", False)
                page_token = data.get("page_token")
                
                if not has_more or not page_token:
                    break
                    
            except Exception as e:
                print(f"❌ 拉取消息异常: {e}")
                break
        
        return all_messages
    
    def get_statistics(self) -> Dict:
        """获取游标统计信息"""
        return {
            "total_groups": len(self.cursors),
            "cursors": [
                {
                    "group_id": k.replace("cursor_", ""),
                    "last_time": v.get("last_time"),
                    "update_time": v.get("update_time")
                }
                for k, v in self.cursors.items()
            ]
        }


class DistributedLock:
    """分布式锁（简化版 - 基于文件锁）"""
    
    def __init__(self, lock_dir: str = None):
        """
        初始化分布式锁
        
        Args:
            lock_dir: 锁文件目录
        """
        if lock_dir is None:
            lock_dir = os.path.join(
                os.path.dirname(os.path.abspath(__file__)),
                "locks"
            )
        self.lock_dir = lock_dir
        os.makedirs(lock_dir, exist_ok=True)
        self.lock_files = {}
    
    def _get_lock_file(self, lock_key: str) -> str:
        """获取锁文件路径"""
        return os.path.join(self.lock_dir, f"{lock_key}.lock")
    
    def acquire(self, lock_key: str, timeout: int = 300) -> bool:
        """
        获取锁
        
        Args:
            lock_key: 锁键
            timeout: 超时时间（秒）
        
        Returns:
            bool: 是否成功获取锁
        """
        lock_file = self._get_lock_file(lock_key)
        
        if os.path.exists(lock_file):
            try:
                with open(lock_file, 'r') as f:
                    data = json.load(f)
                lock_time = datetime.strptime(data.get("time", ""), '%Y-%m-%d %H:%M:%S')
                if (datetime.now() - lock_time).total_seconds() < timeout:
                    return False
            except:
                pass
        
        try:
            with open(lock_file, 'w') as f:
                json.dump({
                    "time": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    "key": lock_key
                }, f)
            self.lock_files[lock_key] = lock_file
            return True
        except:
            return False
    
    def release(self, lock_key: str):
        """
        释放锁
        
        Args:
            lock_key: 锁键
        """
        lock_file = self._get_lock_file(lock_key)
        try:
            if os.path.exists(lock_file):
                os.remove(lock_file)
            if lock_key in self.lock_files:
                del self.lock_files[lock_key]
        except:
            pass
    
    def is_locked(self, lock_key: str, timeout: int = 300) -> bool:
        """
        检查是否被锁定
        
        Args:
            lock_key: 锁键
            timeout: 超时时间
        
        Returns:
            bool: 是否被锁定
        """
        lock_file = self._get_lock_file(lock_key)
        
        if not os.path.exists(lock_file):
            return False
        
        try:
            with open(lock_file, 'r') as f:
                data = json.load(f)
            lock_time = datetime.strptime(data.get("time", ""), '%Y-%m-%d %H:%M:%S')
            return (datetime.now() - lock_time).total_seconds() < timeout
        except:
            return False


class RateLimiter:
    """限流器"""
    
    def __init__(self, max_requests: int = 10, window_seconds: int = 60):
        """
        初始化限流器
        
        Args:
            max_requests: 最大请求数
            window_seconds: 时间窗口（秒）
        """
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests = []
    
    def is_allowed(self) -> bool:
        """
        检查是否允许请求
        
        Returns:
            bool: 是否允许
        """
        now = time.time()
        self.requests = [t for t in self.requests if now - t < self.window_seconds]
        
        if len(self.requests) >= self.max_requests:
            return False
        
        self.requests.append(now)
        return True
    
    def wait_if_needed(self):
        """如果需要，等待到可以请求"""
        while not self.is_allowed():
            time.sleep(1)


if __name__ == "__main__":
    print("🧪 测试增量消息获取器")
    print("=" * 60)
    
    fetcher = IncrementalMessageFetcher("/tmp/test_cursors.json")
    
    print("\n1. 游标管理测试")
    print(f"   获取游标（首次）: {fetcher.get_last_message_id('test_group')}")
    fetcher.update_cursor('test_group', 'msg_001', '2026-03-07 10:00:00')
    print(f"   获取游标（更新后）: {fetcher.get_last_message_id('test_group')}")
    
    print("\n2. 分布式锁测试")
    lock = DistributedLock("/tmp/test_locks")
    print(f"   获取锁: {lock.acquire('test_task')}")
    print(f"   检查锁定: {lock.is_locked('test_task')}")
    print(f"   再次获取锁: {lock.acquire('test_task')}")
    lock.release('test_task')
    print(f"   释放后检查: {lock.is_locked('test_task')}")
    
    print("\n3. 限流器测试")
    limiter = RateLimiter(max_requests=3, window_seconds=5)
    for i in range(5):
        allowed = limiter.is_allowed()
        print(f"   请求 {i+1}: {'✅ 允许' if allowed else '❌ 拒绝'}")
    
    print("\n✅ 测试完成")

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
任务状态管理器 - 行业最优幂等方案
分布式锁 + 状态表 + 任务唯一ID
"""

import os
import json
from datetime import datetime
from typing import Dict, Optional, Any
from enum import Enum

class TaskStatus(Enum):
    """任务状态枚举"""
    PENDING = "等待"
    RUNNING = "执行中"
    COMPLETED = "已完成"
    FAILED = "失败"


class TaskStateManager:
    """任务状态管理器"""
    
    def __init__(self, state_file: str = None):
        """
        初始化任务状态管理器
        
        Args:
            state_file: 状态存储文件路径
        """
        if state_file is None:
            state_file = os.path.join(
                os.path.dirname(os.path.abspath(__file__)),
                "task_states.json"
            )
        self.state_file = state_file
        self.states = self._load_states()
    
    def _load_states(self) -> Dict:
        """加载状态数据"""
        if os.path.exists(self.state_file):
            try:
                with open(self.state_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return {}
        return {}
    
    def _save_states(self):
        """保存状态数据"""
        try:
            with open(self.state_file, 'w', encoding='utf-8') as f:
                json.dump(self.states, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"❌ 保存状态失败: {e}")
    
    def generate_task_id(self, task_type: str, date_key: str, group_id: str) -> str:
        """
        生成任务唯一ID
        
        Args:
            task_type: 任务类型 (daily/weekly/monthly)
            date_key: 日期键
            group_id: 群ID
        
        Returns:
            str: 任务唯一ID
        """
        return f"summary_{task_type}_{date_key}_{group_id}"
    
    def get_task_state(self, task_id: str) -> Optional[Dict]:
        """
        获取任务状态
        
        Args:
            task_id: 任务ID
        
        Returns:
            Optional[Dict]: 任务状态，不存在返回None
        """
        return self.states.get(task_id)
    
    def create_task(
        self, 
        task_id: str, 
        group_id: str, 
        task_type: str, 
        date_key: str,
        metadata: Dict = None
    ) -> bool:
        """
        创建任务
        
        Args:
            task_id: 任务ID
            group_id: 群ID
            task_type: 任务类型
            date_key: 日期键
            metadata: 元数据
        
        Returns:
            bool: 是否创建成功
        """
        if task_id in self.states:
            existing = self.states[task_id]
            if existing.get("status") == TaskStatus.COMPLETED.value:
                return False
        
        self.states[task_id] = {
            "task_id": task_id,
            "group_id": group_id,
            "task_type": task_type,
            "date_key": date_key,
            "status": TaskStatus.PENDING.value,
            "create_time": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            "update_time": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            "retry_count": 0,
            "metadata": metadata or {}
        }
        self._save_states()
        return True
    
    def update_task_status(
        self, 
        task_id: str, 
        status: TaskStatus,
        error_msg: str = None,
        result: Dict = None
    ) -> bool:
        """
        更新任务状态
        
        Args:
            task_id: 任务ID
            status: 新状态
            error_msg: 错误信息
            result: 执行结果
        
        Returns:
            bool: 是否更新成功
        """
        if task_id not in self.states:
            return False
        
        task = self.states[task_id]
        task["status"] = status.value
        task["update_time"] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        if error_msg:
            task["error_msg"] = error_msg
            task["retry_count"] = task.get("retry_count", 0) + 1
        
        if result:
            task["result"] = result
        
        self._save_states()
        return True
    
    def is_task_completed(self, task_id: str) -> bool:
        """
        检查任务是否已完成
        
        Args:
            task_id: 任务ID
        
        Returns:
            bool: 是否已完成
        """
        task = self.get_task_state(task_id)
        if not task:
            return False
        return task.get("status") == TaskStatus.COMPLETED.value
    
    def is_task_running(self, task_id: str) -> bool:
        """
        检查任务是否正在运行
        
        Args:
            task_id: 任务ID
        
        Returns:
            bool: 是否正在运行
        """
        task = self.get_task_state(task_id)
        if not task:
            return False
        return task.get("status") == TaskStatus.RUNNING.value
    
    def get_pending_tasks(self, limit: int = 100) -> list:
        """
        获取待执行任务
        
        Args:
            limit: 最大数量
        
        Returns:
            list: 任务列表
        """
        pending = []
        for task_id, task in self.states.items():
            if task.get("status") == TaskStatus.PENDING.value:
                pending.append(task)
                if len(pending) >= limit:
                    break
        return pending
    
    def get_failed_tasks(self, max_retries: int = 3, limit: int = 100) -> list:
        """
        获取可重试的失败任务
        
        Args:
            max_retries: 最大重试次数
            limit: 最大数量
        
        Returns:
            list: 任务列表
        """
        failed = []
        for task_id, task in self.states.items():
            if task.get("status") == TaskStatus.FAILED.value:
                if task.get("retry_count", 0) < max_retries:
                    failed.append(task)
                    if len(failed) >= limit:
                        break
        return failed
    
    def clean_old_tasks(self, days: int = 35) -> int:
        """
        清理过期任务
        
        Args:
            days: 保留天数
        
        Returns:
            int: 清理数量
        """
        now = datetime.now()
        keys_to_remove = []
        
        for task_id, task in self.states.items():
            try:
                create_time = datetime.strptime(
                    task.get("create_time", ""), 
                    '%Y-%m-%d %H:%M:%S'
                )
                if (now - create_time).days > days:
                    keys_to_remove.append(task_id)
            except:
                keys_to_remove.append(task_id)
        
        for key in keys_to_remove:
            del self.states[key]
        
        if keys_to_remove:
            self._save_states()
        
        return len(keys_to_remove)
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        获取统计信息
        
        Returns:
            Dict: 统计信息
        """
        stats = {
            "total": len(self.states),
            "by_status": {},
            "by_type": {}
        }
        
        for task in self.states.values():
            status = task.get("status", "未知")
            task_type = task.get("task_type", "未知")
            
            stats["by_status"][status] = stats["by_status"].get(status, 0) + 1
            stats["by_type"][task_type] = stats["by_type"].get(task_type, 0) + 1
        
        return stats


class IdempotentTaskExecutor:
    """幂等任务执行器"""
    
    def __init__(self, state_manager: TaskStateManager, lock_manager=None):
        """
        初始化幂等任务执行器
        
        Args:
            state_manager: 状态管理器
            lock_manager: 锁管理器（可选）
        """
        self.state_manager = state_manager
        self.lock_manager = lock_manager
    
    def execute(
        self,
        task_id: str,
        group_id: str,
        task_type: str,
        date_key: str,
        execute_func,
        *args,
        **kwargs
    ) -> Dict[str, Any]:
        """
        执行任务（幂等）
        
        Args:
            task_id: 任务ID
            group_id: 群ID
            task_type: 任务类型
            date_key: 日期键
            execute_func: 执行函数
            *args: 执行函数参数
            **kwargs: 执行函数关键字参数
        
        Returns:
            Dict: 执行结果
        """
        if self.state_manager.is_task_completed(task_id):
            return {
                "success": True,
                "skipped": True,
                "reason": "任务已完成，跳过"
            }
        
        if self.state_manager.is_task_running(task_id):
            return {
                "success": False,
                "skipped": True,
                "reason": "任务正在执行中，跳过"
            }
        
        if self.lock_manager and self.lock_manager.is_locked(task_id):
            return {
                "success": False,
                "skipped": True,
                "reason": "任务被锁定，跳过"
            }
        
        if self.lock_manager:
            if not self.lock_manager.acquire(task_id):
                return {
                    "success": False,
                    "skipped": True,
                    "reason": "获取锁失败，跳过"
                }
        
        try:
            self.state_manager.create_task(task_id, group_id, task_type, date_key)
            self.state_manager.update_task_status(task_id, TaskStatus.RUNNING)
            
            result = execute_func(*args, **kwargs)
            
            if result:
                self.state_manager.update_task_status(
                    task_id, 
                    TaskStatus.COMPLETED,
                    result={"output": str(result)[:500]}
                )
                return {
                    "success": True,
                    "skipped": False,
                    "result": result
                }
            else:
                self.state_manager.update_task_status(
                    task_id,
                    TaskStatus.FAILED,
                    error_msg="执行函数返回False"
                )
                return {
                    "success": False,
                    "skipped": False,
                    "reason": "执行失败"
                }
                
        except Exception as e:
            self.state_manager.update_task_status(
                task_id,
                TaskStatus.FAILED,
                error_msg=str(e)
            )
            return {
                "success": False,
                "skipped": False,
                "error": str(e)
            }
        finally:
            if self.lock_manager:
                self.lock_manager.release(task_id)


if __name__ == "__main__":
    print("🧪 测试任务状态管理器")
    print("=" * 60)
    
    state_manager = TaskStateManager("/tmp/test_task_states.json")
    
    print("\n1. 创建任务")
    task_id = state_manager.generate_task_id("daily", "2026-03-07", "group_001")
    print(f"   任务ID: {task_id}")
    created = state_manager.create_task(task_id, "group_001", "daily", "2026-03-07")
    print(f"   创建结果: {created}")
    
    print("\n2. 检查状态")
    print(f"   是否完成: {state_manager.is_task_completed(task_id)}")
    print(f"   是否运行中: {state_manager.is_task_running(task_id)}")
    
    print("\n3. 更新状态")
    state_manager.update_task_status(task_id, TaskStatus.RUNNING)
    print(f"   更新为运行中")
    print(f"   是否运行中: {state_manager.is_task_running(task_id)}")
    
    print("\n4. 完成任务")
    state_manager.update_task_status(task_id, TaskStatus.COMPLETED)
    print(f"   更新为已完成")
    print(f"   是否完成: {state_manager.is_task_completed(task_id)}")
    
    print("\n5. 再次创建相同任务")
    created_again = state_manager.create_task(task_id, "group_001", "daily", "2026-03-07")
    print(f"   创建结果: {created_again} (应该为False)")
    
    print("\n6. 统计信息")
    stats = state_manager.get_statistics()
    print(f"   总任务数: {stats['total']}")
    print(f"   按状态: {stats['by_status']}")
    print(f"   按类型: {stats['by_type']}")
    
    print("\n✅ 测试完成")

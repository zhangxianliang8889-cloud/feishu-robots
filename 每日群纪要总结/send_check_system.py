#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
发送检查系统 - 完善的备份与校验机制
防止重复发送、格式错误发送、异常发送
"""

import os
import json
import hashlib
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Tuple

class SendCheckSystem:
    """发送检查系统"""
    
    def __init__(self, records_file: str, content_version: str = "2.0"):
        """
        初始化发送检查系统
        
        Args:
            records_file: 发送记录文件路径
            content_version: 内容格式版本号
        """
        self.records_file = records_file
        self.content_version = content_version
        self.records = self._load_records()
    
    def _load_records(self) -> Dict:
        """加载发送记录"""
        if os.path.exists(self.records_file):
            try:
                with open(self.records_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return {}
        return {}
    
    def _save_records(self):
        """保存发送记录"""
        try:
            with open(self.records_file, 'w', encoding='utf-8') as f:
                json.dump(self.records, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"❌ 保存发送记录失败: {e}")
    
    def _generate_content_hash(self, content: str) -> str:
        """生成内容哈希值"""
        return hashlib.md5(content.encode('utf-8')).hexdigest()[:16]
    
    def _generate_record_key(self, group_id: str, report_type: str, date_key: str) -> str:
        """生成记录键"""
        return f"{group_id}_{report_type}_{date_key}"
    
    def check_before_send(self, group_id: str, report_type: str, date_key: str, 
                          content: str = None) -> Tuple[bool, str]:
        """
        发送前检查
        
        Args:
            group_id: 群ID
            report_type: 报告类型
            date_key: 日期键
            content: 待发送内容（可选）
        
        Returns:
            Tuple[bool, str]: (是否可以发送, 原因说明)
        """
        record_key = self._generate_record_key(group_id, report_type, date_key)
        
        if record_key in self.records:
            record = self.records[record_key]
            sent_time = record.get("sent_time", "")
            sent_version = record.get("content_version", "1.0")
            
            if sent_version == self.content_version:
                return (False, f"已发送过（版本{sent_version}，时间{sent_time}），跳过")
            else:
                return (False, f"已发送过旧版本{sent_version}（时间{sent_time}），不建议重复发送")
        
        if content:
            content_length = len(content)
            if content_length < 50:
                return (False, f"内容过短({content_length}字符)，可能格式错误")
            
            if "success" in content and "content" in content:
                return (False, "内容包含字典格式，可能是代码错误")
        
        return (True, "检查通过，可以发送")
    
    def record_send(self, group_id: str, report_type: str, date_key: str,
                    group_name: str, content: str = None, success: bool = True,
                    error_msg: str = None) -> bool:
        """
        记录发送结果
        
        Args:
            group_id: 群ID
            report_type: 报告类型
            date_key: 日期键
            group_name: 群名称
            content: 发送内容
            success: 是否成功
            error_msg: 错误信息
        
        Returns:
            bool: 是否记录成功
        """
        record_key = self._generate_record_key(group_id, report_type, date_key)
        
        record = {
            "group_name": group_name,
            "sent_time": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            "report_type": report_type,
            "date_key": date_key,
            "content_version": self.content_version,
            "success": success
        }
        
        if content:
            record["content_hash"] = self._generate_content_hash(content)
            record["content_length"] = len(content)
        
        if error_msg:
            record["error_msg"] = error_msg
        
        self.records[record_key] = record
        self._save_records()
        
        return True
    
    def get_send_status(self, group_id: str, report_type: str, date_key: str) -> Optional[Dict]:
        """
        获取发送状态
        
        Args:
            group_id: 群ID
            report_type: 报告类型
            date_key: 日期键
        
        Returns:
            Optional[Dict]: 发送记录，不存在返回None
        """
        record_key = self._generate_record_key(group_id, report_type, date_key)
        return self.records.get(record_key)
    
    def clean_old_records(self, days: int = 35) -> int:
        """
        清理过期记录
        
        Args:
            days: 保留天数
        
        Returns:
            int: 清理的记录数
        """
        now = datetime.now()
        keys_to_remove = []
        
        for key, value in self.records.items():
            try:
                sent_time = datetime.strptime(value.get("sent_time", ""), '%Y-%m-%d %H:%M:%S')
                days_diff = (now - sent_time).days
                if days_diff > days:
                    keys_to_remove.append(key)
            except:
                keys_to_remove.append(key)
        
        for key in keys_to_remove:
            del self.records[key]
        
        if keys_to_remove:
            self._save_records()
        
        return len(keys_to_remove)
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        获取发送统计
        
        Returns:
            Dict: 统计信息
        """
        total = len(self.records)
        success = sum(1 for r in self.records.values() if r.get("success", True))
        failed = total - success
        
        versions = {}
        for r in self.records.values():
            v = r.get("content_version", "1.0")
            versions[v] = versions.get(v, 0) + 1
        
        return {
            "total": total,
            "success": success,
            "failed": failed,
            "versions": versions
        }
    
    def validate_content_format(self, content: str, report_type: str) -> Tuple[bool, str]:
        """
        验证内容格式
        
        Args:
            content: 内容
            report_type: 报告类型
        
        Returns:
            Tuple[bool, str]: (是否有效, 原因)
        """
        if not content:
            return (False, "内容为空")
        
        if len(content) < 50:
            return (False, f"内容过短({len(content)}字符)")
        
        if "success" in content and "content" in content:
            return (False, "内容包含字典格式错误")
        
        if report_type in ["日报", "daily"]:
            if "📊" not in content:
                return (False, "日报缺少📊表情")
            if "消息" not in content:
                return (False, "日报缺少'消息'关键词")
        
        return (True, "格式验证通过")


class ContentVersionManager:
    """内容版本管理器"""
    
    VERSIONS = {
        "1.0": {
            "description": "旧格式 - 简单排行榜",
            "features": ["总消息数", "排行榜"],
            "deprecated": True
        },
        "2.0": {
            "description": "新格式 - 完整报告",
            "features": ["今日数据", "今日之星", "全员榜单", "激励语"],
            "deprecated": False
        }
    }
    
    @classmethod
    def get_current_version(cls) -> str:
        """获取当前版本"""
        return "2.0"
    
    @classmethod
    def get_version_info(cls, version: str) -> Optional[Dict]:
        """获取版本信息"""
        return cls.VERSIONS.get(version)
    
    @classmethod
    def is_deprecated(cls, version: str) -> bool:
        """检查版本是否已废弃"""
        info = cls.VERSIONS.get(version, {})
        return info.get("deprecated", True)


if __name__ == "__main__":
    print("🧪 测试发送检查系统")
    print("=" * 60)
    
    test_file = "/tmp/test_send_records.json"
    checker = SendCheckSystem(test_file, content_version="2.0")
    
    test_content = """
📊 测试群 - 群消息日报 (2026-03-07)

📈 今日数据：100 条消息 | 10/10 人活跃 (100%)

🏆 今日之星：🥇张三(20条) 🥈李四(15条) 🥉王五(10条)

📋 全员榜单：
   1. 张三: 20条 🔥
   2. 李四: 15条 🔥
   3. 王五: 10条 💬
    """.strip()
    
    print("\n1. 发送前检查")
    can_send, reason = checker.check_before_send("test_group_1", "日报", "2026-03-07", test_content)
    print(f"   可以发送: {can_send}")
    print(f"   原因: {reason}")
    
    print("\n2. 内容格式验证")
    is_valid, reason = checker.validate_content_format(test_content, "日报")
    print(f"   格式有效: {is_valid}")
    print(f"   原因: {reason}")
    
    print("\n3. 记录发送")
    checker.record_send("test_group_1", "日报", "2026-03-07", "测试群", test_content)
    print("   ✅ 已记录")
    
    print("\n4. 再次检查（应该跳过）")
    can_send, reason = checker.check_before_send("test_group_1", "日报", "2026-03-07", test_content)
    print(f"   可以发送: {can_send}")
    print(f"   原因: {reason}")
    
    print("\n5. 发送统计")
    stats = checker.get_statistics()
    print(f"   总记录: {stats['total']}")
    print(f"   成功: {stats['success']}")
    print(f"   版本分布: {stats['versions']}")
    
    os.remove(test_file)
    print("\n✅ 测试完成")

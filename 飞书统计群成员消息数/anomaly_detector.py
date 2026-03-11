#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据异常检测与告警系统
- 检测连续多日数据为0
- 检测数据突变
- 自动触发告警
"""

import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional

ALERT_LOG_FILE = "/root/feishu-bots/message_stats/alerts.json"
HISTORY_FILE = "/root/feishu-bots/message_stats/history.json"

class DataAnomalyDetector:
    """数据异常检测器"""
    
    def __init__(self):
        self.history = self._load_history()
        self.alerts = self._load_alerts()
    
    def _load_history(self) -> Dict:
        """加载历史数据"""
        if os.path.exists(HISTORY_FILE):
            try:
                with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                pass
        return {"records": []}
    
    def _save_history(self):
        """保存历史数据"""
        try:
            with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.history, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存历史数据失败: {e}")
    
    def _load_alerts(self) -> Dict:
        """加载告警记录"""
        if os.path.exists(ALERT_LOG_FILE):
            try:
                with open(ALERT_LOG_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                pass
        return {"alerts": []}
    
    def _save_alerts(self):
        """保存告警记录"""
        try:
            with open(ALERT_LOG_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.alerts, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存告警记录失败: {e}")
    
    def record_data(self, group_name: str, report_type: str, message_count: int, participant_count: int):
        """记录数据"""
        record = {
            "group_name": group_name,
            "report_type": report_type,
            "message_count": message_count,
            "participant_count": participant_count,
            "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            "date": datetime.now().strftime('%Y-%m-%d')
        }
        
        self.history["records"].append(record)
        
        if len(self.history["records"]) > 1000:
            self.history["records"] = self.history["records"][-500:]
        
        self._save_history()
        
        return self._check_anomaly(record)
    
    def _check_anomaly(self, current_record: Dict) -> Optional[Dict]:
        """检查数据异常"""
        anomalies = []
        
        anomaly_1 = self._check_zero_data(current_record)
        if anomaly_1:
            anomalies.append(anomaly_1)
        
        anomaly_2 = self._check_sudden_change(current_record)
        if anomaly_2:
            anomalies.append(anomaly_2)
        
        if anomalies:
            alert = {
                "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                "group_name": current_record["group_name"],
                "report_type": current_record["report_type"],
                "anomalies": anomalies,
                "status": "pending"
            }
            self.alerts["alerts"].append(alert)
            self._save_alerts()
            return alert
        
        return None
    
    def _check_zero_data(self, current_record: Dict) -> Optional[Dict]:
        """检查连续零数据"""
        group_name = current_record["group_name"]
        report_type = current_record["report_type"]
        
        recent_records = [
            r for r in self.history["records"]
            if r["group_name"] == group_name 
            and r["report_type"] == report_type
            and r["message_count"] == 0
        ][-5:]
        
        if len(recent_records) >= 3:
            return {
                "type": "continuous_zero",
                "severity": "high",
                "description": f"连续{len(recent_records)}次{report_type}数据为0",
                "suggestion": "请检查API连接、时间参数、群组权限"
            }
        
        return None
    
    def _check_sudden_change(self, current_record: Dict) -> Optional[Dict]:
        """检查数据突变"""
        group_name = current_record["group_name"]
        report_type = current_record["report_type"]
        current_count = current_record["message_count"]
        
        previous_records = [
            r for r in self.history["records"]
            if r["group_name"] == group_name 
            and r["report_type"] == report_type
            and r["message_count"] > 0
        ][-5:]
        
        if previous_records:
            avg_count = sum(r["message_count"] for r in previous_records) / len(previous_records)
            
            if avg_count > 0:
                if current_count == 0 and avg_count >= 10:
                    return {
                        "type": "sudden_drop",
                        "severity": "high",
                        "description": f"消息数从平均{avg_count:.0f}条突降到0",
                        "suggestion": "请检查API是否正常、群组是否有新消息"
                    }
                
                if current_count > avg_count * 3 and avg_count >= 5:
                    return {
                        "type": "sudden_spike",
                        "severity": "medium",
                        "description": f"消息数从平均{avg_count:.0f}条突增到{current_count}条",
                        "suggestion": "可能存在异常活动，建议人工复核"
                    }
        
        return None
    
    def get_pending_alerts(self) -> List[Dict]:
        """获取待处理告警"""
        return [a for a in self.alerts["alerts"] if a["status"] == "pending"]
    
    def mark_alert_resolved(self, alert_index: int):
        """标记告警已解决"""
        if 0 <= alert_index < len(self.alerts["alerts"]):
            self.alerts["alerts"][alert_index]["status"] = "resolved"
            self.alerts["alerts"][alert_index]["resolved_at"] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            self._save_alerts()
    
    def generate_alert_report(self) -> str:
        """生成告警报告"""
        pending = self.get_pending_alerts()
        
        if not pending:
            return "✅ 无待处理告警"
        
        report = []
        report.append("⚠️ 数据异常告警报告")
        report.append("=" * 40)
        report.append(f"📅 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"📊 待处理告警: {len(pending)} 条")
        report.append("")
        
        for i, alert in enumerate(pending[-10:], 1):
            report.append(f"告警 #{i}")
            report.append(f"  时间: {alert['timestamp']}")
            report.append(f"  群组: {alert['group_name']}")
            report.append(f"  类型: {alert['report_type']}")
            report.append(f"  异常:")
            for anomaly in alert["anomalies"]:
                report.append(f"    • {anomaly['description']}")
                report.append(f"      建议: {anomaly['suggestion']}")
            report.append("")
        
        return '\n'.join(report)


def validate_data_quality(message_count: int, participant_count: int, group_name: str, report_type: str) -> Dict:
    """
    验证数据质量
    
    Returns:
        Dict: 包含验证结果和建议
    """
    result = {
        "valid": True,
        "warnings": [],
        "suggestions": []
    }
    
    if message_count == 0:
        result["warnings"].append("消息数为0")
        result["suggestions"].append("请确认群内是否有消息")
    
    if participant_count == 0 and message_count > 0:
        result["warnings"].append("消息数>0但参与人数为0")
        result["suggestions"].append("请检查用户统计逻辑")
    
    if message_count > 0 and participant_count == 0:
        result["valid"] = False
        result["suggestions"].append("数据不一致，建议复核")
    
    return result


if __name__ == "__main__":
    detector = DataAnomalyDetector()
    
    test_record = {
        "group_name": "测试群",
        "report_type": "日报",
        "message_count": 0,
        "participant_count": 0
    }
    
    alert = detector.record_data(
        test_record["group_name"],
        test_record["report_type"],
        test_record["message_count"],
        test_record["participant_count"]
    )
    
    if alert:
        print("⚠️ 检测到数据异常:")
        print(json.dumps(alert, ensure_ascii=False, indent=2))
    else:
        print("✅ 数据正常")

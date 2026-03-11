#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
统一配置管理器 - 集中管理所有配置
支持环境变量、配置文件、默认值优先级
"""

import os
import json
from typing import Any, Dict, Optional
from datetime import datetime

class ConfigManager:
    """统一配置管理器"""
    
    _instance = None
    _config = None
    
    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self, config_file: str = None):
        """
        初始化配置管理器
        
        Args:
            config_file: 配置文件路径
        """
        if self._config is not None:
            return
            
        self.config_file = config_file or os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "unified_config.json"
        )
        self._config = self._load_config()
    
    def _load_config(self) -> Dict:
        """加载配置"""
        config = self._get_default_config()
        
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    file_config = json.load(f)
                    self._deep_merge(config, file_config)
            except:
                pass
        
        for key in config:
            env_value = os.environ.get(key)
            if env_value is not None:
                config[key] = self._parse_env_value(env_value, config[key])
        
        return config
    
    def _get_default_config(self) -> Dict:
        """获取默认配置"""
        return {
            "FEISHU_MEETING_APP_ID": "",
            "FEISHU_MEETING_APP_SECRET": "",
            "FEISHU_STATS_APP_ID": "",
            "FEISHU_STATS_APP_SECRET": "",
            
            "AI_API_KEY": "",
            "AI_API_URL": "https://ark.cn-beijing.volces.com/api/v3/chat/completions",
            "AI_MODEL": "ep-20250227094607-mwrn9",
            
            "DAILY_SEND_TIME": "07:00",
            "WEEKLY_SEND_TIME": "07:30",
            "MONTHLY_SEND_TIME": "08:00",
            
            "MAX_CONCURRENT_GROUPS": 5,
            "MAX_RETRIES": 3,
            "RETRY_INTERVAL": 300,
            "API_RATE_LIMIT": 10,
            "API_RATE_WINDOW": 60,
            
            "MIN_MESSAGE_COUNT": 3,
            "SKIP_EMPTY_GROUPS": True,
            "SKIP_SYSTEM_ONLY": True,
            
            "LOG_LEVEL": "INFO",
            "LOG_DIR": "logs",
            "LOG_MAX_DAYS": 30,
            
            "ENABLE_MONITORING": True,
            "ENABLE_ALERTS": False,
            "ALERT_WEBHOOK": "",
            
            "CONTENT_VERSION": "2.0",
            "SHOW_GENERATE_TIME": True,
            "SHOW_BOT_SIGNATURE": True
        }
    
    def _deep_merge(self, base: Dict, override: Dict):
        """深度合并字典"""
        for key, value in override.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._deep_merge(base[key], value)
            else:
                base[key] = value
    
    def _parse_env_value(self, env_value: str, default_value: Any) -> Any:
        """解析环境变量值"""
        if isinstance(default_value, bool):
            return env_value.lower() in ('true', '1', 'yes')
        elif isinstance(default_value, int):
            return int(env_value)
        elif isinstance(default_value, float):
            return float(env_value)
        else:
            return env_value
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        获取配置值
        
        Args:
            key: 配置键
            default: 默认值
        
        Returns:
            Any: 配置值
        """
        return self._config.get(key, default)
    
    def set(self, key: str, value: Any):
        """
        设置配置值
        
        Args:
            key: 配置键
            value: 配置值
        """
        self._config[key] = value
    
    def save(self):
        """保存配置到文件"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self._config, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"❌ 保存配置失败: {e}")
    
    def get_all(self) -> Dict:
        """获取所有配置"""
        return self._config.copy()
    
    def get_feishu_config(self, bot_type: str = "meeting") -> Dict:
        """
        获取飞书配置
        
        Args:
            bot_type: 机器人类型 (meeting/stats)
        
        Returns:
            Dict: 飞书配置
        """
        if bot_type == "meeting":
            return {
                "app_id": self.get("FEISHU_MEETING_APP_ID"),
                "app_secret": self.get("FEISHU_MEETING_APP_SECRET")
            }
        else:
            return {
                "app_id": self.get("FEISHU_STATS_APP_ID"),
                "app_secret": self.get("FEISHU_STATS_APP_SECRET")
            }
    
    def get_ai_config(self) -> Dict:
        """获取AI配置"""
        return {
            "api_key": self.get("AI_API_KEY"),
            "api_url": self.get("AI_API_URL"),
            "model": self.get("AI_MODEL")
        }
    
    def get_retry_config(self) -> Dict:
        """获取重试配置"""
        return {
            "max_retries": self.get("MAX_RETRIES"),
            "retry_interval": self.get("RETRY_INTERVAL"),
            "rate_limit": self.get("API_RATE_LIMIT"),
            "rate_window": self.get("API_RATE_WINDOW")
        }


class UnifiedLogger:
    """统一日志管理器"""
    
    _instance = None
    
    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self, log_dir: str = None, log_level: str = "INFO"):
        """
        初始化日志管理器
        
        Args:
            log_dir: 日志目录
            log_level: 日志级别
        """
        if hasattr(self, '_initialized') and self._initialized:
            return
            
        self._initialized = True
        self.log_dir = log_dir or "logs"
        self.log_level = log_level
        
        os.makedirs(self.log_dir, exist_ok=True)
        
        self.log_file = os.path.join(
            self.log_dir, 
            f"bot_{datetime.now().strftime('%Y%m%d')}.log"
        )
        
        self.levels = {
            "DEBUG": 10,
            "INFO": 20,
            "WARNING": 30,
            "ERROR": 40,
            "CRITICAL": 50
        }
    
    def _write_log(self, level: str, message: str, **kwargs):
        """写入日志"""
        if self.levels.get(level, 20) < self.levels.get(self.log_level, 20):
            return
        
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        extra = " ".join([f"[{k}={v}]" for k, v in kwargs.items()])
        log_line = f"[{timestamp}] [{level}] {message} {extra}\n"
        
        print(log_line.strip())
        
        try:
            with open(self.log_file, 'a', encoding='utf-8') as f:
                f.write(log_line)
        except:
            pass
    
    def debug(self, message: str, **kwargs):
        """调试日志"""
        self._write_log("DEBUG", message, **kwargs)
    
    def info(self, message: str, **kwargs):
        """信息日志"""
        self._write_log("INFO", message, **kwargs)
    
    def warning(self, message: str, **kwargs):
        """警告日志"""
        self._write_log("WARNING", message, **kwargs)
    
    def error(self, message: str, **kwargs):
        """错误日志"""
        self._write_log("ERROR", message, **kwargs)
    
    def critical(self, message: str, **kwargs):
        """严重错误日志"""
        self._write_log("CRITICAL", message, **kwargs)


class MonitoringSystem:
    """监控系统"""
    
    def __init__(self, config: ConfigManager = None):
        """
        初始化监控系统
        
        Args:
            config: 配置管理器
        """
        self.config = config or ConfigManager()
        self.metrics = {}
        self.alerts = []
    
    def record_metric(self, name: str, value: float, tags: Dict = None):
        """
        记录指标
        
        Args:
            name: 指标名称
            value: 指标值
            tags: 标签
        """
        if name not in self.metrics:
            self.metrics[name] = []
        
        self.metrics[name].append({
            "value": value,
            "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            "tags": tags or {}
        })
    
    def increment_counter(self, name: str, tags: Dict = None):
        """
        增加计数器
        
        Args:
            name: 计数器名称
            tags: 标签
        """
        current = sum(m["value"] for m in self.metrics.get(name, []))
        self.record_metric(name, 1, tags)
    
    def send_alert(self, level: str, title: str, message: str):
        """
        发送告警
        
        Args:
            level: 告警级别
            title: 告警标题
            message: 告警内容
        """
        alert = {
            "level": level,
            "title": title,
            "message": message,
            "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        self.alerts.append(alert)
        
        webhook = self.config.get("ALERT_WEBHOOK")
        if webhook and self.config.get("ENABLE_ALERTS"):
            try:
                import requests
                requests.post(webhook, json=alert, timeout=5)
            except:
                pass
    
    def get_statistics(self) -> Dict:
        """获取统计信息"""
        stats = {}
        for name, values in self.metrics.items():
            if values:
                total = sum(v["value"] for v in values)
                stats[name] = {
                    "count": len(values),
                    "total": total,
                    "avg": total / len(values),
                    "last": values[-1]["timestamp"]
                }
        return stats


if __name__ == "__main__":
    print("🧪 测试统一配置管理器")
    print("=" * 60)
    
    config = ConfigManager("/tmp/test_config.json")
    
    print("\n1. 配置管理")
    config.set("TEST_KEY", "test_value")
    print(f"   获取配置: {config.get('TEST_KEY')}")
    print(f"   获取默认: {config.get('NOT_EXISTS', 'default')}")
    
    print("\n2. 飞书配置")
    feishu_config = config.get_feishu_config("meeting")
    print(f"   Meeting App ID: {feishu_config['app_id'][:10] if feishu_config['app_id'] else 'Not Set'}...")
    
    print("\n3. AI配置")
    ai_config = config.get_ai_config()
    print(f"   AI Model: {ai_config['model']}")
    
    print("\n4. 日志测试")
    logger = UnifiedLogger("/tmp/test_logs")
    logger.info("这是一条测试日志")
    logger.warning("这是一条警告日志")
    logger.error("这是一条错误日志")
    
    print("\n5. 监控测试")
    monitoring = MonitoringSystem(config)
    monitoring.increment_counter("api_calls", {"type": "feishu"})
    monitoring.increment_counter("api_calls", {"type": "ai"})
    monitoring.record_metric("response_time", 1.5, {"api": "feishu"})
    
    stats = monitoring.get_statistics()
    print(f"   API调用次数: {stats.get('api_calls', {}).get('total', 0)}")
    
    print("\n✅ 测试完成")

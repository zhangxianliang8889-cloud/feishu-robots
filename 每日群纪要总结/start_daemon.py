#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
启动脚本 - 同时启动两个机器人的守护进程
运行此脚本后可以安心睡觉，机器人会自动运行
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from daemon_manager import MultiBotDaemon

if __name__ == "__main__":
    print("=" * 60)
    print("🚀 启动双机器人守护进程")
    print("=" * 60)
    print("")
    
    daemon = MultiBotDaemon()
    
    daemon.add_bot(
        name="群会议纪要机器人",
        script_path="/Users/yueguangbaohe/Documents/trae_projects/pi_digits/每日群纪要总结/群会议纪要_最终版.py",
        max_restarts=10,
        restart_interval=60
    )
    
    daemon.add_bot(
        name="群消息统计机器人",
        script_path="/Users/yueguangbaohe/Documents/trae_projects/pi_digits/每日群纪要总结/../飞书统计群成员消息数/多群统计.py",
        max_restarts=10,
        restart_interval=60
    )
    
    print("")
    print("💡 提示:")
    print("   - 按 Ctrl+C 可以停止所有机器人")
    print("   - 机器人会自动重启（最多10次）")
    print("   - 网络断开时会自动等待恢复")
    print("   - 可以安心睡觉了！💤")
    print("")
    
    daemon.run()

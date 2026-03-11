#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
完整双向同步管理器
同步两个项目：
1. 飞书统计群成员消息数 ↔ /root/feishu-bots/message_stats
2. 每日群纪要总结 ↔ /root/feishu-bots/meeting_summary
"""

import os
import hashlib
import subprocess
from datetime import datetime

# 配置
SERVER = "root@115.191.47.166"

# 项目配置
PROJECTS = [
    {
        "name": "飞书统计群成员消息数",
        "local_dir": "/Users/yueguangbaohe/Documents/trae_projects/pi_digits/飞书统计群成员消息数",
        "remote_dir": "/root/feishu-bots/message_stats",
        "files": [
            "多群统计.py",
            "test_statistics_bot.py",
            "anomaly_detector.py",
            "config.py",
            "user_name_cache.py",
            "send_check_system.py",
            "incremental_fetcher.py",
            "enhanced_api_client.py",
            "task_state_manager.py",
            "unified_config.py"
        ]
    },
    {
        "name": "每日群纪要总结",
        "local_dir": "/Users/yueguangbaohe/Documents/trae_projects/pi_digits/每日群纪要总结",
        "remote_dir": "/root/feishu-bots/meeting_summary",
        "files": [
            "群会议纪要_最终版.py",
            "config.py",
            "ai_summarizer.py",
            "smart_summarizer.py",
            "unified_summarizer.py",
            "unified_config.py",
            "unified_interface.py",
            "concurrent_processor.py",
            "daemon_manager.py",
            "send_check_system.py",
            "incremental_fetcher.py",
            "enhanced_api_client.py",
            "task_state_manager.py"
        ]
    }
]

def get_file_md5(filepath):
    """计算文件MD5"""
    if not os.path.exists(filepath):
        return None
    try:
        with open(filepath, 'rb') as f:
            return hashlib.md5(f.read()).hexdigest()
    except Exception as e:
        print(f"    ⚠️ 读取文件失败: {e}")
        return None

def get_remote_md5(server, remote_path):
    """获取远程文件MD5"""
    try:
        result = subprocess.run(
            ["ssh", "-o", "StrictHostKeyChecking=no", server, f"md5sum {remote_path} 2>/dev/null || echo 'ERROR'"],
            capture_output=True, text=True, timeout=15
        )
        if result.returncode == 0:
            output = result.stdout.strip()
            if output and not output.startswith('ERROR'):
                return output.split()[0]
    except Exception as e:
        print(f"    ⚠️ 获取远程MD5失败: {e}")
    return None

def sync_to_remote(local_file, remote_path):
    """同步本地到远程"""
    try:
        result = subprocess.run(
            ["scp", "-o", "StrictHostKeyChecking=no", local_file, f"{SERVER}:{remote_path}"],
            capture_output=True, text=True, timeout=30
        )
        return result.returncode == 0
    except Exception as e:
        print(f"    ❌ 同步失败: {e}")
        return False

def sync_from_remote(remote_path, local_file):
    """同步远程到本地"""
    try:
        result = subprocess.run(
            ["scp", "-o", "StrictHostKeyChecking=no", f"{SERVER}:{remote_path}", local_file],
            capture_output=True, text=True, timeout=30
        )
        return result.returncode == 0
    except Exception as e:
        print(f"    ❌ 同步失败: {e}")
        return False

def sync_project(project):
    """同步一个项目"""
    print(f"\n{'=' * 70}")
    print(f"📁 同步项目: {project['name']}")
    print(f"{'=' * 70}")
    print(f"本地目录: {project['local_dir']}")
    print(f"远程目录: {project['remote_dir']}")
    
    sync_log = []
    
    for filename in project['files']:
        print(f"\n处理文件: {filename}")
        local_path = os.path.join(project['local_dir'], filename)
        remote_path = f"{project['remote_dir']}/{filename}"
        
        local_md5 = get_file_md5(local_path)
        remote_md5 = get_remote_md5(SERVER, remote_path)
        
        print(f"  本地MD5: {local_md5 or 'N/A'}")
        print(f"  远程MD5: {remote_md5 or 'N/A'}")
        
        if local_md5 is None and remote_md5 is None:
            print(f"  ⚠️ 双端文件都不存在，跳过")
            sync_log.append(f"{filename}: 双端都不存在")
            continue
        
        if local_md5 is None:
            print(f"  ⚠️ 本地文件不存在，从远程同步到本地...")
            if sync_from_remote(remote_path, local_path):
                print(f"  ✅ 同步成功 (远程→本地)")
                sync_log.append(f"{filename}: 远程→本地")
            else:
                print(f"  ❌ 同步失败")
                sync_log.append(f"{filename}: 同步失败")
            continue
        
        if remote_md5 is None:
            print(f"  ⚠️ 远程文件不存在，从本地同步到远程...")
            if sync_to_remote(local_path, remote_path):
                print(f"  ✅ 同步成功 (本地→远程)")
                sync_log.append(f"{filename}: 本地→远程")
            else:
                print(f"  ❌ 同步失败")
                sync_log.append(f"{filename}: 同步失败")
            continue
        
        if local_md5 != remote_md5:
            print(f"  ⚠️ MD5不一致，以本地为准同步到远程...")
            if sync_to_remote(local_path, remote_path):
                print(f"  ✅ 同步成功 (本地→远程)")
                sync_log.append(f"{filename}: 本地→远程 (MD5不一致)")
            else:
                print(f"  ❌ 同步失败")
                sync_log.append(f"{filename}: 同步失败")
            continue
        
        print(f"  ✅ MD5一致，无需同步")
        sync_log.append(f"{filename}: 已同步")
    
    return sync_log

def main():
    print("=" * 70)
    print("🔄 完整双向同步管理器")
    print("=" * 70)
    print(f"同步时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"目标服务器: {SERVER}")
    
    all_sync_logs = []
    
    for project in PROJECTS:
        sync_log = sync_project(project)
        all_sync_logs.extend([f"[{project['name']}] {log}" for log in sync_log])
    
    print("\n" + "=" * 70)
    print("📊 同步摘要")
    print("=" * 70)
    for log in all_sync_logs:
        print(f"  {log}")
    
    # 保存同步记录
    log_file = "/Users/yueguangbaohe/Documents/trae_projects/pi_digits/full_sync_log.txt"
    try:
        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(f"\n{'='*70}\n")
            f.write(f"同步时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            for log in all_sync_logs:
                f.write(f"  {log}\n")
        print(f"\n✅ 同步记录已保存到: {log_file}")
    except Exception as e:
        print(f"\n⚠️ 保存同步记录失败: {e}")
    
    print("\n" + "=" * 70)
    print("✅ 同步完成！")
    print("=" * 70)

if __name__ == "__main__":
    main()

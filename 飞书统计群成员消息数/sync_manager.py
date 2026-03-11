#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
双向同步管理器 - 确保本地和服务器代码完全一致
"""

import os
import hashlib
import subprocess
from datetime import datetime

# 配置
LOCAL_DIR = "/Users/yueguangbaohe/Documents/trae_projects/pi_digits/飞书统计群成员消息数"
REMOTE_DIR = "/root/feishu-bots/message_stats"
SERVER = "root@115.191.47.166"

# 需要同步的文件
SYNC_FILES = [
    "多群统计.py",
    "test_statistics_bot.py",
    "anomaly_detector.py",
    "config.py",
    "user_name_cache.py"
]

def get_file_md5(filepath):
    """计算文件MD5"""
    if not os.path.exists(filepath):
        return None
    with open(filepath, 'rb') as f:
        return hashlib.md5(f.read()).hexdigest()

def get_remote_md5(server, remote_path):
    """获取远程文件MD5"""
    try:
        result = subprocess.run(
            ["ssh", "-o", "StrictHostKeyChecking=no", server, f"md5sum {remote_path}"],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0:
            return result.stdout.split()[0]
    except:
        pass
    return None

def sync_to_remote(local_file, remote_file):
    """同步本地到远程"""
    try:
        result = subprocess.run(
            ["scp", "-o", "StrictHostKeyChecking=no", local_file, f"{SERVER}:{remote_file}"],
            capture_output=True, text=True, timeout=30
        )
        return result.returncode == 0
    except Exception as e:
        print(f"同步失败: {e}")
        return False

def sync_from_remote(remote_file, local_file):
    """同步远程到本地"""
    try:
        result = subprocess.run(
            ["scp", "-o", "StrictHostKeyChecking=no", f"{SERVER}:{remote_file}", local_file],
            capture_output=True, text=True, timeout=30
        )
        return result.returncode == 0
    except Exception as e:
        print(f"同步失败: {e}")
        return False

def main():
    print("=" * 70)
    print("双向同步管理器")
    print("=" * 70)
    print(f"同步时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"本地目录: {LOCAL_DIR}")
    print(f"远程目录: {SERVER}:{REMOTE_DIR}")
    print("=" * 70)
    
    sync_log = []
    
    for filename in SYNC_FILES:
        print(f"\n处理文件: {filename}")
        local_path = os.path.join(LOCAL_DIR, filename)
        remote_path = f"{REMOTE_DIR}/{filename}"
        
        local_md5 = get_file_md5(local_path)
        remote_md5 = get_remote_md5(SERVER, remote_path)
        
        print(f"  本地MD5: {local_md5 or 'N/A'}")
        print(f"  远程MD5: {remote_md5 or 'N/A'}")
        
        if local_md5 is None:
            print(f"  ⚠️ 本地文件不存在，从远程同步到本地...")
            if sync_from_remote(remote_path, local_path):
                print(f"  ✅ 同步成功")
                sync_log.append(f"{filename}: 远程 -> 本地")
            else:
                print(f"  ❌ 同步失败")
                sync_log.append(f"{filename}: 同步失败")
        elif remote_md5 is None:
            print(f"  ⚠️ 远程文件不存在，从本地同步到远程...")
            if sync_to_remote(local_path, remote_path):
                print(f"  ✅ 同步成功")
                sync_log.append(f"{filename}: 本地 -> 远程")
            else:
                print(f"  ❌ 同步失败")
                sync_log.append(f"{filename}: 同步失败")
        elif local_md5 != remote_md5:
            print(f"  ⚠️ MD5不一致，以本地为准同步到远程...")
            if sync_to_remote(local_path, remote_path):
                print(f"  ✅ 同步成功")
                sync_log.append(f"{filename}: 本地 -> 远程 (MD5不一致)")
            else:
                print(f"  ❌ 同步失败")
                sync_log.append(f"{filename}: 同步失败")
        else:
            print(f"  ✅ MD5一致，无需同步")
            sync_log.append(f"{filename}: 已同步")
    
    print("\n" + "=" * 70)
    print("同步摘要")
    print("=" * 70)
    for log in sync_log:
        print(f"  {log}")
    
    # 保存同步记录
    log_file = os.path.join(LOCAL_DIR, "sync_log.txt")
    with open(log_file, 'a', encoding='utf-8') as f:
        f.write(f"\n{'='*70}\n")
        f.write(f"同步时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        for log in sync_log:
            f.write(f"  {log}\n")
    
    print(f"\n同步记录已保存到: {log_file}")
    print("=" * 70)

if __name__ == "__main__":
    main()

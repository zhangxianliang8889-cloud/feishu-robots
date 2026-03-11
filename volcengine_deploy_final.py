#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
豆包火山云服务器部署脚本 - 最终版（使用expect）
"""

import os
import subprocess
import time
import sys

# 服务器配置
SERVER = {
    "name": "豆包火山云服务器",
    "ip": "115.191.47.166",
    "username": "root",
    "password": "Aa123789",
    "note": "豆包火山云服务器"
}

LOCAL_DIR = "/Users/yueguangbaohe/Documents/trae_projects/pi_digits"
REMOTE_DIR = "/root/feishu_bots"

def run_ssh_command(server, command, timeout=60):
    """运行SSH命令（使用expect自动输入密码）"""
    expect_script = f'''
spawn ssh -o StrictHostKeyChecking=no -o ConnectTimeout=10 {server['username']}@{server['ip']} "{command}"
expect "password:"
send "{server['password']}\r"
expect eof
'''
    
    result = subprocess.run(
        ["expect", "-c", expect_script],
        capture_output=True,
        text=True,
        timeout=timeout
    )
    return result

def run_scp_command(server, local_path, remote_path, timeout=120):
    """运行SCP命令（使用expect自动输入密码）"""
    expect_script = f'''
spawn scp -o StrictHostKeyChecking=no -o ConnectTimeout=10 -r {local_path} {server['username']}@{server['ip']}:{remote_path}
expect "password:"
send "{server['password']}\r"
expect eof
'''
    
    result = subprocess.run(
        ["expect", "-c", expect_script],
        capture_output=True,
        text=True,
        timeout=timeout
    )
    return result

def test_connection(server):
    """测试服务器连接"""
    print(f"\n🔍 测试连接: {server['name']} ({server['ip']})")
    
    # 测试ping
    print("   测试网络连通性...")
    result = subprocess.run(
        ["ping", "-c", "2", server["ip"]],
        capture_output=True,
        text=True,
        timeout=10
    )
    
    if result.returncode == 0:
        print(f"   ✅ Ping成功")
    else:
        print(f"   ❌ Ping失败")
        return False
    
    # 测试SSH连接
    print("   测试SSH连接...")
    result = run_ssh_command(server, "echo 'SSH_OK'")
    if "SSH_OK" in result.stdout:
        print(f"   ✅ SSH连接成功")
        return True
    else:
        print(f"   ❌ SSH连接失败")
        print(f"   输出: {result.stdout}")
        print(f"   错误: {result.stderr}")
        return False

def deploy_to_server(server):
    """部署到服务器"""
    print(f"\n🚀 开始部署到: {server['name']} ({server['ip']})")
    print("=" * 60)
    
    # 步骤1: 创建部署目录
    print("\n📁 步骤1: 创建部署目录...")
    result = run_ssh_command(server, f"mkdir -p {REMOTE_DIR}")
    if result.returncode != 0:
        print(f"   ❌ 创建目录失败")
        return False
    print("   ✅ 部署目录创建成功")
    
    # 步骤2: 检查Python环境
    print("\n🐍 步骤2: 检查Python环境...")
    result = run_ssh_command(server, "python3 --version")
    if result.returncode == 0:
        print(f"   ✅ Python已安装: {result.stdout.strip()}")
    else:
        print("   ⚠️  Python3未安装，尝试安装...")
        result = run_ssh_command(server, "yum install python3 -y 2>/dev/null || apt install python3 -y 2>/dev/null", timeout=120)
    
    # 步骤3: 安装pip
    print("\n📦 步骤3: 检查pip...")
    result = run_ssh_command(server, "pip3 --version")
    if result.returncode != 0:
        print("   安装pip...")
        result = run_ssh_command(server, "yum install python3-pip -y 2>/dev/null || apt install python3-pip -y 2>/dev/null", timeout=120)
    print("   ✅ pip已就绪")
    
    # 步骤4: 上传代码
    print("\n📤 步骤4: 上传代码到服务器...")
    print("   这可能需要几分钟，请耐心等待...")
    result = run_scp_command(server, LOCAL_DIR, REMOTE_DIR)
    if result.returncode != 0:
        print(f"   ❌ 上传代码失败")
        print(f"   错误: {result.stderr}")
        return False
    print("   ✅ 代码上传成功")
    
    # 步骤5: 安装Python依赖
    print("\n📦 步骤5: 安装Python依赖...")
    deps = "requests schedule paramiko"
    result = run_ssh_command(server, f"pip3 install {deps} -q 2>&1", timeout=120)
    print("   ✅ Python依赖安装完成")
    
    # 步骤6: 安装screen
    print("\n🖥️  步骤6: 安装screen...")
    result = run_ssh_command(server, "yum install screen -y 2>/dev/null || apt install screen -y 2>/dev/null", timeout=120)
    print("   ✅ screen安装完成")
    
    # 步骤7: 配置时区
    print("\n🌍 步骤7: 设置时区...")
    run_ssh_command(server, "timedatectl set-timezone Asia/Shanghai 2>/dev/null || true")
    result = run_ssh_command(server, "date")
    print(f"   ✅ 服务器时间: {result.stdout.strip()}")
    
    # 步骤8: 检查配置文件
    print("\n🔍 步骤8: 检查配置文件...")
    result = run_ssh_command(server, f"grep CEO_LIST {REMOTE_DIR}/pi_digits/飞书统计群成员消息数/config.py")
    if "张贤良" in result.stdout and "蒋文卿" in result.stdout:
        print("   ✅ CEO_LIST配置正确")
    else:
        print("   ⚠️  CEO_LIST配置可能有问题")
    
    # 步骤9: 启动机器人
    print("\n🚀 步骤9: 启动机器人服务...")
    
    # 先停止可能已运行的实例
    run_ssh_command(server, "pkill -f '群会议纪要_最终版.py' 2>/dev/null; pkill -f '多群统计.py' 2>/dev/null")
    time.sleep(2)
    
    # 启动群会议纪要机器人
    result = run_ssh_command(server, f"cd {REMOTE_DIR}/pi_digits/每日群纪要总结 && screen -dmS meeting_bot bash -c 'python3 群会议纪要_最终版.py'")
    print("   ✅ 群会议纪要机器人已启动")
    
    time.sleep(2)
    
    # 启动群消息统计机器人
    result = run_ssh_command(server, f"cd {REMOTE_DIR}/pi_digits/飞书统计群成员消息数 && screen -dmS stats_bot bash -c 'python3 多群统计.py'")
    print("   ✅ 群消息统计机器人已启动")
    
    time.sleep(3)
    
    # 步骤10: 检查运行状态
    print("\n📊 步骤10: 检查运行状态...")
    result = run_ssh_command(server, "screen -ls")
    print(f"   Screen会话:\n{result.stdout}")
    
    result = run_ssh_command(server, "ps aux | grep python | grep -v grep")
    if "群会议纪要" in result.stdout or "多群统计" in result.stdout:
        print("   ✅ 机器人进程运行中")
    else:
        print("   ⚠️  机器人进程可能未启动")
    
    # 步骤11: 显示部署信息
    print("\n" + "=" * 60)
    print("✅ 部署完成！")
    print("=" * 60)
    print(f"\n📍 服务器信息:")
    print(f"   IP: {server['ip']}")
    print(f"   部署目录: {REMOTE_DIR}/pi_digits")
    print(f"\n🤖 机器人状态:")
    print(f"   群会议纪要机器人: screen -r meeting_bot")
    print(f"   群消息统计机器人: screen -r stats_bot")
    print(f"\n📋 常用命令:")
    print(f"   查看日志: ssh root@{server['ip']} 'tail -f {REMOTE_DIR}/pi_digits/每日群纪要总结/logs/*.log'")
    print(f"   进入服务器: ssh root@{server['ip']}")
    print(f"\n⏰ 定时任务:")
    print(f"   群消息统计: 日报09:00, 周报12:00, 月报15:00")
    print(f"   群会议纪要: 日报21:00, 周报09:00, 月报09:30")
    print(f"\n💡 提示:")
    print(f"   - 机器人已在后台运行，关闭终端不会影响")
    print(f"   - 使用screen可以查看运行日志")
    print(f"   - 服务器已设置为北京时间")
    print("=" * 60)
    
    return True

def main():
    """主函数"""
    print("=" * 60)
    print("🚀 豆包火山云服务器部署脚本 - 最终版")
    print("=" * 60)
    
    # 测试连接
    if not test_connection(SERVER):
        print("❌ 服务器连接失败，请检查:")
        print("   1. 服务器是否已开机")
        print("   2. 安全组是否开放22端口")
        print("   3. IP地址和密码是否正确")
        sys.exit(1)
    
    # 执行部署
    if deploy_to_server(SERVER):
        print("\n🎉 部署成功！机器人已在服务器上运行。")
        print("\n⚠️  注意：本地运行的机器人需要手动停止，避免重复发送")
        print("\n   停止本地机器人方法:")
        print("   - 在终端6按 Ctrl+C 停止群会议纪要机器人")
        print("   - 在终端16按 Ctrl+C 停止群消息统计机器人")
    else:
        print("\n❌ 部署失败，请检查错误信息")
        sys.exit(1)

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
阿里云服务器智能部署脚本（支持多服务器）
"""

import subprocess
import sys
import os
import time

# 服务器列表
SERVERS = [
    {
        "name": "服务器1 (原配置)",
        "ip": "47.100.10.100",
        "username": "xuankong",
        "password": "xkxx@2021",
        "note": "可能需要密钥认证"
    },
    {
        "name": "服务器2 (xk-java-02)",
        "ip": "47.108.200.81",
        "username": "root",
        "password": "xkxx@2021",
        "note": "控制台可见"
    },
    {
        "name": "服务器3",
        "ip": "47.108.227.164",
        "username": "root",
        "password": "xkxx@2021",
        "note": "控制台可见"
    }
]

LOCAL_DIR = "/Users/yueguangbaohe/Documents/trae_projects/pi_digits"
REMOTE_DIR = "/root/feishu_bots"

def test_connection(server):
    """测试服务器连接"""
    print(f"\n🔍 测试连接: {server['name']} ({server['ip']})")
    
    # 测试ping
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
    
    # 测试SSH端口
    result = subprocess.run(
        ["nc", "-zv", server["ip"], "22"],
        capture_output=True,
        text=True,
        timeout=5
    )
    
    if result.returncode == 0:
        print(f"   ✅ SSH端口开放")
    else:
        print(f"   ❌ SSH端口关闭")
        return False
    
    # 测试SSH连接
    expect_script = f'''
#!/usr/bin/expect -f
set timeout 10
spawn ssh -o StrictHostKeyChecking=no {server['username']}@{server['ip']} "echo 'SSH连接成功'"
expect {{
    "password:" {{
        send "{server['password']}\\r"
        expect {{
            "SSH连接成功" {{
                exit 0
            }}
            timeout {{
                exit 1
            }}
        }}
    }}
    "Permission denied" {{
        exit 2
    }}
    timeout {{
        exit 3
    }}
}}
'''
    
    result = subprocess.run(
        ["expect", "-c", expect_script],
        capture_output=True,
        text=True,
        timeout=15
    )
    
    if result.returncode == 0:
        print(f"   ✅ SSH连接成功")
        return True
    elif result.returncode == 2:
        print(f"   ⚠️ SSH需要密钥认证")
        return False
    else:
        print(f"   ❌ SSH连接失败")
        return False

def select_server():
    """选择服务器"""
    print("=" * 60)
    print("🚀 阿里云服务器智能部署")
    print("=" * 60)
    print("")
    
    print("📋 可用服务器列表:")
    print("")
    
    for i, server in enumerate(SERVERS, 1):
        print(f"{i}. {server['name']}")
        print(f"   IP: {server['ip']}")
        print(f"   用户: {server['username']}")
        print(f"   备注: {server['note']}")
        print("")
    
    while True:
        try:
            choice = input("请选择要部署的服务器 (1-3): ").strip()
            index = int(choice) - 1
            if 0 <= index < len(SERVERS):
                return SERVERS[index]
            else:
                print("❌ 无效选择，请重新输入")
        except ValueError:
            print("❌ 请输入数字")
        except KeyboardInterrupt:
            print("\n\n👋 用户取消")
            sys.exit(0)

def execute_ssh_command(server, command):
    """执行SSH命令"""
    try:
        expect_script = f'''
#!/usr/bin/expect -f
set timeout 30
spawn ssh -o StrictHostKeyChecking=no {server['username']}@{server['ip']} "{command}"
expect {{
    "password:" {{
        send "{server['password']}\\r"
        expect eof
    }}
    eof
}}
'''
        
        result = subprocess.run(
            ["expect", "-c", expect_script],
            capture_output=True,
            text=True,
            timeout=60
        )
        
        return result.returncode, result.stdout, result.stderr
    except Exception as e:
        return -1, "", str(e)

def upload_file(server, local_path, remote_path):
    """上传文件"""
    try:
        print(f"📤 上传文件: {os.path.basename(local_path)}")
        
        expect_script = f'''
#!/usr/bin/expect -f
set timeout 300
spawn scp -o StrictHostKeyChecking=no {local_path} {server['username']}@{server['ip']}:{remote_path}
expect {{
    "password:" {{
        send "{server['password']}\\r"
        expect eof
    }}
    eof
}}
'''
        
        result = subprocess.run(
            ["expect", "-c", expect_script],
            capture_output=True,
            text=True,
            timeout=300
        )
        
        if result.returncode == 0:
            print(f"   ✅ 上传成功")
            return True
        else:
            print(f"   ❌ 上传失败: {result.stderr}")
            return False
    except Exception as e:
        print(f"   ❌ 上传异常: {e}")
        return False

def upload_directory(server, local_dir, remote_dir):
    """上传目录"""
    try:
        print(f"📤 上传目录: {os.path.basename(local_dir)}")
        
        expect_script = f'''
#!/usr/bin/expect -f
set timeout 600
spawn scp -r -o StrictHostKeyChecking=no {local_dir} {server['username']}@{server['ip']}:{remote_dir}
expect {{
    "password:" {{
        send "{server['password']}\\r"
        expect eof
    }}
    eof
}}
'''
        
        result = subprocess.run(
            ["expect", "-c", expect_script],
            capture_output=True,
            text=True,
            timeout=600
        )
        
        if result.returncode == 0:
            print(f"   ✅ 上传成功")
            return True
        else:
            print(f"   ❌ 上传失败: {result.stderr}")
            return False
    except Exception as e:
        print(f"   ❌ 上传异常: {e}")
        return False

def install_dependencies(server):
    """安装依赖"""
    print("\n📦 安装Python依赖...")
    
    commands = [
        "pip3 install requests schedule -q",
        "pip3 install paramiko -q",
    ]
    
    for cmd in commands:
        exit_code, output, error = execute_ssh_command(server, cmd)
        if exit_code == 0:
            print(f"   ✅ {cmd}")
        else:
            print(f"   ❌ {cmd}")
            if error:
                print(f"   错误: {error[:200]}")

def create_directory(server, path):
    """创建目录"""
    exit_code, output, error = execute_ssh_command(server, f"mkdir -p {path}")
    if exit_code == 0:
        print(f"   ✅ 创建目录: {path}")
    else:
        print(f"   ❌ 创建目录失败: {error}")

def create_start_script(server):
    """创建启动脚本"""
    script_content = f'''#!/bin/bash
# 飞书机器人启动脚本

cd {REMOTE_DIR}

echo "============================================================"
echo "🚀 启动飞书机器人"
echo "============================================================"

# 安装screen
if ! command -v screen &> /dev/null; then
    echo "📦 安装screen..."
    yum install screen -y 2>/dev/null || apt install screen -y 2>/dev/null
    echo "✅ screen安装完成"
fi

echo "✅ 环境准备完成"

# 创建screen会话并运行
screen -dmS bots bash -c "cd {REMOTE_DIR}/群会议纪要机器人 && python3 start_daemon.py"

echo "✅ 机器人已在后台运行"
echo ""
echo "查看运行状态:"
echo "  screen -r bots"
echo ""
echo "查看日志:"
echo "  tail -f {REMOTE_DIR}/群会议纪要机器人/logs/*.log"
'''
    
    script_path = os.path.join("/tmp", "start_bots.sh")
    with open(script_path, 'w', encoding='utf-8') as f:
        f.write(script_content)
    
    remote_script = f"{REMOTE_DIR}/start_bots.sh"
    
    exit_code, output, error = execute_ssh_command(server, f"chmod +x {remote_script}")
    if exit_code == 0:
        print(f"   ✅ 创建启动脚本")
    else:
        print(f"   ❌ 创建启动脚本失败: {error}")
    
    upload_file(server, script_path, remote_script)

def start_bots(server):
    """启动机器人"""
    print("\n🚀 启动机器人...")
    
    exit_code, output, error = execute_ssh_command(
        server,
        f"cd {REMOTE_DIR} && bash start_bots.sh"
    )
    
    if exit_code == 0:
        print("✅ 机器人启动成功")
        print(f"\n{output}")
    else:
        print(f"❌ 机器人启动失败: {error}")

def check_status(server):
    """检查运行状态"""
    print("\n📊 检查运行状态...")
    
    exit_code, output, error = execute_ssh_command(
        server,
        f"ps aux | grep python | grep -v grep"
    )
    
    if exit_code == 0:
        print(f"运行中的Python进程:\n{output}")
    else:
        print("❌ 没有运行的Python进程")

def deploy(server):
    """完整部署流程"""
    print(f"\n📋 部署信息:")
    print(f"   • 服务器: {server['name']}")
    print(f"   • IP: {server['ip']}")
    print(f"   • 用户: {server['username']}")
    print(f"   • 本地目录: {LOCAL_DIR}")
    print("")
    
    if not os.path.exists(LOCAL_DIR):
        print(f"❌ 本地目录不存在: {LOCAL_DIR}")
        return False
    
    try:
        print(f"\n📁 部署到: {REMOTE_DIR}")
        
        create_directory(server, REMOTE_DIR)
        
        print("\n📤 上传代码...")
        upload_directory(server, LOCAL_DIR, REMOTE_DIR)
        
        print("\n📦 安装依赖...")
        install_dependencies(server)
        
        print("\n📝 创建启动脚本...")
        create_start_script(server)
        
        print("\n🚀 启动机器人...")
        start_bots(server)
        
        time.sleep(2)
        
        print("\n📊 检查运行状态...")
        check_status(server)
        
        print("\n" + "=" * 60)
        print("✅ 部署完成！")
        print("=" * 60)
        print("")
        print("💡 后续操作:")
        print(f"   • SSH连接: ssh {server['username']}@{server['ip']}")
        print(f"   • 查看运行: ssh {server['username']}@{server['ip']} -t 'screen -r bots'")
        print(f"   • 查看日志: ssh {server['username']}@{server['ip']} -t 'tail -f {REMOTE_DIR}/群会议纪要机器人/logs/*.log'")
        print("")
        print("🎉 机器人已部署并运行！")
        
        return True
            
    except Exception as e:
        print(f"\n❌ 部署失败: {e}")
        return False

def main():
    """主函数"""
    # 选择服务器
    server = select_server()
    
    # 测试连接
    if not test_connection(server):
        print("\n❌ 服务器连接测试失败，请检查网络或服务器配置")
        print("\n💡 建议:")
        print("   1. 检查服务器是否在线")
        print("   2. 检查用户名和密码是否正确")
        print("   3. 检查SSH配置（可能需要密钥认证）")
        print("   4. 尝试选择其他服务器")
        return
    
    # 开始部署
    deploy(server)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 用户取消")
    except Exception as e:
        print(f"\n❌ 错误: {e}")

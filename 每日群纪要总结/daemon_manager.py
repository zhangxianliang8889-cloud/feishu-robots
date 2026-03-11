#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
守护进程管理器 - 自动重启 + 断网重连 + 健康检查
让机器人可以无人值守运行，安心睡觉
"""

import os
import sys
import time
import signal
import subprocess
import json
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

class DaemonManager:
    """守护进程管理器"""
    
    def __init__(
        self,
        script_path: str,
        name: str = "Bot",
        max_restarts: int = 10,
        restart_interval: int = 60,
        health_check_interval: int = 300,
        network_check_interval: int = 60
    ):
        """
        初始化守护进程管理器
        
        Args:
            script_path: 要运行的脚本路径
            name: 进程名称
            max_restarts: 最大重启次数
            restart_interval: 重启间隔（秒）
            health_check_interval: 健康检查间隔（秒）
            network_check_interval: 网络检查间隔（秒）
        """
        self.script_path = script_path
        self.name = name
        self.max_restarts = max_restarts
        self.restart_interval = restart_interval
        self.health_check_interval = health_check_interval
        self.network_check_interval = network_check_interval
        
        self.process: Optional[subprocess.Popen] = None
        self.restart_count = 0
        self.last_restart_time: Optional[datetime] = None
        self.start_time: Optional[datetime] = None
        self.running = True
        self.last_health_check: Optional[datetime] = None
        self.network_ok = True
        
        self.status_file = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            f"daemon_status_{name}.json"
        )
        
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """信号处理器"""
        print(f"\n🛑 收到停止信号，正在停止 {self.name}...")
        self.running = False
        if self.process:
            self.process.terminate()
            try:
                self.process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self.process.kill()
        self._save_status("stopped")
        sys.exit(0)
    
    def _check_network(self) -> bool:
        """
        检查网络连接
        
        Returns:
            bool: 网络是否正常
        """
        try:
            import socket
            socket.create_connection(("open.feishu.cn", 443), timeout=5)
            return True
        except:
            return False
    
    def _wait_for_network(self) -> bool:
        """
        等待网络恢复
        
        Returns:
            bool: 是否恢复
        """
        print(f"⚠️ [{self.name}] 网络断开，等待恢复...")
        wait_count = 0
        max_wait = 60
        
        while wait_count < max_wait and self.running:
            if self._check_network():
                print(f"✅ [{self.name}] 网络已恢复")
                self.network_ok = True
                return True
            
            time.sleep(self.network_check_interval)
            wait_count += 1
            print(f"⏳ [{self.name}] 等待网络恢复中... ({wait_count}/{max_wait})")
        
        return False
    
    def _should_restart(self) -> bool:
        """
        检查是否应该重启
        
        Returns:
            bool: 是否应该重启
        """
        if self.restart_count >= self.max_restarts:
            print(f"❌ [{self.name}] 达到最大重启次数 {self.max_restarts}，停止重启")
            return False
        
        if self.last_restart_time:
            elapsed = (datetime.now() - self.last_restart_time).total_seconds()
            if elapsed < self.restart_interval:
                wait_time = self.restart_interval - elapsed
                print(f"⏳ [{self.name}] 等待 {wait_time:.0f} 秒后重启...")
                time.sleep(wait_time)
        
        return True
    
    def _start_process(self) -> bool:
        """
        启动进程
        
        Returns:
            bool: 是否成功启动
        """
        try:
            print(f"🚀 [{self.name}] 启动进程: {self.script_path}")
            
            self.process = subprocess.Popen(
                [sys.executable, self.script_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                cwd=os.path.dirname(self.script_path)
            )
            
            self.start_time = datetime.now()
            self.last_restart_time = datetime.now()
            self.restart_count += 1
            
            self._save_status("running")
            
            print(f"✅ [{self.name}] 进程已启动 (PID: {self.process.pid})")
            return True
            
        except Exception as e:
            print(f"❌ [{self.name}] 启动失败: {e}")
            return False
    
    def _check_process_health(self) -> bool:
        """
        检查进程健康状态
        
        Returns:
            bool: 进程是否健康
        """
        if not self.process:
            return False
        
        return_code = self.process.poll()
        if return_code is not None:
            return False
        
        if self.start_time:
            elapsed = (datetime.now() - self.start_time).total_seconds()
            if elapsed < 60:
                return True
        
        return True
    
    def _save_status(self, status: str, error: str = None):
        """
        保存状态
        
        Args:
            status: 状态
            error: 错误信息
        """
        try:
            status_data = {
                "name": self.name,
                "status": status,
                "pid": self.process.pid if self.process else None,
                "start_time": self.start_time.strftime('%Y-%m-%d %H:%M:%S') if self.start_time else None,
                "last_restart": self.last_restart_time.strftime('%Y-%m-%d %H:%M:%S') if self.last_restart_time else None,
                "restart_count": self.restart_count,
                "update_time": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                "error": error
            }
            
            with open(self.status_file, 'w', encoding='utf-8') as f:
                json.dump(status_data, f, ensure_ascii=False, indent=2)
        except:
            pass
    
    def _read_process_output(self):
        """读取进程输出"""
        if not self.process:
            return
        
        try:
            while True:
                line = self.process.stdout.readline()
                if not line:
                    break
                print(line.rstrip())
        except:
            pass
    
    def run(self):
        """运行守护进程"""
        print("=" * 60)
        print(f"🛡️ {self.name} 守护进程管理器启动")
        print("=" * 60)
        print(f"📋 配置:")
        print(f"   - 脚本路径: {self.script_path}")
        print(f"   - 最大重启次数: {self.max_restarts}")
        print(f"   - 重启间隔: {self.restart_interval}秒")
        print(f"   - 健康检查间隔: {self.health_check_interval}秒")
        print(f"   - 网络检查间隔: {self.network_check_interval}秒")
        print("=" * 60)
        print("")
        
        last_network_check = datetime.now()
        last_health_check = datetime.now()
        
        while self.running:
            if not self._check_network():
                self.network_ok = False
                if not self._wait_for_network():
                    print(f"❌ [{self.name}] 网络长时间未恢复，等待...")
                    time.sleep(60)
                    continue
            
            if not self._check_process_health():
                print(f"⚠️ [{self.name}] 进程异常退出")
                
                if self.process:
                    return_code = self.process.poll()
                    print(f"   退出码: {return_code}")
                    
                    try:
                        stderr = self.process.stderr.read()
                        if stderr:
                            print(f"   错误输出: {stderr[:500]}")
                    except:
                        pass
                
                self._save_status("crashed")
                
                if self._should_restart():
                    if self._start_process():
                        self.restart_count = 0
                else:
                    break
            
            now = datetime.now()
            
            if (now - last_health_check).total_seconds() >= self.health_check_interval:
                if self._check_process_health():
                    print(f"💚 [{self.name}] 健康检查通过 (运行时间: {(now - self.start_time).total_seconds():.0f}秒)")
                last_health_check = now
            
            if (now - last_network_check).total_seconds() >= self.network_check_interval:
                if self._check_network():
                    self.network_ok = True
                else:
                    self.network_ok = False
                    print(f"⚠️ [{self.name}] 网络连接异常")
                last_network_check = now
            
            time.sleep(10)
        
        print(f"\n🛑 [{self.name}] 守护进程已停止")
        self._save_status("stopped")


class MultiBotDaemon:
    """多机器人守护进程管理器"""
    
    def __init__(self):
        """初始化多机器人守护进程管理器"""
        self.daemons: Dict[str, DaemonManager] = {}
        self.running = True
        
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """信号处理器"""
        print(f"\n🛑 收到停止信号，正在停止所有机器人...")
        self.running = False
        for name, daemon in self.daemons.items():
            daemon.running = False
            if daemon.process:
                daemon.process.terminate()
        sys.exit(0)
    
    def add_bot(
        self,
        name: str,
        script_path: str,
        max_restarts: int = 10,
        restart_interval: int = 60
    ):
        """
        添加机器人
        
        Args:
            name: 机器人名称
            script_path: 脚本路径
            max_restarts: 最大重启次数
            restart_interval: 重启间隔
        """
        daemon = DaemonManager(
            script_path=script_path,
            name=name,
            max_restarts=max_restarts,
            restart_interval=restart_interval
        )
        self.daemons[name] = daemon
        print(f"✅ 已添加机器人: {name}")
    
    def run(self):
        """运行所有机器人守护进程"""
        print("=" * 60)
        print("🛡️ 多机器人守护进程管理器启动")
        print("=" * 60)
        print(f"📋 已添加 {len(self.daemons)} 个机器人:")
        for name, daemon in self.daemons.items():
            print(f"   - {name}: {daemon.script_path}")
        print("=" * 60)
        print("")
        
        import threading
        
        threads = []
        for name, daemon in self.daemons.items():
            thread = threading.Thread(target=daemon.run, name=name)
            thread.daemon = True
            thread.start()
            threads.append(thread)
        
        while self.running:
            time.sleep(10)
            
            all_stopped = all(not daemon.running for daemon in self.daemons.values())
            if all_stopped:
                print("⚠️ 所有机器人已停止")
                break
        
        print("\n🛑 多机器人守护进程已停止")


def create_launch_script():
    """创建启动脚本"""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    
    meeting_script = os.path.join(base_dir, "群会议纪要_最终版.py")
    stats_script = os.path.join(base_dir, "..", "飞书统计群成员消息数", "多群统计.py")
    
    launch_script = os.path.join(base_dir, "start_daemon.py")
    
    content = f'''#!/usr/bin/env python3
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
        script_path="{meeting_script}",
        max_restarts=10,
        restart_interval=60
    )
    
    daemon.add_bot(
        name="群消息统计机器人",
        script_path="{stats_script}",
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
'''
    
    with open(launch_script, 'w', encoding='utf-8') as f:
        f.write(content)
    
    os.chmod(launch_script, 0o755)
    
    return launch_script


if __name__ == "__main__":
    print("🧪 测试守护进程管理器")
    print("=" * 60)
    
    print("\n1. 创建启动脚本")
    launch_script = create_launch_script()
    print(f"   ✅ 已创建: {launch_script}")
    
    print("\n2. 使用方法")
    print("   方法1 - 单独运行一个机器人:")
    print("     python3 daemon_manager.py")
    print("")
    print("   方法2 - 同时运行两个机器人:")
    print("     python3 start_daemon.py")
    print("")
    print("   方法3 - 后台运行（推荐）:")
    print("     nohup python3 start_daemon.py > daemon.log 2>&1 &")
    print("")
    print("   方法4 - 使用screen（推荐）:")
    print("     screen -S bots")
    print("     python3 start_daemon.py")
    print("     按 Ctrl+A+D 分离会话")
    
    print("\n✅ 测试完成")

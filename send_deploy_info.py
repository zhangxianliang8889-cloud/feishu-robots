#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
发送部署说明到飞书群
"""

import requests
import json

MEETING_APP_ID = "cli_a9233dfe18389bde"
MEETING_APP_SECRET = "8gvZm8C04sS0GJXtDQdkkeAOJV6gCr4w"

def get_token():
    """获取访问令牌"""
    url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
    data = {
        "app_id": MEETING_APP_ID,
        "app_secret": MEETING_APP_SECRET
    }
    resp = requests.post(url, json=data, proxies={}).json()
    return resp.get("tenant_access_token")

def send_text_message(token, chat_id, text):
    """发送文本消息"""
    url = "https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type=chat_id"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    data = {
        "receive_id": chat_id,
        "msg_type": "text",
        "content": json.dumps({"text": text})
    }
    
    resp = requests.post(url, headers=headers, json=data, proxies={})
    return resp.json()

def get_test_group_id(token):
    """获取测试群ID"""
    url = "https://open.feishu.cn/open-apis/im/v1/chats?page_size=50"
    headers = {"Authorization": f"Bearer {token}"}
    
    resp = requests.get(url, headers=headers, proxies={}).json()
    
    if resp.get("code") == 0:
        for chat in resp.get("data", {}).get("items", []):
            if "张贤良测试群" in chat.get("name", ""):
                return chat.get("chat_id")
    
    return None

if __name__ == "__main__":
    print("📤 发送部署说明到飞书测试群")
    print("=" * 60)
    
    print("1. 获取访问令牌...")
    token = get_token()
    if not token:
        print("❌ 获取令牌失败")
        exit(1)
    print("   ✅ 成功")
    
    print("\n2. 获取测试群ID...")
    chat_id = get_test_group_id(token)
    if not chat_id:
        print("❌ 未找到测试群")
        exit(1)
    print(f"   ✅ 测试群ID: {chat_id}")
    
    print("\n3. 发送部署说明...")
    
    message = """🚀 飞书机器人部署包已准备好

📦 部署包位置：
/Users/yueguangbaohe/Documents/trae_projects/pi_digits/飞书机器人部署包.zip

📋 部署步骤：

1️⃣ 解压部署包
unzip 飞书机器人部署包.zip

2️⃣ 安装依赖
pip3 install requests schedule

3️⃣ 运行启动脚本
cd 飞书机器人部署包
./start.sh

或使用守护进程：
cd 群会议纪要机器人
python3 start_daemon.py

⏰ 定时发送时间：

群会议纪要机器人：
• 日报：每天 21:00
• 周报：每周一 09:00
• 月报：每月最后一天 09:30

群消息统计机器人：
• 日报：每天 09:00
• 周报：每周一 09:00
• 月报：每月1号 09:00

💡 推荐使用screen后台运行：
screen -S bots
python3 start_daemon.py
按 Ctrl+A+D 分离会话

📁 文件说明：
• 群会议纪要机器人/ - 主程序目录
• 群消息统计机器人/ - 主程序目录
• 部署说明.md - 详细部署文档
• start.sh - 快速启动脚本

⚠️ 注意事项：
1. 确保服务器能访问飞书API
2. 配置文件中的APP_ID和APP_SECRET已设置
3. 建议使用守护进程管理器自动重启"""
    
    result = send_text_message(token, chat_id, message)
    if result.get("code") == 0:
        print("   ✅ 发送成功")
    else:
        print(f"   ❌ 发送失败: {result}")
    
    print("\n" + "=" * 60)
    print("✅ 完成！请到飞书测试群查看")
    print("\n💡 部署包位置：")
    print("   /Users/yueguangbaohe/Documents/trae_projects/pi_digits/飞书机器人部署包.zip")

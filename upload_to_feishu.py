#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
上传部署包到飞书群
"""

import requests
import os

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

def upload_file(token, file_path):
    """上传文件"""
    url = "https://open.feishu.cn/open-apis/drive/v1/medias/upload_all"
    
    headers = {"Authorization": f"Bearer {token}"}
    
    file_name = os.path.basename(file_path)
    file_size = os.path.getsize(file_path)
    
    form_data = {
        "file_name": (None, file_name),
        "parent_type": (None, "ccm_import_open"),
        "parent_node": (None, ""),
        "size": (None, str(file_size)),
    }
    
    with open(file_path, 'rb') as f:
        files = {
            "file": (file_name, f, "application/zip")
        }
        resp = requests.post(url, headers=headers, data=form_data, files=files, proxies={})
    
    return resp.json()

def send_file_message(token, chat_id, file_key):
    """发送文件消息"""
    url = "https://open.feishu.cn/open-apis/im/v1/messages"
    headers = {"Authorization": f"Bearer {token}"}
    
    data = {
        "receive_id": chat_id,
        "msg_type": "file",
        "content": f'{{"file_key": "{file_key}"}}'
    }
    
    resp = requests.post(url, headers=headers, json=data, proxies={})
    return resp.json()

def send_text_message(token, chat_id, text):
    """发送文本消息"""
    url = "https://open.feishu.cn/open-apis/im/v1/messages"
    headers = {"Authorization": f"Bearer {token}"}
    
    data = {
        "receive_id": chat_id,
        "msg_type": "text",
        "content": f'{{"text": "{text}"}}'
    }
    
    resp = requests.post(url, headers=headers, json=data, proxies={})
    return resp.json()

def get_test_group_id(token):
    """获取测试群ID"""
    url = "https://open.feishu.cn/open-apis/im/v1/chats"
    headers = {"Authorization": f"Bearer {token}"}
    params = {"page_size": 50}
    
    resp = requests.get(url, headers=headers, params=params, proxies={}).json()
    
    if resp.get("code") == 0:
        for chat in resp.get("data", {}).get("items", []):
            if "张贤良测试群" in chat.get("name", ""):
                return chat.get("chat_id")
    
    return None

if __name__ == "__main__":
    print("📤 上传部署包到飞书测试群")
    print("=" * 60)
    
    file_path = "/Users/yueguangbaohe/Documents/trae_projects/pi_digits/飞书机器人部署包.zip"
    
    if not os.path.exists(file_path):
        print(f"❌ 文件不存在: {file_path}")
        exit(1)
    
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
    
    print("\n3. 上传文件...")
    upload_result = upload_file(token, file_path)
    if upload_result.get("code") != 0:
        print(f"❌ 上传失败: {upload_result}")
        exit(1)
    
    file_key = upload_result.get("data", {}).get("file_key")
    if not file_key:
        print(f"❌ 未获取到file_key: {upload_result}")
        exit(1)
    print(f"   ✅ 上传成功，file_key: {file_key}")
    
    print("\n4. 发送说明消息...")
    message = """🚀 飞书机器人部署包

📦 包含内容：
• 群会议纪要机器人
• 群消息统计机器人
• 部署说明文档
• 快速启动脚本

📋 部署步骤：
1. 解压部署包
2. 安装依赖：pip3 install requests schedule
3. 运行启动脚本：./start.sh 或 python3 start_daemon.py

⏰ 发送时间：
• 群会议纪要：日报21:00，周报周一09:00，月报月底09:30
• 群消息统计：日报09:00，周报周一09:00，月报1号09:00

💡 详细说明请查看 部署说明.md"""
    
    send_result = send_text_message(token, chat_id, message)
    if send_result.get("code") == 0:
        print("   ✅ 说明消息发送成功")
    else:
        print(f"   ⚠️ 发送失败: {send_result}")
    
    print("\n5. 发送文件...")
    file_result = send_file_message(token, chat_id, file_key)
    if file_result.get("code") == 0:
        print("   ✅ 文件发送成功")
    else:
        print(f"   ⚠️ 发送失败: {file_result}")
    
    print("\n" + "=" * 60)
    print("✅ 完成！请到飞书测试群查看")

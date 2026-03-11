#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试脚本：发送群会议纪要到张贤良测试群
"""

import requests
import json
import time
from datetime import datetime, timedelta
import sys
import os

# 添加当前目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from config import *
except ImportError:
    DAILY_TIME = "21:00"
    WEEKLY_TIME = "09:00"
    MONTHLY_TIME = "09:30"
    SEND_MODE = "all"
    WHITELIST_GROUPS = []
    BLACKLIST_GROUPS = []
    SKIP_EMPTY_GROUPS = True
    MIN_MESSAGE_COUNT = 3
    SKIP_SYSTEM_ONLY = True
    REPORT_FORMAT = "simple"
    SHOW_GENERATE_TIME = True
    SHOW_BOT_SIGNATURE = True
    DEBUG_MODE = False
    DEBUG_GROUP = "张贤良测试群"
    TEST_MODE = False
    TEST_GROUP = "张贤良测试群"
    FEISHU_APP_ID = "cli_a9233dfe18389bde"
    FEISHU_APP_SECRET = "8gvZm8C04sS0GJXtDQdkkeAOJV6gCr4w"

try:
    from ai_summarizer import ai_summarize_messages, ai_generate_inspiration, ai_categorize_and_summarize
    AI_SUMMARIZER_AVAILABLE = True
except ImportError:
    AI_SUMMARIZER_AVAILABLE = False

BOT_NAME = "群会议纪要"

# 飞书API相关
APP_ID = FEISHU_APP_ID
APP_SECRET = FEISHU_APP_SECRET

class FeishuBot:
    def __init__(self):
        self.app_id = APP_ID
        self.app_secret = APP_SECRET
        self.access_token = None
        self.token_expire_time = 0
    
    def get_access_token(self):
        """获取飞书访问令牌"""
        current_time = int(time.time())
        if self.access_token and current_time < self.token_expire_time:
            return self.access_token
        
        url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal/"
        headers = {
            "Content-Type": "application/json"
        }
        data = {
            "app_id": self.app_id,
            "app_secret": self.app_secret
        }
        
        try:
            response = requests.post(url, headers=headers, json=data, timeout=10)
            result = response.json()
            if result.get("code") == 0:
                self.access_token = result.get("tenant_access_token")
                self.token_expire_time = current_time + result.get("expire", 3600)
                return self.access_token
            else:
                print(f"获取access_token失败: {result.get('msg')}")
                return None
        except Exception as e:
            print(f"获取access_token异常: {e}")
            return None
    
    def get_groups(self):
        """获取机器人所在的群列表"""
        token = self.get_access_token()
        if not token:
            return []
        
        url = "https://open.feishu.cn/open-apis/im/v1/chats"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        data = {
            "page_size": 100,
            "page_token": ""
        }
        
        groups = []
        try:
            response = requests.get(url, headers=headers, params=data, timeout=10)
            result = response.json()
            if result.get("code") == 0:
                groups = result.get("data", {}).get("items", [])
        except Exception as e:
            print(f"获取群列表异常: {e}")
        
        return groups
    
    def get_group_messages(self, group_id, start_time, end_time):
        """获取群消息"""
        token = self.get_access_token()
        if not token:
            return []
        
        url = f"https://open.feishu.cn/open-apis/im/v1/messages"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        data = {
            "chat_id": group_id,
            "start_time": start_time,
            "end_time": end_time,
            "page_size": 100,
            "page_token": ""
        }
        
        messages = []
        try:
            response = requests.get(url, headers=headers, params=data, timeout=10)
            result = response.json()
            if result.get("code") == 0:
                messages = result.get("data", {}).get("items", [])
        except Exception as e:
            print(f"获取群消息异常: {e}")
        
        return messages
    
    def send_message(self, group_id, content):
        """发送消息到群"""
        token = self.get_access_token()
        if not token:
            return False
        
        url = "https://open.feishu.cn/open-apis/im/v1/messages"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        data = {
            "receive_id_type": "chat_id",
            "receive_id": group_id,
            "content": json.dumps({"text": content}),
            "msg_type": "text"
        }
        
        try:
            response = requests.post(url, headers=headers, json=data, timeout=10)
            result = response.json()
            if result.get("code") == 0:
                return True
            else:
                print(f"发送消息失败: {result.get('msg')}")
                return False
        except Exception as e:
            print(f"发送消息异常: {e}")
            return False

def generate_meeting_summary(group_name, group_id, bot):
    """生成会议纪要"""
    print(f"\n📊 正在处理群：{group_name}")
    
    # 获取过去24小时的消息
    end_time = int(time.time())
    start_time = end_time - 24 * 3600
    
    messages = bot.get_group_messages(group_id, start_time, end_time)
    print(f"✅ 获取到 {len(messages)} 条消息")
    
    # 提取文本消息
    text_messages = []
    for msg in messages:
        if msg.get("msg_type") == "text":
            content = json.loads(msg.get("content", "{}"))
            text = content.get("text", "")
            if text:
                text_messages.append(text)
    
    print(f"✅ 提取到 {len(text_messages)} 条文本消息")
    
    if len(text_messages) < MIN_MESSAGE_COUNT:
        print(f"⏭️  消息数量({len(text_messages)})少于阈值({MIN_MESSAGE_COUNT})，跳过")
        return None
    
    # 使用AI生成总结
    if AI_SUMMARIZER_AVAILABLE:
        print("✅ 使用AI生成总结...")
        ai_result = ai_summarize_messages(text_messages, summary_type="daily")
        
        if ai_result.get("success"):
            summary = ai_result.get("summary")
            # 生成AI建议或金句
            inspiration = ai_generate_inspiration(summary)
            
            # 构建消息内容
            today = datetime.now().strftime("%Y-%m-%d")
            message = f"📊 {group_name} - 群会议纪要日报 ({today})\n\n"
            message += "════════════════════\n"
            message += f"📈 今日数据：{len(messages)} 条消息\n"
            message += "════════════════════\n\n"
            message += summary + "\n\n"
            message += f"{inspiration}\n\n"
            message += "💡 AI助手每天为大家总结群聊精华，每天进步一点点，实现复利的力量！\n"
            message += "🌟 鼓励大家多交流、多分享，让智慧在碰撞中涌现！\n\n"
            message += f"⏰ 生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            message += f"🤖 由{BOT_NAME}机器人自动生成\n"
            
            return message
        else:
            print("❌ AI总结失败")
            return None
    else:
        print("❌ AI总结模块不可用")
        return None

def main():
    """主函数"""
    print("🚀 测试群会议纪要发送到张贤良测试群")
    
    bot = FeishuBot()
    
    # 获取群列表
    groups = bot.get_groups()
    print(f"📋 找到 {len(groups)} 个群")
    
    # 找到张贤良测试群
    test_group = None
    for group in groups:
        if group.get("name") == "张贤良测试群":
            test_group = group
            break
    
    if not test_group:
        print("❌ 未找到张贤良测试群")
        return
    
    print(f"✅ 找到张贤良测试群: {test_group.get('name')} (ID: {test_group.get('chat_id')})")
    
    # 生成会议纪要
    summary = generate_meeting_summary(test_group.get('name'), test_group.get('chat_id'), bot)
    
    if summary:
        print("\n📝 生成的会议纪要：")
        print(summary)
        
        # 发送到测试群
        print("\n📤 发送到张贤良测试群...")
        success = bot.send_message(test_group.get('chat_id'), summary)
        if success:
            print("✅ 发送成功！")
        else:
            print("❌ 发送失败！")
    else:
        print("❌ 无法生成会议纪要")

if __name__ == "__main__":
    main()

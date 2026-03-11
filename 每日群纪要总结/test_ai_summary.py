#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试脚本：使用示例消息测试AI总结功能并发送到张贤良测试群
"""

import requests
import json
import time
from datetime import datetime
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
        # 确保content是字符串
        if not isinstance(content, str):
            content = str(content)
        # 处理可能的JSON编码问题
        content = content.encode('utf-8').decode('utf-8')
        
        # 使用params参数传递receive_id_type
        params = {
            "receive_id_type": "chat_id"
        }
        
        # 构建消息数据
        data = {
            "receive_id": group_id,
            "msg_type": "text",
            "content": json.dumps({"text": content}, ensure_ascii=False)
        }
        
        try:
            # 打印调试信息
            print(f"发送消息参数: {params}")
            print(f"发送消息数据: {json.dumps(data, ensure_ascii=False)}")
            
            # 使用与主程序相同的方式
            response = requests.post(url, headers=headers, params=params, json=data, timeout=10)
            result = response.json()
            if result.get("code") == 0:
                return True
            else:
                print(f"发送消息失败: {result.get('msg')}")
                print(f"详细信息: {result}")
                return False
        except Exception as e:
            print(f"发送消息异常: {e}")
            return False

def generate_meeting_summary_with_sample(group_name, bot):
    """使用示例消息生成会议纪要"""
    print(f"\n📊 正在生成示例会议纪要：{group_name}")
    
    # 示例消息 - 模拟真实群聊
    sample_messages = [
        "今天我们讨论了项目的进度，前端开发已经完成了80%，后端API也基本就绪",
        "设计部门提出了新的UI方案，大家都觉得很不错，需要进一步细化",
        "下周我们需要进行一次用户测试，看看产品的实际使用效果",
        "市场部已经开始准备推广材料，预计下月初开始宣传",
        "技术团队需要在月底前完成所有功能开发，确保能按时上线",
        "大家对新的功能模块都很期待，希望能给用户带来更好的体验",
        "运营部门提出了一些优化建议，我们需要在后续版本中考虑",
        "测试团队已经开始编写测试用例，确保产品质量",
        "财务部门提醒我们要控制项目成本，避免超出预算",
        "HR部门表示会为项目团队提供必要的支持和资源"
    ]
    
    print(f"✅ 使用 {len(sample_messages)} 条示例消息")
    
    # 使用AI生成总结
    if AI_SUMMARIZER_AVAILABLE:
        print("✅ 使用AI生成总结...")
        ai_result = ai_summarize_messages(sample_messages, summary_type="daily")
        
        if ai_result.get("success"):
            summary = ai_result.get("summary")
            # 生成AI建议或金句
            inspiration = ai_generate_inspiration(summary)
            
            # 构建消息内容
            today = datetime.now().strftime("%Y-%m-%d")
            message = f"📊 {group_name} - 群会议纪要日报 ({today})\n\n"
            message += "════════════════════\n"
            message += f"📈 今日数据：{len(sample_messages)} 条消息\n"
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
    print("🚀 测试AI总结功能并发送到张贤良测试群")
    
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
    
    # 使用示例消息生成会议纪要
    summary = generate_meeting_summary_with_sample(test_group.get('name'), bot)
    
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

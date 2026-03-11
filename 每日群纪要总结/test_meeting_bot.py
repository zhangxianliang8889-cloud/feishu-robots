#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试群会议纪要机器人的日报、周报、月报功能
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
        params = {
            "chat_id": group_id,
            "start_time": start_time,
            "end_time": end_time,
            "page_size": 100,
            "page_token": ""
        }
        
        messages = []
        try:
            response = requests.get(url, headers=headers, params=params, timeout=10)
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
        
        params = {
            "receive_id_type": "chat_id"
        }
        
        data = {
            "receive_id": group_id,
            "msg_type": "text",
            "content": json.dumps({"text": content}, ensure_ascii=False)
        }
        
        try:
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

def generate_meeting_summary(group_name, group_id, bot, summary_type="daily"):
    """生成会议纪要"""
    print(f"\n📊 正在生成{summary_type}纪要：{group_name}")
    
    # 根据类型设置时间范围
    if summary_type == "daily":
        date_str = datetime.now().strftime("%Y-%m-%d")
    elif summary_type == "weekly":
        start_date = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
        end_date = datetime.now().strftime("%Y-%m-%d")
        date_str = f"{start_date} ~ {end_date}"
    else:  # monthly
        date_str = datetime.now().strftime("%Y-%m")
    
    # 使用示例消息
    sample_messages = [
        "今天我们讨论了新项目的启动计划，需要在下周一前完成所有准备工作",
        "产品部提出了新的功能需求，技术部需要评估可行性",
        "市场部已经准备好了推广方案，等待审批",
        "设计部的新UI设计已经完成，大家可以查看一下",
        "测试部发现了几个bug，需要开发部尽快修复",
        "下周将有客户来访，需要做好接待准备",
        "财务部门提醒大家及时提交报销单据",
        "人力资源部通知下周将进行团队建设活动",
        "技术部分享了最新的技术趋势和学习资源",
        "管理层强调了本月的工作重点和目标"
    ]
    
    text_messages = sample_messages
    print(f"✅ 使用 {len(text_messages)} 条示例消息")
    
    if len(text_messages) < MIN_MESSAGE_COUNT:
        print(f"⏭️  消息数量({len(text_messages)})少于阈值({MIN_MESSAGE_COUNT})，跳过")
        return None
    
    # 使用AI生成总结
    if AI_SUMMARIZER_AVAILABLE:
        print("✅ 使用AI生成总结...")
        ai_result = ai_summarize_messages(text_messages, summary_type=summary_type)
        
        if ai_result.get("success"):
            summary = ai_result.get("summary")
            # 生成AI建议或金句
            inspiration = ai_generate_inspiration(summary)
            
            # 构建消息内容
            if summary_type == "daily":
                message = f"📊 {group_name} - 群会议纪要日报 ({date_str})\n\n"
            elif summary_type == "weekly":
                message = f"📊 {group_name} - 群会议纪要周报 ({date_str})\n\n"
            else:
                message = f"📊 {group_name} - 群会议纪要月报 ({date_str})\n\n"
            
            message += "════════════════════\n"
            message += f"📈 数据：{len(text_messages)} 条消息\n"
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
    print("🚀 测试群会议纪要机器人")
    
    bot = FeishuBot()
    
    # 目标群：策划一组
    target_group_id = "oc_bb817774c9b04c98003f941596f481bd"
    target_group_name = "策划一组"
    
    # 测试群：张贤良测试群
    test_group_id = "oc_3ea67ec60886f42c15e632954f08bb08"
    test_group_name = "张贤良测试群"
    
    print(f"\n🎯 目标群：{target_group_name}")
    print(f"📧 发送到：{test_group_name}")
    
    # 测试日报
    print("\n" + "="*60)
    print("📅 测试日报")
    print("="*60)
    daily_summary = generate_meeting_summary(target_group_name, target_group_id, bot, "daily")
    if daily_summary:
        print("\n📝 生成的日报：")
        print(daily_summary)
        print("\n📤 发送到测试群...")
        success = bot.send_message(test_group_id, daily_summary)
        if success:
            print("✅ 日报发送成功！")
        else:
            print("❌ 日报发送失败！")
    
    # 测试周报
    print("\n" + "="*60)
    print("📅 测试周报")
    print("="*60)
    weekly_summary = generate_meeting_summary(target_group_name, target_group_id, bot, "weekly")
    if weekly_summary:
        print("\n📝 生成的周报：")
        print(weekly_summary)
        print("\n📤 发送到测试群...")
        success = bot.send_message(test_group_id, weekly_summary)
        if success:
            print("✅ 周报发送成功！")
        else:
            print("❌ 周报发送失败！")
    
    # 测试月报
    print("\n" + "="*60)
    print("📅 测试月报")
    print("="*60)
    monthly_summary = generate_meeting_summary(target_group_name, target_group_id, bot, "monthly")
    if monthly_summary:
        print("\n📝 生成的月报：")
        print(monthly_summary)
        print("\n📤 发送到测试群...")
        success = bot.send_message(test_group_id, monthly_summary)
        if success:
            print("✅ 月报发送成功！")
        else:
            print("❌ 月报发送失败！")

if __name__ == "__main__":
    main()

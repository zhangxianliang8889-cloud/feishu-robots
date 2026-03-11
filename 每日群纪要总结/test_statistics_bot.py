#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试群消息统计机器人的日报、周报、月报功能
使用群消息统计机器人的配置和凭证
"""

import requests
import json
import time
from datetime import datetime, timedelta
import sys
import os

# 添加当前目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 优先使用群消息统计机器人的配置
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '飞书统计群成员消息数'))

try:
    from config import *
except ImportError:
    DAILY_TIME = "09:00"
    WEEKLY_TIME = "12:00"
    MONTHLY_TIME = "15:00"
    SEND_MODE = "all"
    WHITELIST_GROUPS = []
    BLACKLIST_GROUPS = []
    SKIP_EMPTY_GROUPS = True
    MIN_MESSAGE_COUNT = 3
    SHOW_TOP_MESSAGES = 5
    SHOW_TOP_USERS = 5
    SHOW_ACTIVE_HOURS = True
    SHOW_KEYWORDS = True
    KEYWORD_COUNT = 10
    SHOW_EMOJI_STATS = False
    EMOJI_COUNT = 5
    REPORT_FORMAT = "simple"
    SHOW_GENERATE_TIME = True
    SHOW_BOT_SIGNATURE = True
    DEBUG_MODE = False
    DEBUG_GROUP = "张贤良测试群"
    TEST_MODE = False
    TEST_GROUP = "张贤良测试群"
    FEISHU_APP_ID = "cli_a92aab4685f9dbc7"
    FEISHU_APP_SECRET = "kjoKDg6QN3fcR58IvLj8WeK3YwkRwsXO"

try:
    from ai_summarizer import ai_analyze_statistics, ai_generate_insights
    AI_ANALYZER_AVAILABLE = True
except ImportError:
    AI_ANALYZER_AVAILABLE = False

BOT_NAME = "群消息统计"

# 飞书API相关
APP_ID = FEISHU_APP_ID
APP_SECRET = FEISHU_APP_SECRET
NO_PROXY = {}  # 无代理设置

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
            response = requests.post(url, headers=headers, json=data, timeout=10, proxies=NO_PROXY)
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
    
    def get_group_members(self, group_id):
        """获取群成员列表"""
        token = self.get_access_token()
        if not token:
            return {}
        
        url = f"https://open.feishu.cn/open-apis/im/v1/chats/{group_id}/members"
        headers = {
            "Authorization": f"Bearer {token}"
        }
        params = {
            "page_size": 100,
            "member_id_type": "open_id"
        }
        
        members = {}
        page_token = None
        
        try:
            while True:
                if page_token:
                    params["page_token"] = page_token
                
                response = requests.get(url, headers=headers, params=params, timeout=10, proxies=NO_PROXY)
                response.raise_for_status()
                result = response.json()
                
                if result.get("code") == 0:
                    items = result.get("data", {}).get("items", [])
                    for item in items:
                        member_id = item.get("member_id")
                        name = item.get("name")
                        if member_id and name:
                            members[member_id] = name
                    
                    page_token = result.get("data", {}).get("page_token")
                    if not page_token:
                        break
                else:
                    print(f"获取群成员失败: {result.get('msg')}")
                    break
        except Exception as e:
            print(f"获取群成员异常: {e}")
        
        return members
    
    def get_group_messages(self, group_id, start_time, end_time):
        """获取群消息"""
        token = self.get_access_token()
        if not token:
            return []
        
        url = "https://open.feishu.cn/open-apis/im/v1/messages"
        headers = {
            "Authorization": f"Bearer {token}"
        }
        params = {
            "container_id": group_id,
            "container_id_type": "chat",
            "page_size": 100
        }
        
        messages = []
        page_token = None
        
        try:
            while True:
                if page_token:
                    params["page_token"] = page_token
                
                response = requests.get(url, headers=headers, params=params, timeout=10, proxies=NO_PROXY)
                response.raise_for_status()
                result = response.json()
                
                if result.get("code") == 0:
                    items = result.get("data", {}).get("items", [])
                    for msg in items:
                        create_time = msg.get("create_time")
                        if create_time:
                            msg_time = int(create_time)  # 保持毫秒级
                            if start_time <= msg_time <= end_time:
                                messages.append(msg)
                    
                    page_token = result.get("data", {}).get("page_token")
                    if not page_token:
                        break
                else:
                    print(f"获取群消息失败: {result.get('msg')}")
                    break
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
            response = requests.post(url, headers=headers, params=params, json=data, timeout=10, proxies=NO_PROXY)
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

def analyze_message_statistics(messages, members_map):
    """分析消息统计数据"""
    stats = {
        "total_messages": 0,
        "user_stats": {},
        "hour_stats": {},
        "message_types": {},
        "keywords": [],
        "emojis": []
    }
    
    CEO_LIST = {"张贤良", "蒋文卿"}
    
    for user_name in members_map.values():
        if user_name not in CEO_LIST:
            stats["user_stats"][user_name] = 0
    
    for msg in messages:
        stats["total_messages"] += 1
        
        sender = msg.get("sender", {})
        sender_id = sender.get("sender_id", {})
        if isinstance(sender_id, dict):
            user_id = sender_id.get("open_id") or sender_id.get("user_id") or sender_id.get("union_id")
        else:
            user_id = sender_id
        
        if user_id:
            user_name = members_map.get(user_id, "未知用户")
            # 跳过CEO用户
            if user_name in CEO_LIST:
                continue
            if user_name not in stats["user_stats"]:
                stats["user_stats"][user_name] = 0
            stats["user_stats"][user_name] += 1
        
        # 统计发送时间
        create_time = msg.get("create_time")
        if create_time:
            try:
                # 飞书API返回的时间戳是毫秒级
                msg_time = int(create_time) / 1000
                hour = datetime.fromtimestamp(msg_time).hour
                if hour not in stats["hour_stats"]:
                    stats["hour_stats"][hour] = 0
                stats["hour_stats"][hour] += 1
            except Exception as e:
                print(f"时间解析失败: {e}")
        
        # 统计消息类型
        msg_type = msg.get("msg_type")
        if msg_type:
            if msg_type not in stats["message_types"]:
                stats["message_types"][msg_type] = 0
            stats["message_types"][msg_type] += 1
    
    return stats

def generate_statistics_report(group_name, stats, summary_type="daily"):
    """生成统计报告"""
    SEP = "────────────────────"
    
    if summary_type == "daily":
        date_str = datetime.now().strftime("%Y-%m-%d")
        period_text = "今日"
        star_text = "今日之星"
        title = f"📊 {group_name} - 群消息日报"
    elif summary_type == "weekly":
        start_date = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
        end_date = datetime.now().strftime("%Y-%m-%d")
        date_str = f"{start_date} ~ {end_date}"
        period_text = "本周"
        star_text = "本周之星"
        title = f"📊 {group_name} - 群消息周报"
    else:
        date_str = datetime.now().strftime("%Y-%m")
        period_text = "本月"
        star_text = "本月之星"
        title = f"📊 {group_name} - 群消息月报"
    
    report = f"{title}\n{SEP}\n"
    
    active_users = len([count for count in stats['user_stats'].values() if count > 0])
    total_users = len(stats.get('user_stats', {}))
    active_rate = (active_users / total_users * 100) if total_users > 0 else 0
    
    report += f"📈 {period_text}数据：{stats['total_messages']}条 | {active_users}/{total_users}人活跃 ({active_rate:.0f}%)\n\n"
    
    if stats['user_stats']:
        sorted_users = sorted(stats['user_stats'].items(), key=lambda x: x[1], reverse=True)
        
        if len(sorted_users) >= 3:
            report += f"🏆 {star_text}\n"
            report += f"   🥇 {sorted_users[0][0]} ({sorted_users[0][1]}条)\n"
            report += f"   🥈 {sorted_users[1][0]} ({sorted_users[1][1]}条)\n"
            report += f"   🥉 {sorted_users[2][0]} ({sorted_users[2][1]}条)\n\n"
        
        report += f"📋 活跃榜单\n{SEP}\n"
        for i, (user, count) in enumerate(sorted_users, 1):
            if count >= 20:
                emoji = "🔥"
            elif count >= 10:
                emoji = "🔥"
            elif count >= 5:
                emoji = "💬"
            elif count >= 1:
                emoji = "💭"
            else:
                emoji = "💤"
            report += f"{i}. {user} {count}条 {emoji}\n"
        report += "\n"
    
    if stats['total_messages'] > 100:
        report += "🌟 群氛围火热！大家交流积极，群智涌现！\n\n"
    elif stats['total_messages'] > 50:
        report += "🌟 群氛围活跃！大家交流积极，群智涌现！\n\n"
    elif stats['total_messages'] > 20:
        report += "🌟 群氛围良好！大家交流积极，群智涌现！\n\n"
    
    if stats['user_stats']:
        inactive_users = [user for user, count in stats['user_stats'].items() if count == 0]
        if inactive_users:
            report += "💌 期待你的声音\n"
            report += f"   {', '.join(inactive_users[:5])}"
            if len(inactive_users) > 5:
                report += " 等"
            report += "\n   你的想法对我们很重要！\n\n"
    
    report += f"{SEP}\n"
    report += f"⏰ {datetime.now().strftime('%H:%M')} | 🤖 群消息统计\n"
    
    return report

def main():
    """主函数"""
    import argparse
    parser = argparse.ArgumentParser(description='测试群消息统计机器人')
    parser.add_argument('--send', action='store_true', help='实际发送到测试群（默认只预览）')
    parser.add_argument('--type', choices=['daily', 'weekly', 'monthly', 'all'], default='all', help='报告类型')
    args = parser.parse_args()
    
    print("🚀 测试群消息统计机器人")
    if not args.send:
        print("⚠️ 预览模式（添加 --send 参数实际发送）")
    
    bot = FeishuBot()
    
    target_group_id = "oc_48e2db5c69667ddfe1a50331939f98e1"
    target_group_name = "英璨市场部大群"
    
    test_group_id = "oc_3ea67ec60886f42c15e632954f08bb08"
    test_group_name = "张贤良测试群"
    
    print(f"\n🎯 目标群：{target_group_name}")
    print(f"📧 发送到：{test_group_name}")
    
    members_map = bot.get_group_members(target_group_id)
    print(f"✅ 获取到 {len(members_map)} 位真实群成员")
    
    if not members_map:
        print("❌ 无法获取群成员，使用示例数据")
        members_map = {
            "user1": "张三",
            "user2": "李四",
            "user3": "王五",
            "user4": "赵六",
            "user5": "钱七"
        }
    
    # CEO列表，不统计他们的消息
    CEO_LIST = {"张贤良", "蒋文卿"}
    
    # 生成模拟消息数据
    def generate_sample_messages(members_map, count=114):
        """生成模拟消息数据"""
        messages = []
        
        # 过滤掉CEO用户
        filtered_members = {uid: name for uid, name in members_map.items() if name not in CEO_LIST}
        user_ids = list(filtered_members.keys())
        user_names = list(filtered_members.values())
        
        # 模拟不同用户的消息数（已排除CEO）
        message_counts = {
            user_names[0]: 26,  # 吴诗雨
            user_names[1]: 24,  # 洪永进
            user_names[2]: 14,  # 胡慧敏
            user_names[3]: 11,  # 邓思文
            user_names[4]: 10,  # 石孟
            user_names[5]: 9,   # 陈鑫涛
            user_names[6]: 5,   # 吴梦凡
            user_names[7]: 5,   # 张帆
            user_names[8]: 4,   # 林燕
            user_names[9]: 4,   # 宁宁子
            user_names[10]: 1,  # 董曜然
            user_names[11]: 1,  # 蔡艺云
            user_names[12]: 0,  # 肖艳妮
        }
        
        current_time = int(time.time() * 1000)
        
        for user_name, msg_count in message_counts.items():
            user_id = user_ids[user_names.index(user_name)]
            for i in range(msg_count):
                msg = {
                    "sender": {
                        "sender_id": user_id
                    },
                    "create_time": str(current_time - i * 60000),  # 每条消息间隔1分钟
                    "msg_type": "text" if i % 5 != 0 else "image"
                }
                messages.append(msg)
        
        return messages
    
    # 测试日报
    print("\n" + "="*60)
    print("📅 测试日报")
    print("="*60)
    messages = generate_sample_messages(members_map)
    print(f"✅ 使用 {len(messages)} 条模拟消息")
    
    if len(messages) >= MIN_MESSAGE_COUNT:
        stats = analyze_message_statistics(messages, members_map)
        daily_report = generate_statistics_report(target_group_name, stats, "daily")
        print("\n📝 生成的日报：")
        print(daily_report)
        
        if args.send and args.type in ['daily', 'all']:
            print("\n📤 发送到测试群...")
            success = bot.send_message(test_group_id, daily_report)
            if success:
                print("✅ 日报发送成功！")
            else:
                print("❌ 日报发送失败！")
        elif not args.send:
            print("\n💡 预览模式，未发送（添加 --send 参数实际发送）")
    else:
        print(f"⏭️ 消息数量({len(messages)})少于阈值({MIN_MESSAGE_COUNT})，跳过")
    
    if args.type not in ['weekly', 'all']:
        return
    
    print("\n" + "="*60)
    print("📅 测试周报")
    print("="*60)
    weekly_messages = generate_sample_messages(members_map, 300)
    print(f"✅ 使用 {len(weekly_messages)} 条模拟消息")
    
    if len(weekly_messages) >= MIN_MESSAGE_COUNT:
        stats = analyze_message_statistics(weekly_messages, members_map)
        weekly_report = generate_statistics_report(target_group_name, stats, "weekly")
        print("\n📝 生成的周报：")
        print(weekly_report)
        
        if args.send and args.type in ['weekly', 'all']:
            print("\n📤 发送到测试群...")
            success = bot.send_message(test_group_id, weekly_report)
            if success:
                print("✅ 周报发送成功！")
            else:
                print("❌ 周报发送失败！")
        elif not args.send:
            print("\n💡 预览模式，未发送（添加 --send 参数实际发送）")
    else:
        print(f"⏭️ 消息数量({len(weekly_messages)})少于阈值({MIN_MESSAGE_COUNT})，跳过")
    
    if args.type not in ['monthly', 'all']:
        return
    
    print("\n" + "="*60)
    print("📅 测试月报")
    print("="*60)
    monthly_messages = generate_sample_messages(members_map, 1000)
    print(f"✅ 使用 {len(monthly_messages)} 条模拟消息")
    
    if len(monthly_messages) >= MIN_MESSAGE_COUNT:
        stats = analyze_message_statistics(monthly_messages, members_map)
        monthly_report = generate_statistics_report(target_group_name, stats, "monthly")
        print("\n📝 生成的月报：")
        print(monthly_report)
        
        if args.send and args.type in ['monthly', 'all']:
            print("\n📤 发送到测试群...")
            success = bot.send_message(test_group_id, monthly_report)
            if success:
                print("✅ 月报发送成功！")
            else:
                print("❌ 月报发送失败！")
        elif not args.send:
            print("\n💡 预览模式，未发送（添加 --send 参数实际发送）")
    else:
        print(f"⏭️ 消息数量({len(monthly_messages)})少于阈值({MIN_MESSAGE_COUNT})，跳过")

if __name__ == "__main__":
    main()

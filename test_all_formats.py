#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""测试所有报告格式 - 发送到张贤良测试群"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '飞书统计群成员消息数'))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '每日群纪要总结'))

import requests
import json
from datetime import datetime, timedelta

# 飞书配置
FEISHU_APP_ID = "cli_a9233dfe18389bde"
FEISHU_APP_SECRET = "8gvZm8C04sS0GJXtDQdkkeAOJV6gCr4w"
TEST_GROUP_ID = "oc_3ea67ec60886f42c15e632954f08bb08"  # 张贤良测试群

def get_tenant_token():
    url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
    data = {"app_id": FEISHU_APP_ID, "app_secret": FEISHU_APP_SECRET}
    resp = requests.post(url, json=data).json()
    return resp.get("tenant_access_token")

def send_message(token, group_id, text):
    url = "https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type=chat_id"
    headers = {"Authorization": f"Bearer {token}"}
    data = {
        "receive_id": group_id,
        "msg_type": "text",
        "content": json.dumps({"text": text})
    }
    try:
        resp = requests.post(url, json=data, headers=headers, timeout=10).json()
        code = resp.get("code")
        if code != 0:
            print(f"   ⚠️ 发送失败: {resp.get('msg', '未知错误')} (code: {code})")
            return False
        return True
    except Exception as e:
        print(f"   ❌ 发送异常: {e}")
        return False

# ========== 群消息统计机器人格式 ==========

def generate_daily_report():
    """日报格式"""
    report = """📊 张贤良测试群 - 群消息日报 (2026-03-07)

📈 今日数据：45 条消息 | 5/8 人活跃 (62%)

🏆 今日之星：🥇张三(18条) 🥈李四(12条) 🥉王五(8条)

📋 全员榜单：
   1. 张三: 18条 🔥
   2. 李四: 12条 💬
   3. 王五: 8条 💬
   4. 赵六: 5条 💭
   5. 钱七: 2条 💭
   6. 孙八: 0条 💤
   7. 周九: 0条 💤
   8. 吴十: 0条 💤

💪 今日交流不错！继续保持，期待更多伙伴加入讨论！

💌 期待你的声音：孙八, 周九, 吴十
   你的想法对我们很重要，期待听到你的分享！

🌈 这里是我们灵感碰撞的地方！💪 勇于表达，让群智涌现！
⏰ 2026-03-07 10:00:00 | 🤖 群消息统计机器人"""
    return report

def generate_weekly_report():
    """周报格式"""
    report = """📊 张贤良测试群 - 群消息周报 (2026-03-02 ~ 2026-03-08)

📈 本周数据：280 条消息 | 6/8 人活跃 (75%) | 日均 40 条

🏆 本周贡献榜：🥇张三(85条) 🥈李四(72条) 🥉王五(58条) 🏅赵六(35条) 🏅钱七(30条)

📋 全员周榜：
   1. 张三: 85条 (日均12.1) 🔥
   2. 李四: 72条 (日均10.3) 🔥
   3. 王五: 58条 (日均8.3) 💬
   4. 赵六: 35条 (日均5.0) 💬
   5. 钱七: 30条 (日均4.3) 💭
   6. 孙八: 0条 (日均0.0) 💤
   7. 周九: 0条 (日均0.0) 💤
   8. 吴十: 0条 (日均0.0) 💤

🌟 本周群氛围超棒！团队协作紧密，群智涌现！

💌 期待你的声音：孙八, 周九, 吴十
   本周没有看到你的发言，期待下周听到你的想法！

🎉 特别感谢：张三, 李四, 王五
   你们的分享让群更有价值！

🌈 这里是我们灵感碰撞的地方！💪 勇于表达，让群智涌现！
⏰ 2026-03-07 10:00:00 | 🤖 群消息统计机器人"""
    return report

def generate_monthly_report():
    """月报格式"""
    report = """📊 张贤良测试群 - 群消息月报 (2026-02)

📈 本月数据：850 条消息 | 7/8 人活跃 (87%) | 日均 30 条

🏆 本月贡献榜：🥇张三(280条) 🥈李四(220条) 🥉王五(180条) 🏅赵六(100条) 🏅钱七(70条)

📋 全员月榜：
   1. 张三: 280条 (日均10.0) 🔥
   2. 李四: 220条 (日均7.9) 🔥
   3. 王五: 180条 (日均6.4) 💬
   4. 赵六: 100条 (日均3.6) 💬
   5. 钱七: 70条 (日均2.5) 💭
   6. 孙八: 0条 (日均0.0) 💤
   7. 周九: 0条 (日均0.0) 💤
   8. 吴十: 0条 (日均0.0) 💤

🌟 本月群氛围极佳！团队协作高效，群智涌现！

💌 期待你的声音：孙八, 周九, 吴十
   本月没有看到你的发言，期待下月听到你的想法！

🎉 特别感谢：张三, 李四, 王五, 赵六, 钱七
   你们的分享让群更有价值，感谢你们的付出！

🌈 这里是我们灵感碰撞的地方！💪 勇于表达，让群智涌现！
⏰ 2026-03-07 10:00:00 | 🤖 群消息统计机器人"""
    return report

# ========== 群会议纪要机器人格式 ==========

def generate_daily_summary():
    """日报格式"""
    report = """📅 每日群会议纪要 (2026-03-07)
════════════════════════════════════════
👥 参与人数：5人 | 💬 消息数：45条

📌 今日要点：
• 讨论了新项目的开发计划
• 确定了下周的会议时间
• 分享了技术文档链接
• 讨论了系统架构设计
• 确认了需求变更

✅ 完成事项：
• 确定项目排期
• 确认需求文档
• 通过技术方案

📋 待办事项：
• 需要完成原型设计
• 请张三跟进服务器配置
• 记得提交周报

📎 相关链接：
• https://docs.example.com/project
• https://github.com/example/repo

💡 今日总结：群聊主要围绕「项目、开发、计划」展开，共5人参与。
════════════════════════════════════════
⏰ 生成时间：2026-03-07 21:00:00
🤖 由群会议纪要AI机器人自动生成"""
    return report

def generate_weekly_summary():
    """周报格式"""
    report = """📊 每周群会议纪要 (2026-03-02 ~ 2026-03-08)
════════════════════════════════════════
👥 参与人数：6人 | 💬 消息数：280条
📊 日均消息：40条

📌 本周重点讨论：
• 新项目开发计划
• 技术方案评审
• 团队协作流程优化
• 客户需求变更
• 系统架构设计
• 数据库选型讨论
• 接口规范制定
• 测试策略规划

✅ 本周决议：
• 决定采用微服务架构
• 确定下周发布计划
• 同意增加测试资源
• 确认使用MySQL数据库
• 通过新的接口规范

📋 待跟进事项：
• 需要完成接口文档
• 请李四跟进数据库优化
• 记得提交周报
• 安排代码评审会议
• 更新项目文档

❓ 本周疑问：
• 如何处理并发问题？
• 有没有更好的方案？
• 这个需求是否合理？

💡 建议与想法：
• 建议增加代码评审环节
• 可以尝试自动化测试
• 推荐引入CI/CD流程

────────────────────────────────────────
📊 本周复盘：
• 本周交流活跃，团队协作良好
• 建议继续保持，可尝试更深入的话题讨论
• 有5项待办事项，建议及时跟进

🎯 周总结：本周主要围绕「项目、开发、架构」展开讨论。
════════════════════════════════════════
⏰ 生成时间：2026-03-07 09:00:00
🤖 由群会议纪要AI机器人自动生成"""
    return report

def generate_monthly_summary():
    """月报格式"""
    report = """📈 每月群会议纪要 (2026-02)
════════════════════════════════════════
👥 参与人数：8人 | 💬 消息数：850条
📊 日均消息：30条

📌 本月核心话题：
• 项目开发进度跟踪
• 技术方案讨论
• 团队建设活动
• 客户需求分析
• 系统性能优化
• 代码规范制定
• 文档体系建设
• 测试流程改进
• 部署流程优化
• 监控告警配置

✅ 本月重要决议：
• 决定采用敏捷开发模式
• 确定代码规范标准
• 通过新功能设计方案
• 确认使用Docker部署
• 建立代码评审机制

📋 待跟进事项：
• 需要完善监控体系
• 请团队跟进性能优化
• 更新技术文档
• 安排团队培训

💡 本月建议汇总：
• 建议定期组织技术分享
• 可以优化会议流程
• 推荐使用新的协作工具
• 建议引入自动化测试
• 推荐建立知识库

────────────────────────────────────────
📊 月度复盘：
• 本月交流较为活跃，团队氛围良好
• 建议继续鼓励成员分享，提升讨论质量
• 有4项待办事项，建议梳理优先级

🎯 月总结：本月主要围绕「项目、开发、团队、技术」展开讨论。

🚀 下月展望：期待更多精彩讨论，群智涌现！
════════════════════════════════════════
⏰ 生成时间：2026-03-07 09:30:00
🤖 由群会议纪要AI机器人自动生成"""
    return report

def main():
    print("=" * 70)
    print("🧪 测试所有报告格式 - 发送到张贤良测试群")
    print("=" * 70)
    print()
    
    # 获取token
    print("🔑 获取飞书Token...")
    token = get_tenant_token()
    if not token:
        print("❌ Token获取失败")
        return
    print("✅ Token获取成功\n")
    
    # 测试群ID（张贤良测试群）
    test_group_id = TEST_GROUP_ID
    
    # 1. 群消息统计 - 日报
    print("📊 发送群消息统计 - 日报...")
    send_message(token, test_group_id, "🧪 【测试】群消息统计机器人 - 日报格式\n\n" + generate_daily_report())
    print("✅ 日报发送成功\n")
    
    # 2. 群消息统计 - 周报
    print("📊 发送群消息统计 - 周报...")
    send_message(token, test_group_id, "🧪 【测试】群消息统计机器人 - 周报格式\n\n" + generate_weekly_report())
    print("✅ 周报发送成功\n")
    
    # 3. 群消息统计 - 月报
    print("📊 发送群消息统计 - 月报...")
    send_message(token, test_group_id, "🧪 【测试】群消息统计机器人 - 月报格式\n\n" + generate_monthly_report())
    print("✅ 月报发送成功\n")
    
    # 4. 群会议纪要 - 日报
    print("📅 发送群会议纪要 - 日报...")
    send_message(token, test_group_id, "🧪 【测试】群会议纪要机器人 - 日报格式\n\n" + generate_daily_summary())
    print("✅ 日报发送成功\n")
    
    # 5. 群会议纪要 - 周报
    print("📅 发送群会议纪要 - 周报...")
    send_message(token, test_group_id, "🧪 【测试】群会议纪要机器人 - 周报格式\n\n" + generate_weekly_summary())
    print("✅ 周报发送成功\n")
    
    # 6. 群会议纪要 - 月报
    print("📅 发送群会议纪要 - 月报...")
    send_message(token, test_group_id, "🧪 【测试】群会议纪要机器人 - 月报格式\n\n" + generate_monthly_summary())
    print("✅ 月报发送成功\n")
    
    print("=" * 70)
    print("✅ 所有格式测试完成！请查看张贤良测试群")
    print("=" * 70)

if __name__ == "__main__":
    main()

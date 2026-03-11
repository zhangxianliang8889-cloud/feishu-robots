#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI智能总结模块 - 使用火山引擎豆包API
真正的智能总结，而不是简单摘抄
"""

import os
import json
import re
import requests
from typing import List, Dict, Any, Optional

AI_CONFIG = {
    "api_key": "a773de80-b0c6-4430-b8f0-80e28aaecccd",
    "base_url": "https://ark.cn-beijing.volces.com/api/v3",
    "model": "doubao-seed-1-8-251228"
}

def ai_summarize_messages(messages, summary_type: str = "daily") -> Dict[str, Any]:
    """
    使用AI智能总结消息
    
    Args:
        messages: 消息列表（字符串列表或字典列表）
        summary_type: daily/weekly/monthly
    
    Returns:
        dict: 包含总结内容
    """
    if not messages:
        return {
            "success": False,
            "summary": "暂无消息内容",
            "categories": {},
            "key_insights": []
        }
    
    # 处理消息格式（支持字符串列表或字典列表）
    filtered_messages = []
    for msg in messages:
        # 如果是字典，提取content字段
        if isinstance(msg, dict):
            content_text = msg.get('content', '')
            sender = msg.get('sender', '未知')
            if content_text:
                msg_text = f"{sender}: {content_text}"
            else:
                continue
        else:
            msg_text = str(msg)
        
        # 过滤掉无意义的消息
        if not any(keyword in msg_text for keyword in ['收到', '好的', 'ok', 'OK', '好', '嗯', '知道了', '明白', '收到了', '机器人', 'bot', 'BOT']):
            filtered_messages.append(msg_text)
    
    # 合并消息内容（无数量限制）
    content = "\n".join(filtered_messages)  # 无数量限制
    
    # 根据总结类型设置提示词
    if summary_type == "daily":
        prompt = f"""请对以下群聊内容进行智能总结，要求：
1. 提取3-5个核心话题，每个话题用一句话概括
2. 识别完成的事项和待办事项
3. 给出2-3条关键洞察或建议
4. 使用中文，语言简洁专业

群聊内容：
{content}

请按以下格式输出：
📌 核心话题：
• [话题1]：[一句话概括]
• [话题2]：[一句话概括]
...

✅ 完成事项：
• [事项1]
• [事项2]
...

📋 待办事项：
• [事项1]
• [事项2]
...

💡 关键洞察：
• [洞察1]
• [洞察2]
..."""
    elif summary_type == "weekly":
        prompt = f"""请对以下群聊内容进行周报总结，要求：
1. 提取本周核心话题和讨论重点
2. 总结本周重要决议和成果
3. 列出待跟进事项
4. 给出下周建议

群聊内容：
{content}

请按以下格式输出：
📌 本周核心话题：
• [话题1]：[详细描述]
...

✅ 本周重要决议：
• [决议1]
...

📋 待跟进事项：
• [事项1]
...

💡 下周建议：
• [建议1]
..."""
    else:  # monthly
        prompt = f"""请对以下群聊内容进行月报总结，要求：
1. 提取本月核心话题和讨论重点
2. 总结本月重要决议和成果
3. 列出待跟进事项
4. 给出下月展望

群聊内容：
{content}

请按以下格式输出：
📌 本月核心话题：
• [话题1]：[详细描述]
...

✅ 本月重要决议：
• [决议1]
...

📋 待跟进事项：
• [事项1]
...

🚀 下月展望：
• [展望1]
..."""
    
    try:
        # 调用豆包API
        headers = {
            "Authorization": f"Bearer {AI_CONFIG['api_key']}",
            "Content-Type": "application/json"
        }
        
        data = {
            "model": AI_CONFIG["model"],
            "messages": [
                {"role": "system", "content": "你是一个专业的群聊内容总结助手，擅长从杂乱的聊天记录中提取关键信息，生成结构化的会议纪要。"},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.7,
            "max_tokens": 2000
        }
        
        response = requests.post(
            f"{AI_CONFIG['base_url']}/chat/completions",
            headers=headers,
            json=data,
            timeout=60
        )
        
        if response.status_code == 200:
            result = response.json()
            ai_content = result.get("choices", [{}])[0].get("message", {}).get("content", "")
            
            # 解析AI返回的内容
            categories = {}
            key_insights = []
            
            # 提取核心话题
            if "📌 核心话题" in ai_content or "📌 本周核心话题" in ai_content or "📌 本月核心话题" in ai_content:
                topic_section = ai_content.split("📌")[1].split("✅")[0] if "✅" in ai_content else ai_content.split("📌")[1]
                topics = [line.strip() for line in topic_section.split("\n") if line.strip().startswith("•")]
                if topics:
                    categories["核心话题"] = "\n".join(topics[:5])
            
            # 提取关键洞察
            if "💡 关键洞察" in ai_content or "💡 下周建议" in ai_content or "🚀 下月展望" in ai_content:
                insight_section = ai_content.split("💡")[1] if "💡" in ai_content else ai_content.split("🚀")[1]
                insights = [line.strip()[2:] for line in insight_section.split("\n") if line.strip().startswith("•")]
                key_insights = insights[:3]
            
            return {
                "success": True,
                "summary": ai_content,
                "categories": categories,
                "key_insights": key_insights
            }
        else:
            print(f"AI API调用失败: {response.status_code} - {response.text}")
            return {
                "success": False,
                "summary": "AI服务暂时不可用",
                "categories": {},
                "key_insights": []
            }
    
    except Exception as e:
        print(f"AI总结失败: {e}")
        return {
            "success": False,
            "summary": f"AI总结出错: {str(e)}",
            "categories": {},
            "key_insights": []
        }

def ai_generate_inspiration(summary_text: str) -> str:
    """
    根据总结内容生成AI建议或名人金句
    
    Args:
        summary_text: 总结文本
    
    Returns:
        str: AI建议或金句
    """
    try:
        prompt = f"""根据以下群聊总结，给出一条简短的建议或相关的名人金句（不超过50字）：

{summary_text}

要求：
1. 与内容相关
2. 有启发性
3. 简短有力"""
        
        headers = {
            "Authorization": f"Bearer {AI_CONFIG['api_key']}",
            "Content-Type": "application/json"
        }
        
        data = {
            "model": AI_CONFIG["model"],
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.8,
            "max_tokens": 100
        }
        
        response = requests.post(
            f"{AI_CONFIG['base_url']}/chat/completions",
            headers=headers,
            json=data,
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            return result.get("choices", [{}])[0].get("message", {}).get("content", "💡 保持交流，群智涌现！")
        
        return "💡 保持交流，群智涌现！"
    
    except Exception as e:
        print(f"生成建议失败: {e}")
        return "💡 保持交流，群智涌现！"

def ai_categorize_and_summarize(messages: List[str]) -> Dict[str, Any]:
    """
    对消息进行分类并生成智能总结
    
    Args:
        messages: 消息列表
    
    Returns:
        dict: 分类和总结结果
    """
    return ai_summarize_messages(messages, summary_type="daily")

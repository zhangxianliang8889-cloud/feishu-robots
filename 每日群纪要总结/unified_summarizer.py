#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
统一总结生成器 - 避免代码重复
所有日报、周报、月报共用同一套逻辑
"""

import re

def is_noise_content(text):
    """判断是否是噪音内容"""
    if not text:
        return True
    noise_patterns = [
        r'^[好的收到嗯哦]+$',
        r'^[表情图片]+$',
        r'^[\d\s]+$',
        r'^[是的对]+$',
        r'^[哈哈]+$',
        r'^[谢谢感谢]+$',
    ]
    for pattern in noise_patterns:
        if re.match(pattern, text):
            return True
    return False

def extract_complete_sentences(text, max_sentences=5, max_length=200):
    """
    从文本中提取完整句子
    
    Args:
        text: 输入文本
        max_sentences: 最大句子数
        max_length: 最大总长度
    
    Returns:
        list: 完整句子列表
    """
    if not text:
        return []
    
    sentences = re.split(r'[。！？\n]', text)
    sentences = [s.strip() for s in sentences if s.strip()]
    
    result = []
    total_length = 0
    
    for sentence in sentences:
        if len(sentence) < 10:
            continue
        if is_noise_content(sentence):
            continue
        
        is_dup = False
        for existing in result:
            if sentence[:15] in existing or existing[:15] in sentence:
                is_dup = True
                break
        
        if is_dup:
            continue
        
        if total_length + len(sentence) > max_length:
            break
        
        result.append(sentence)
        total_length += len(sentence)
        
        if len(result) >= max_sentences:
            break
    
    return result

def generate_topic_summary(topic_contents, max_length=200):
    """
    生成主题总结
    
    Args:
        topic_contents: 主题内容列表
        max_length: 最大长度
    
    Returns:
        str: 总结文本
    """
    if not topic_contents:
        return "暂无具体讨论内容。"
    
    all_sentences = []
    for content in topic_contents[:15]:
        sentences = extract_complete_sentences(content, max_sentences=3, max_length=100)
        all_sentences.extend(sentences)
    
    unique_sentences = []
    for sentence in all_sentences[:8]:
        is_dup = False
        for existing in unique_sentences:
            if sentence[:15] in existing or existing[:15] in sentence:
                is_dup = True
                break
        if not is_dup:
            unique_sentences.append(sentence)
    
    if unique_sentences:
        summary = "。".join(unique_sentences[:3]) + "。"
        return summary[:max_length]
    
    return "暂无具体讨论内容。"

def generate_tasks_summary(tasks, max_items=5):
    """
    生成待办事项总结
    
    Args:
        tasks: 待办事项列表
        max_items: 最大条目数
    
    Returns:
        list: 处理后的待办事项列表
    """
    if not tasks:
        return []
    
    result = []
    for task in tasks[:max_items * 2]:
        if len(task) < 5:
            continue
        
        sentences = extract_complete_sentences(task, max_sentences=1, max_length=100)
        if sentences:
            result.append(sentences[0])
        
        if len(result) >= max_items:
            break
    
    return result

def generate_suggestions_summary(suggestions, max_items=5):
    """
    生成建议总结
    
    Args:
        suggestions: 建议列表
        max_items: 最大条目数
    
    Returns:
        list: 处理后的建议列表
    """
    if not suggestions:
        return []
    
    result = []
    for suggestion in suggestions[:max_items * 2]:
        if len(suggestion) < 5:
            continue
        
        sentences = extract_complete_sentences(suggestion, max_sentences=1, max_length=100)
        if sentences:
            result.append(sentences[0])
        
        if len(result) >= max_items:
            break
    
    return result

def generate_questions_summary(questions, max_items=5):
    """
    生成问题总结
    
    Args:
        questions: 问题列表
        max_items: 最大条目数
    
    Returns:
        list: 处理后的问题列表
    """
    if not questions:
        return []
    
    result = []
    for question in questions[:max_items * 2]:
        if len(question) < 5:
            continue
        
        sentences = extract_complete_sentences(question, max_sentences=1, max_length=100)
        if sentences:
            result.append(sentences[0])
        
        if len(result) >= max_items:
            break
    
    return result

def smart_categorize_messages(messages):
    """
    智能分类消息
    
    Args:
        messages: 消息列表
    
    Returns:
        dict: 分类后的消息
    """
    categories = {
        "工作讨论": [],
        "项目进展": [],
        "问题求助": [],
        "经验分享": [],
        "决策事项": [],
        "其他": []
    }
    
    keywords = {
        "工作讨论": ["讨论", "分析", "研究", "方案", "计划", "思路", "想法", "观点", "工作"],
        "项目进展": ["完成", "进度", "阶段", "里程碑", "交付", "上线", "发布", "项目"],
        "问题求助": ["问题", "求助", "帮忙", "请教", "疑问", "困惑", "怎么", "如何"],
        "经验分享": ["经验", "分享", "建议", "推荐", "心得", "体会", "总结"],
        "决策事项": ["决定", "确定", "通过", "同意", "批准", "确认", "定下"]
    }
    
    for msg in messages:
        content = msg.get("content", "")
        if not content or len(content) < 10:
            continue
        
        categorized = False
        for category, kws in keywords.items():
            for kw in kws:
                if kw in content:
                    categories[category].append(msg)
                    categorized = True
                    break
            if categorized:
                break
        
        if not categorized:
            categories["其他"].append(msg)
    
    return categories

if __name__ == "__main__":
    test_text = "譬如泰国的税收制度非常严格，导致街头很少看到超级跑车。所有现象背后都有制度支撑。"
    sentences = extract_complete_sentences(test_text)
    print("提取的句子:", sentences)
    
    summary = generate_topic_summary([test_text])
    print("生成的总结:", summary)

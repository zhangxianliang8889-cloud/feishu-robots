#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
智能文本总结模块 - 改进版
解决问题：断断续续、句子不完整、缺乏连贯性
"""

import re
from collections import Counter

def split_into_sentences(text):
    """将文本分割成完整句子"""
    if not text:
        return []
    
    sentences = re.split(r'[。！？\n]', text)
    sentences = [s.strip() for s in sentences if s.strip() and len(s.strip()) > 5]
    return sentences

def extract_complete_sentences(messages, max_sentences=20):
    """从消息中提取完整句子"""
    all_sentences = []
    
    for msg in messages:
        content = msg.get("content", "")
        if not content:
            continue
        
        sentences = split_into_sentences(content)
        for sentence in sentences:
            if len(sentence) > 10 and not is_noise(sentence):
                all_sentences.append({
                    "sentence": sentence,
                    "sender": msg.get("sender", "未知"),
                    "time": msg.get("time", "")
                })
    
    return all_sentences[:max_sentences]

def is_noise(text):
    """判断是否是噪音内容"""
    noise_patterns = [
        r'^[好的收到嗯哦]+$',  # 简单回复
        r'^[表情图片]+$',  # 表情图片
        r'^[\d\s]+$',  # 纯数字
        r'^[是的对]+$',  # 简单确认
    ]
    
    for pattern in noise_patterns:
        if re.match(pattern, text):
            return True
    return False

def categorize_sentences(sentences):
    """将句子分类到不同主题"""
    categories = {
        "工作讨论": [],
        "项目进展": [],
        "问题求助": [],
        "经验分享": [],
        "决策事项": [],
        "其他": []
    }
    
    keywords = {
        "工作讨论": ["讨论", "分析", "研究", "方案", "计划", "思路", "想法", "观点"],
        "项目进展": ["完成", "进度", "阶段", "里程碑", "交付", "上线", "发布"],
        "问题求助": ["问题", "求助", "帮忙", "请教", "疑问", "困惑", "怎么"],
        "经验分享": ["经验", "分享", "建议", "推荐", "心得", "体会", "总结"],
        "决策事项": ["决定", "确定", "通过", "同意", "批准", "确认", "定下"]
    }
    
    for item in sentences:
        sentence = item["sentence"]
        categorized = False
        
        for category, kws in keywords.items():
            for kw in kws:
                if kw in sentence:
                    categories[category].append(item)
                    categorized = True
                    break
            if categorized:
                break
        
        if not categorized:
            categories["其他"].append(item)
    
    return categories

def generate_coherent_summary(sentences, max_length=200):
    """生成连贯的摘要"""
    if not sentences:
        return "暂无具体讨论内容。"
    
    unique_sentences = []
    for item in sentences:
        sentence = item["sentence"]
        is_dup = False
        for us in unique_sentences:
            if sentence[:15] in us["sentence"] or us["sentence"][:15] in sentence:
                is_dup = True
                break
        if not is_dup:
            unique_sentences.append(item)
    
    summary_parts = []
    current_length = 0
    
    for item in unique_sentences[:5]:
        sentence = item["sentence"]
        if current_length + len(sentence) > max_length:
            break
        summary_parts.append(sentence)
        current_length += len(sentence)
    
    if summary_parts:
        return "。".join(summary_parts) + "。"
    return "暂无具体讨论内容。"

def extract_key_points(messages, category_name, max_points=3):
    """提取关键要点"""
    sentences = extract_complete_sentences(messages, max_sentences=30)
    categories = categorize_sentences(sentences)
    
    category_sentences = categories.get(category_name, [])
    
    if not category_sentences:
        return []
    
    key_points = []
    for item in category_sentences[:max_points]:
        sentence = item["sentence"]
        if len(sentence) > 15:
            key_points.append({
                "content": sentence[:80] + "..." if len(sentence) > 80 else sentence,
                "sender": item["sender"]
            })
    
    return key_points

def smart_summarize(messages, summary_type="daily"):
    """
    智能总结主函数
    
    Args:
        messages: 消息列表
        summary_type: daily/weekly/monthly
    
    Returns:
        dict: 包含各类总结内容
    """
    sentences = extract_complete_sentences(messages, max_sentences=50)
    categories = categorize_sentences(sentences)
    
    result = {
        "total_sentences": len(sentences),
        "categories": {},
        "key_topics": [],
        "summary": ""
    }
    
    for category, items in categories.items():
        if items:
            result["categories"][category] = {
                "count": len(items),
                "items": items[:5],
                "summary": generate_coherent_summary(items, max_length=150)
            }
    
    all_text = " ".join([item["sentence"] for item in sentences])
    words = re.findall(r'[\u4e00-\u9fa5]{2,}', all_text)
    word_freq = Counter(words)
    result["key_topics"] = [w for w, _ in word_freq.most_common(5)]
    
    main_categories = [cat for cat, data in result["categories"].items() 
                       if data["count"] >= 2 and cat != "其他"]
    
    if main_categories:
        summary_parts = []
        for cat in main_categories[:3]:
            cat_summary = result["categories"][cat]["summary"]
            if cat_summary != "暂无具体讨论内容。":
                summary_parts.append(f"【{cat}】{cat_summary}")
        result["summary"] = "\n\n".join(summary_parts)
    else:
        result["summary"] = generate_coherent_summary(sentences, max_length=300)
    
    return result

if __name__ == "__main__":
    test_messages = [
        {"content": "今天我们讨论一下项目的进度问题。目前第一阶段已经完成了。", "sender": "张三", "time": "10:00"},
        {"content": "好的，那下一步我们需要做什么？", "sender": "李四", "time": "10:05"},
        {"content": "下一步是进行用户测试，预计需要两周时间。", "sender": "张三", "time": "10:10"},
        {"content": "我有个问题，用户测试的方案确定了吗？", "sender": "王五", "time": "10:15"},
        {"content": "方案已经确定，我会分享给大家参考。", "sender": "张三", "time": "10:20"},
    ]
    
    result = smart_summarize(test_messages)
    print("=" * 80)
    print("📊 智能总结结果")
    print("=" * 80)
    print(f"\n总句子数: {result['total_sentences']}")
    print(f"\n关键话题: {', '.join(result['key_topics'])}")
    print(f"\n分类统计:")
    for cat, data in result['categories'].items():
        print(f"  - {cat}: {data['count']}条")
    print(f"\n总结:\n{result['summary']}")

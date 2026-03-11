#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys
sys.path.insert(0, '/root/feishu_bots/meeting_bot')
from ai_summarizer import ai_summarize_messages

# 测试AI总结功能
messages = [
    '刺棠房子塌了',
    '作者很喜欢在文中化用一些诗词',
    '她的另一部《白雪歌》也挺好看的',
    '非太监版的《观鹤笔记》',
    '@user 全部是李贺的！！！鬼里鬼气！！！我喜欢'
]

print("Testing AI summarizer...")
result = ai_summarize_messages(messages, summary_type="daily")
print("Success:", result.get("success"))
print("Summary length:", len(result.get("summary", "")))
print("Categories:", list(result.get("categories", {}).keys()))
print("\nSummary preview:")
print(result.get("summary", "")[:500])

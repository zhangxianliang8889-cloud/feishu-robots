#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
检查未知用户是否在缓存中
"""

import json
import os

# 未知用户列表
unknown_users = [
    "ou_7b676a09e299759b0b9a1bcb9abf03e5",
    "ou_bf1ac932c4ed35a0182854860b3533a2",
    "ou_8b66227bbe65f564292bed7df60635f9",
    "ou_e290b3293228299ff50e3c6794aa2a23",
    "ou_499438af277a590126e8e037f977afbe"
]

# 加载缓存
cache_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "飞书统计群成员消息数", "user_name_cache.json")

with open(cache_file, 'r', encoding='utf-8') as f:
    cache = json.load(f)

print("=" * 80)
print("🔍 检查未知用户是否在缓存中")
print("=" * 80)

for i, user_id in enumerate(unknown_users, 1):
    if user_id in cache:
        print(f"\n{i}. ✅ 找到: {cache[user_id].get('name')}")
        print(f"   用户ID: {user_id}")
        print(f"   来源群: {cache[user_id].get('source_group')}")
    else:
        print(f"\n{i}. ❌ 未找到")
        print(f"   用户ID: {user_id}")

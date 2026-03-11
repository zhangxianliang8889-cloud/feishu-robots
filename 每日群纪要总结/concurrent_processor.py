#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
高效并发处理器 - 马斯克式第一性原理设计
实现多群并发处理，最大化效率
"""

import asyncio
import aiohttp
import time
from typing import List, Dict, Any, Optional
from datetime import datetime
import json

class ConcurrentProcessor:
    """并发处理器 - 同时处理多个群"""
    
    def __init__(self, max_concurrent_groups: int = 5, max_concurrent_ai: int = 3):
        """
        初始化并发处理器
        
        Args:
            max_concurrent_groups: 最大并发群数
            max_concurrent_ai: 最大并发AI调用数
        """
        self.max_concurrent_groups = max_concurrent_groups
        self.max_concurrent_ai = max_concurrent_ai
        self.semaphore_groups = asyncio.Semaphore(max_concurrent_groups)
        self.semaphore_ai = asyncio.Semaphore(max_concurrent_ai)
        self.results = []
        self.errors = []
    
    async def process_group(self, group_info: Dict, processor_func, *args) -> Dict:
        """
        处理单个群（带信号量控制）
        
        Args:
            group_info: 群信息
            processor_func: 处理函数
            *args: 额外参数
        
        Returns:
            Dict: 处理结果
        """
        async with self.semaphore_groups:
            start_time = time.time()
            try:
                result = await processor_func(group_info, *args)
                elapsed = time.time() - start_time
                return {
                    "group": group_info.get("chat_name", "unknown"),
                    "success": True,
                    "elapsed": elapsed,
                    "result": result
                }
            except Exception as e:
                elapsed = time.time() - start_time
                return {
                    "group": group_info.get("chat_name", "unknown"),
                    "success": False,
                    "elapsed": elapsed,
                    "error": str(e)
                }
    
    async def process_all_groups(self, groups: List[Dict], processor_func, *args) -> List[Dict]:
        """
        并发处理所有群
        
        Args:
            groups: 群列表
            processor_func: 处理函数
            *args: 额外参数
        
        Returns:
            List[Dict]: 所有群的处理结果
        """
        start_time = time.time()
        
        tasks = [
            self.process_group(group, processor_func, *args)
            for group in groups
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        elapsed = time.time() - start_time
        
        success_count = sum(1 for r in results if isinstance(r, dict) and r.get("success"))
        error_count = len(results) - success_count
        
        print(f"\n{'='*60}")
        print(f"📊 并发处理完成")
        print(f"{'='*60}")
        print(f"✅ 成功: {success_count}/{len(groups)}")
        print(f"❌ 失败: {error_count}/{len(groups)}")
        print(f"⏱️ 总耗时: {elapsed:.1f}秒")
        print(f"⚡ 平均每群: {elapsed/len(groups):.1f}秒")
        print(f"{'='*60}\n")
        
        return results

class AIRequestBatcher:
    """AI请求批处理器 - 减少API调用次数"""
    
    def __init__(self, batch_size: int = 5, batch_timeout: float = 2.0):
        """
        初始化批处理器
        
        Args:
            batch_size: 批次大小
            batch_timeout: 批次超时时间（秒）
        """
        self.batch_size = batch_size
        self.batch_timeout = batch_timeout
        self.pending_requests = []
        self.results_cache = {}
    
    async def add_request(self, request_id: str, messages: List[str], processor_func) -> Any:
        """
        添加请求到批次
        
        Args:
            request_id: 请求ID
            messages: 消息列表
            processor_func: 处理函数
        
        Returns:
            Any: 处理结果
        """
        self.pending_requests.append({
            "id": request_id,
            "messages": messages,
            "processor": processor_func
        })
        
        if len(self.pending_requests) >= self.batch_size:
            return await self._process_batch()
        
        return None
    
    async def _process_batch(self) -> List[Any]:
        """处理当前批次"""
        if not self.pending_requests:
            return []
        
        batch = self.pending_requests[:self.batch_size]
        self.pending_requests = self.pending_requests[self.batch_size:]
        
        tasks = [
            req["processor"](req["messages"])
            for req in batch
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for req, result in zip(batch, results):
            self.results_cache[req["id"]] = result
        
        return results

class TokenCache:
    """Token缓存器 - 减少Token获取次数"""
    
    def __init__(self, cache_duration: int = 7000):
        """
        初始化Token缓存
        
        Args:
            cache_duration: 缓存时长（秒），默认7000秒（约2小时）
        """
        self.cache_duration = cache_duration
        self.token_cache = {}
    
    def get_token(self, app_id: str, app_secret: str, token_getter) -> str:
        """
        获取Token（带缓存）
        
        Args:
            app_id: 应用ID
            app_secret: 应用密钥
            token_getter: Token获取函数
        
        Returns:
            str: Token
        """
        cache_key = f"{app_id}_{app_secret}"
        
        if cache_key in self.token_cache:
            cached = self.token_cache[cache_key]
            if time.time() - cached["timestamp"] < self.cache_duration:
                print("✅ 使用缓存的Token")
                return cached["token"]
        
        token = token_getter(app_id, app_secret)
        
        if token:
            self.token_cache[cache_key] = {
                "token": token,
                "timestamp": time.time()
            }
        
        return token
    
    def clear_cache(self):
        """清除缓存"""
        self.token_cache = {}

class PerformanceMonitor:
    """性能监控器 - 监控各环节耗时"""
    
    def __init__(self):
        self.metrics = {}
    
    def start_timer(self, name: str):
        """开始计时"""
        if name not in self.metrics:
            self.metrics[name] = {"times": [], "total": 0}
        self.metrics[name]["start"] = time.time()
    
    def end_timer(self, name: str):
        """结束计时"""
        if name in self.metrics and "start" in self.metrics[name]:
            elapsed = time.time() - self.metrics[name]["start"]
            self.metrics[name]["times"].append(elapsed)
            self.metrics[name]["total"] += elapsed
            del self.metrics[name]["start"]
            return elapsed
        return 0
    
    def get_report(self) -> str:
        """获取性能报告"""
        report_lines = ["\n📊 性能报告", "=" * 40]
        
        for name, data in self.metrics.items():
            if data["times"]:
                avg = data["total"] / len(data["times"])
                report_lines.append(
                    f"{name}: 平均 {avg:.2f}s, 总计 {data['total']:.2f}s, 次数 {len(data['times'])}"
                )
        
        return "\n".join(report_lines)

def run_concurrent_tasks(tasks: List, max_workers: int = 5):
    """
    运行并发任务（同步版本）
    
    Args:
        tasks: 任务列表
        max_workers: 最大并发数
    
    Returns:
        List: 结果列表
    """
    from concurrent.futures import ThreadPoolExecutor, as_completed
    
    results = []
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(task): i for i, task in enumerate(tasks)}
        
        for future in as_completed(futures):
            try:
                result = future.result()
                results.append((futures[future], result))
            except Exception as e:
                results.append((futures[future], {"error": str(e)}))
    
    results.sort(key=lambda x: x[0])
    return [r[1] for r in results]

if __name__ == "__main__":
    print("🚀 高效并发处理器")
    print("=" * 60)
    
    print("\n功能特性：")
    print("1. 多群并发处理 - 同时处理多个群")
    print("2. AI请求批处理 - 减少API调用次数")
    print("3. Token缓存 - 减少Token获取次数")
    print("4. 性能监控 - 实时监控各环节耗时")
    
    print("\n使用示例：")
    print("""
# 创建并发处理器
processor = ConcurrentProcessor(max_concurrent_groups=5)

# 并发处理所有群
results = await processor.process_all_groups(groups, process_group_func)

# 查看性能报告
monitor = PerformanceMonitor()
monitor.start_timer("ai_summarize")
# ... 执行任务 ...
monitor.end_timer("ai_summarize")
print(monitor.get_report())
    """)

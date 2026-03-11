#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
统一接口层 - 确保所有函数返回值格式一致
防止因返回值类型变化导致的调用错误
"""

from typing import Dict, Any, Union, Optional

def extract_summary_content(summary_result: Union[Dict, str, None]) -> Dict[str, Any]:
    """
    统一提取总结内容，处理多种返回值格式
    
    Args:
        summary_result: local_summarize 或 generate_xxx_summary 的返回值
            - Dict: {"success": bool, "content": str, "ai_used": bool}
            - str: 直接返回的字符串
            - None: 空值
    
    Returns:
        Dict: {
            "success": bool,
            "content": str,
            "ai_used": bool,
            "error": str (可选)
        }
    """
    if summary_result is None:
        return {
            "success": False,
            "content": "",
            "ai_used": False,
            "error": "返回值为空"
        }
    
    if isinstance(summary_result, dict):
        success = summary_result.get("success", True)
        content = summary_result.get("content", "")
        ai_used = summary_result.get("ai_used", False)
        
        if not content:
            return {
                "success": False,
                "content": "",
                "ai_used": False,
                "error": "内容为空"
            }
        
        return {
            "success": success,
            "content": content,
            "ai_used": ai_used
        }
    
    if isinstance(summary_result, str):
        if not summary_result or len(summary_result) < 10:
            return {
                "success": False,
                "content": "",
                "ai_used": False,
                "error": "内容过短或为空"
            }
        
        return {
            "success": True,
            "content": summary_result,
            "ai_used": False
        }
    
    return {
        "success": False,
        "content": str(summary_result),
        "ai_used": False,
        "error": f"未知的返回值类型: {type(summary_result)}"
    }

def is_valid_summary(summary_result: Union[Dict, str, None], min_length: int = 50) -> bool:
    """
    检查总结是否有效
    
    Args:
        summary_result: 总结结果
        min_length: 最小长度要求
    
    Returns:
        bool: 是否有效
    """
    extracted = extract_summary_content(summary_result)
    return extracted["success"] and len(extracted["content"]) >= min_length

def get_summary_text(summary_result: Union[Dict, str, None]) -> str:
    """
    获取总结文本（简化版）
    
    Args:
        summary_result: 总结结果
    
    Returns:
        str: 总结文本，失败返回空字符串
    """
    extracted = extract_summary_content(summary_result)
    return extracted["content"] if extracted["success"] else ""

if __name__ == "__main__":
    print("🧪 测试统一接口层")
    print("=" * 60)
    
    test_cases = [
        {"success": True, "content": "这是测试内容", "ai_used": True},
        {"success": False, "content": "", "ai_used": False},
        "直接字符串返回",
        "",
        None,
        {"content": "缺少success字段"},
    ]
    
    for i, case in enumerate(test_cases, 1):
        print(f"\n测试 {i}: {type(case).__name__}")
        result = extract_summary_content(case)
        print(f"  success: {result['success']}")
        print(f"  content: {result['content'][:30]}..." if result['content'] else "  content: (空)")
        print(f"  ai_used: {result['ai_used']}")
        if 'error' in result:
            print(f"  error: {result['error']}")

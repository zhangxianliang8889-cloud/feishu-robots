# 统一测试指南

## 📋 测试文件说明

### 主要测试文件
- `test_ai_summary.py` - 测试AI总结功能（使用示例消息）
- `test_send_to_test_group.py` - 测试从真实群获取消息并发送到测试群
- `test_meeting_bot.py` - 测试群会议纪要机器人的日报/周报/月报
- `test_statistics_bot.py` - 测试群消息统计机器人的日报/周报/月报

### 其他测试文件（待清理）
- `test_daily_report.py` - 测试日报（功能重复）
- `test_chuhuaerbu.py` - 测试策划二部（特定群测试）
- `test_all_formats.py` - 测试所有格式（功能重复）
- `test_mobile.py` - 测试移动端（特定功能测试）
- `test_send.py` - 测试发送（功能重复）

## 🔧 高并发处理

### 已集成到主程序
主程序`群会议纪要_最终版.py`已经集成了高并发处理：
- 导入了`ConcurrentProcessor`
- 使用`run_concurrent_tasks`进行并发处理
- 最大并发数：5个群

### 并发处理器特性
1. 多群并发处理 - 同时处理多个群
2. AI请求批处理 - 减少API调用次数
3. Token缓存 - 减少Token获取次数
4. 性能监控 - 实时监控各环节耗时

## 📦 文件同步检查清单

### 需要同步到服务器的文件
1. ✅ `群会议纪要_最终版.py` - 主程序（已集成高并发）
2. ✅ `concurrent_processor.py` - 并发处理器
3. ✅ `ai_summarizer.py` - AI总结模块
4. ✅ `config.py` - 配置文件
5. ✅ `enhanced_api_client.py` - 增强API客户端
6. ✅ `incremental_fetcher.py` - 增量获取器
7. ✅ `task_state_manager.py` - 任务状态管理器
8. ✅ `unified_summarizer.py` - 统一总结器
9. ✅ `unified_config.py` - 统一配置
10. ✅ `unified_interface.py` - 统一接口

### 测试文件（可选同步）
- `test_ai_summary.py` - AI总结测试
- `test_send_to_test_group.py` - 发送测试
- `test_meeting_bot.py` - 会议纪要机器人测试
- `test_statistics_bot.py` - 消息统计机器人测试

### 待清理的测试文件
- `test_daily_report.py` - 功能重复，建议删除
- `test_chuhuaerbu.py` - 特定群测试，建议删除
- `test_all_formats.py` - 功能重复，建议删除
- `test_mobile.py` - 特定功能测试，建议删除
- `test_send.py` - 功能重复，建议删除

## 🎯 测试命令

### 测试AI总结功能
```bash
python3 test_ai_summary.py
```

### 测试从真实群获取消息
```bash
python3 test_send_to_test_group.py
```

### 测试群会议纪要机器人
```bash
python3 test_meeting_bot.py
```

### 测试群消息统计机器人
```bash
python3 test_statistics_bot.py
```

## 📊 主程序功能检查

### 高并发处理
- ✅ 已集成到主程序
- ✅ 使用`run_concurrent_tasks`进行并发处理
- ✅ 最大并发数：5个群

### AI总结功能
- ✅ 使用豆包API
- ✅ 支持日报、周报、月报
- ✅ 智能提取核心话题
- ✅ 识别完成事项和待办事项
- ✅ 生成关键洞察

### 消息统计功能
- ✅ 统计消息总数
- ✅ 统计参与人数
- ✅ 统计消息类型
- ✅ 统计活跃用户
- ✅ 统计活跃时间段

## 🔍 问题排查

### 问题1：为什么创建了多个测试文件？
**原因**：在测试过程中，为了验证不同功能，创建了多个测试文件，导致功能重复。

**解决方案**：保留主要测试文件，删除重复的测试文件。

### 问题2：高并发处理的修改在哪里？
**位置**：主程序`群会议纪要_最终版.py`第68行和第1703行。

**说明**：已经集成了高并发处理，使用`run_concurrent_tasks`函数进行并发处理。

### 问题3：文件同步问题？
**解决方案**：创建统一的同步脚本，确保所有文件正确同步到服务器。

## 📝 下一步行动

1. 清理重复的测试文件
2. 创建统一的同步脚本
3. 确保所有文件正确同步到服务器
4. 验证服务器上的文件完整性

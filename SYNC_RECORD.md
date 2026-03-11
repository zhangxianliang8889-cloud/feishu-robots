# 代码同步记录

**同步时间**：2026-03-08 03:50:00  
**同步方向**：双向同步（本地 ↔ 服务器）  
**服务器**：root@115.191.47.166

---

## 一、同步内容

### 1.1 本地 → 服务器

#### 群会议纪要机器人 (meeting_summary)
| 文件 | 大小 | 状态 |
|-----|------|------|
| 群会议纪要_最终版.py | 75KB | ✅ 已同步 |
| ai_summarizer.py | 7.8KB | ✅ 已同步 |
| config.py | 1.5KB | ✅ 已同步 |
| concurrent_processor.py | 9.1KB | ✅ 已同步 |
| enhanced_api_client.py | 13KB | ✅ 已同步 |
| incremental_fetcher.py | 13KB | ✅ 已同步 |
| task_state_manager.py | 12KB | ✅ 已同步 |
| send_check_system.py | 9.9KB | ✅ 已同步 |
| smart_summarizer.py | 7.0KB | ✅ 已同步 |
| unified_summarizer.py | 6.5KB | ✅ 已同步 |
| unified_config.py | 11KB | ✅ 已同步 |
| test_*.py (5个测试文件) | - | ✅ 已同步 |
| *.md (4个文档文件) | - | ✅ 已同步 |
| sync_to_server.sh | 2.7KB | ✅ 已同步 |

#### 群消息统计机器人 (message_stats)
| 文件 | 大小 | 状态 |
|-----|------|------|
| 多群统计.py | 43KB | ✅ 已同步 |
| config.py | 1.7KB | ✅ 已同步 |
| user_name_cache.py | 5.2KB | ✅ 已同步 |
| enhanced_api_client.py | 13KB | ✅ 已同步 |
| incremental_fetcher.py | 13KB | ✅ 已同步 |
| task_state_manager.py | 12KB | ✅ 已同步 |
| send_check_system.py | 9.9KB | ✅ 已同步 |
| unified_config.py | 11KB | ✅ 已同步 |
| user_name_cache.json | 16KB | ✅ 已同步 |
| send_records.json | 3.2KB | ✅ 已同步 |
| sync_to_server.sh | 1.4KB | ✅ 已同步 |

### 1.2 服务器 → 本地

| 文件 | 来源 | 状态 |
|-----|------|------|
| server_send_records.json | meeting_summary | ✅ 已拉取 |
| server_send_records.json | message_stats | ✅ 已拉取 |
| server_user_name_cache.json | message_stats | ✅ 已拉取 |

---

## 二、代码完整性验证

### MD5校验结果

| 文件 | 本地MD5 | 服务器MD5 | 状态 |
|-----|---------|----------|------|
| 群会议纪要_最终版.py | d0ddab760873cfa2586f5d5ffb78c061 | d0ddab760873cfa2586f5d5ffb78c061 | ✅ 一致 |
| 多群统计.py | 66ba3655ff0c0dee01621223c3b3049d | 66ba3655ff0c0dee01621223c3b3049d | ✅ 一致 |

---

## 三、本次同步的主要变更

### 3.1 群会议纪要机器人

| 变更项 | 描述 |
|-------|------|
| 标题重复修复 | 删除发送时的重复标题，只使用ai_summary中的标题 |
| 删除"本周疑问"板块 | 不再显示疑问板块 |
| 新增"AI建议与洞察" | 替代原来的"建议与想法"，使用AI智能生成 |
| UTF-8编码修复 | 添加stdout/stderr的UTF-8编码设置 |

### 3.2 群消息统计机器人

| 变更项 | 描述 |
|-------|------|
| UTF-8编码修复 | 添加stdout/stderr的UTF-8编码设置 |
| 用户ID解析优化 | 支持open_id、user_id、union_id多种类型 |
| 报告格式优化 | 横线分隔符长度适中，不会换行 |

---

## 四、双向同步机制

### 4.1 同步流程

```
┌─────────────────┐                    ┌─────────────────┐
│   本地开发环境   │                    │   服务器环境     │
├─────────────────┤                    ├─────────────────┤
│                 │   scp *.py *.json  │                 │
│   源代码文件    │ ─────────────────→ │   源代码文件    │
│                 │                    │                 │
│                 │   scp 数据文件     │                 │
│   数据备份      │ ←───────────────── │   运行时数据    │
│                 │                    │                 │
└─────────────────┘                    └─────────────────┘
```

### 4.2 同步命令

**本地 → 服务器**：
```bash
# 群会议纪要
cd /Users/yueguangbaohe/Documents/trae_projects/pi_digits/每日群纪要总结
scp *.py *.json *.md *.sh root@115.191.47.166:/root/feishu-bots/meeting_summary/

# 群消息统计
cd /Users/yueguangbaohe/Documents/trae_projects/pi_digits/飞书统计群成员消息数
scp *.py *.json *.sh root@115.191.47.166:/root/feishu-bots/message_stats/
```

**服务器 → 本地**：
```bash
# 拉取运行时数据
scp root@115.191.47.166:/root/feishu-bots/meeting_summary/send_records.json ./server_send_records.json
scp root@115.191.47.166:/root/feishu-bots/message_stats/send_records.json ./server_send_records.json
scp root@115.191.47.166:/root/feishu-bots/message_stats/user_name_cache.json ./server_user_name_cache.json
```

---

## 五、服务器路径映射

| 本地路径 | 服务器路径 |
|---------|-----------|
| `/Users/yueguangbaohe/Documents/trae_projects/pi_digits/每日群纪要总结/` | `/root/feishu-bots/meeting_summary/` |
| `/Users/yueguangbaohe/Documents/trae_projects/pi_digits/飞书统计群成员消息数/` | `/root/feishu-bots/message_stats/` |

---

## 六、验证结果

- ✅ 所有Python文件同步成功
- ✅ 所有配置文件同步成功
- ✅ MD5校验通过，代码完整性确认
- ✅ 运行时数据已备份到本地
- ✅ 双向同步机制建立完成

---

**同步完成时间**：2026-03-08 03:50  
**同步状态**：✅ 成功

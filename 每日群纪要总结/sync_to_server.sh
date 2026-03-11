#!/bin/bash
# 同步文件到服务器

echo "🚀 开始同步文件到服务器..."

# 服务器配置
SERVER_USER="root"
SERVER_HOST="115.191.47.166"
SERVER_PATH="/root/feishu-bots/每日群纪要总结"

# 需要同步的核心文件
CORE_FILES=(
    "群会议纪要_最终版.py"
    "concurrent_processor.py"
    "ai_summarizer.py"
    "config.py"
    "enhanced_api_client.py"
    "incremental_fetcher.py"
    "task_state_manager.py"
    "unified_summarizer.py"
    "unified_config.py"
    "unified_interface.py"
    "daemon_manager.py"
    "start_daemon.py"
    "send_check_system.py"
)

# 需要同步的测试文件
TEST_FILES=(
    "test_ai_summary.py"
    "test_send_to_test_group.py"
    "test_meeting_bot.py"
    "test_statistics_bot.py"
)

# 其他文件
OTHER_FILES=(
    "get_groups.py"
    "show_formats.py"
    "smart_summarizer.py"
)

echo "📦 同步核心文件..."
for file in "${CORE_FILES[@]}"; do
    if [ -f "$file" ]; then
        echo "  ✅ $file"
        rsync -avz "$file" "${SERVER_USER}@${SERVER_HOST}:${SERVER_PATH}/"
    else
        echo "  ❌ $file 不存在"
    fi
done

echo "📦 同步测试文件..."
for file in "${TEST_FILES[@]}"; do
    if [ -f "$file" ]; then
        echo "  ✅ $file"
        rsync -avz "$file" "${SERVER_USER}@${SERVER_HOST}:${SERVER_PATH}/"
    else
        echo "  ❌ $file 不存在"
    fi
done

echo "📦 同步其他文件..."
for file in "${OTHER_FILES[@]}"; do
    if [ -f "$file" ]; then
        echo "  ✅ $file"
        rsync -avz "$file" "${SERVER_USER}@${SERVER_HOST}:${SERVER_PATH}/"
    else
        echo "  ❌ $file 不存在"
    fi
done

echo "📦 同步配置文件..."
if [ -f "config.py" ]; then
    echo "  ✅ config.py"
    rsync -avz "config.py" "${SERVER_USER}@${SERVER_HOST}:${SERVER_PATH}/"
else
    echo "  ❌ config.py 不存在"
fi

echo "📦 同步数据文件..."
if [ -f "send_records.json" ]; then
    echo "  ✅ send_records.json"
    rsync -avz "send_records.json" "${SERVER_USER}@${SERVER_HOST}:${SERVER_PATH}/"
else
    echo "  ⚠️  send_records.json 不存在（首次运行时会自动创建）"
fi

echo "📦 同步文档文件..."
if [ -f "UNIFIED_TEST_GUIDE.md" ]; then
    echo "  ✅ UNIFIED_TEST_GUIDE.md"
    rsync -avz "UNIFIED_TEST_GUIDE.md" "${SERVER_USER}@${SERVER_HOST}:${SERVER_PATH}/"
else
    echo "  ❌ UNIFIED_TEST_GUIDE.md 不存在"
fi

echo ""
echo "🎉 同步完成！"
echo ""
echo "📝 注意事项："
echo "1. 请修改脚本中的服务器配置（SERVER_USER、SERVER_HOST、SERVER_PATH）"
echo "2. 取消注释 rsync 命令以实际执行同步"
echo "3. 首次同步前请确保服务器目录存在"
echo "4. 同步后请在服务器上重启相关服务"

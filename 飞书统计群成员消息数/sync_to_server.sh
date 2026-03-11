#!/bin/bash
# 同步文件到服务器

echo "🚀 开始同步文件到服务器..."

SERVER_USER="root"
SERVER_HOST="115.191.47.166"
SERVER_PATH="/root/feishu-bots/飞书统计群成员消息数"

CORE_FILES=(
    "多群统计.py"
    "config.py"
    "user_name_cache.py"
    "enhanced_api_client.py"
    "incremental_fetcher.py"
    "task_state_manager.py"
    "send_check_system.py"
    "unified_config.py"
)

TEST_FILES=(
    "test_statistics_bot.py"
)

echo "📦 同步核心文件..."
for file in "${CORE_FILES[@]}"; do
    if [ -f "$file" ]; then
        echo "  ✅ $file"
    else
        echo "  ❌ $file 不存在"
    fi
done

echo "📦 同步测试文件..."
for file in "${TEST_FILES[@]}"; do
    if [ -f "$file" ]; then
        echo "  ✅ $file"
    else
        echo "  ❌ $file 不存在"
    fi
done

echo "📦 同步配置文件..."
if [ -f "config.py" ]; then
    echo "  ✅ config.py"
fi

echo "📦 同步数据文件..."
if [ -f "send_records.json" ]; then
    echo "  ✅ send_records.json"
fi

echo ""
echo "🎉 同步完成！"
echo ""
echo "📝 注意事项："
echo "1. 请修改脚本中的服务器配置（SERVER_USER、SERVER_HOST、SERVER_PATH）"
echo "2. 取消注释 rsync 命令以实际执行同步"
echo "3. 首次同步前请确保服务器目录存在"
echo "4. 同步后请在服务器上重启相关服务"

#!/bin/bash
# 阿里云服务器启动脚本

cd /root/feishu_bots

echo "============================================================"
echo "🚀 启动飞书机器人"
echo "============================================================"

# 安装screen
if ! command -v screen &> /dev/null; then
    echo "📦 安装screen..."
    yum install screen -y 2>/dev/null || apt install screen -y 2>/dev/null
    echo "✅ screen安装完成"
fi

echo "✅ 环境准备完成"

# 停止旧的screen会话
screen -S bots -X quit 2>/dev/null

# 等待一下
sleep 1

# 创建screen会话并运行
screen -dmS bots bash -c "cd /root/feishu_bots/群会议纪要机器人 && python3 start_daemon.py"

echo "✅ 机器人已在后台运行"
echo ""
echo "查看运行状态:"
echo "  screen -r bots"
echo ""
echo "查看日志:"
echo "  tail -f /root/feishu_bots/群会议纪要机器人/logs/*.log"
echo ""
echo "退出screen会话（保持程序运行）:"
echo "  按 Ctrl+A+D"

#!/bin/bash
# 阿里云服务器部署脚本（手动执行版）

HOST="47.100.10.100"
USERNAME="xuankong"
PASSWORD="xkxx@2021"
LOCAL_DIR="/Users/yueguangbaohe/Documents/trae_projects/pi_digits"
REMOTE_DIR="/root/feishu_bots"

echo "============================================================"
echo "🚀 阿里云服务器部署脚本"
echo "============================================================"
echo ""
echo "📋 服务器信息:"
echo "   • IP: $HOST"
echo "   • 用户: $USERNAME"
echo "   • 本地目录: $LOCAL_DIR"
echo "   • 远程目录: $REMOTE_DIR"
echo ""

echo "📤 步骤1: 上传代码到服务器..."
echo "   请输入密码: $PASSWORD"
echo ""

scp -r "$LOCAL_DIR" "$USERNAME@$HOST:$REMOTE_DIR"

if [ $? -eq 0 ]; then
    echo "✅ 代码上传成功"
else
    echo "❌ 代码上传失败"
    exit 1
fi

echo ""
echo "============================================================"
echo "✅ 部署完成！"
echo "============================================================"
echo ""
echo "📋 接下来请在服务器上执行以下命令："
echo ""
echo "1. 连接服务器:"
echo "   ssh $USERNAME@$HOST"
echo ""
echo "2. 安装依赖:"
echo "   cd $REMOTE_DIR"
echo "   pip3 install requests schedule paramiko"
echo ""
echo "3. 安装screen:"
echo "   yum install screen -y"
echo ""
echo "4. 启动机器人:"
echo "   cd $REMOTE_DIR/群会议纪要机器人"
echo "   screen -dmS bots bash -c 'python3 start_daemon.py'"
echo ""
echo "5. 查看运行状态:"
echo "   screen -r bots"
echo "   按 Ctrl+A+D 退出会话"
echo ""
echo "6. 查看日志:"
echo "   tail -f $REMOTE_DIR/群会议纪要机器人/logs/*.log"
echo ""
echo "🎉 部署完成！"

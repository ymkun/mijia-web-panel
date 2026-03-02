#!/bin/bash
"""
启动米家控制面板并在60秒后自动关闭
"""

APP_PATH="$(dirname "$0")/dist/米家控制面板.app"

if [ ! -d "$APP_PATH" ]; then
    echo "错误: 找不到应用 $APP_PATH"
    exit 1
fi

echo "启动米家控制面板..."
echo "60秒后将自动关闭"
open "$APP_PATH"

echo "等待60秒..."
sleep 60

echo "正在关闭米家控制面板..."

# 查找并杀死米家控制面板进程
PID=$(ps aux | grep -i "米家控制面板" | grep -v grep | grep -v bash | head -1 | awk '{print $2}')

if [ -n "$PID" ]; then
    echo "找到进程 $PID，正在关闭..."
    kill -9 "$PID"
    echo "已关闭米家控制面板"
else
    echo "未找到米家控制面板进程"
fi

echo "操作完成"

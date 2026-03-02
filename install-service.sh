#!/bin/bash
# 米家控制面板 - 开机自启动安装脚本

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PLIST_SOURCE="$SCRIPT_DIR/com.mijia.panel.plist"
PLIST_DEST="$HOME/Library/LaunchAgents/com.mijia.panel.plist"

echo "=== 米家控制面板 - 开机自启动安装 ==="
echo ""

# 检查 plist 文件是否存在
if [ ! -f "$PLIST_SOURCE" ]; then
    echo "错误: 找不到 com.mijia.panel.plist"
    exit 1
fi

# 更新 plist 中的路径
sed -i '' "s|/Users/mingkun/claude_project/mijia-panel|$SCRIPT_DIR|g" "$PLIST_SOURCE"

# 停止并卸载旧服务（如果存在）
if [ -f "$PLIST_DEST" ]; then
    echo "停止旧服务..."
    launchctl unload "$PLIST_DEST" 2>/dev/null
fi

# 复制 plist 到 LaunchAgents
echo "安装 LaunchAgent..."
cp "$PLIST_SOURCE" "$PLIST_DEST"

# 加载服务
echo "启动服务..."
launchctl load "$PLIST_DEST"

echo ""
echo "=== 安装完成 ==="
echo "服务已启动，访问 http://localhost:5001"
echo ""
echo "常用命令:"
echo "  查看状态: launchctl list | grep mijia"
echo "  停止服务: launchctl unload $PLIST_DEST"
echo "  启动服务: launchctl load $PLIST_DEST"
echo "  查看日志: tail -f /tmp/mijia-panel.log"

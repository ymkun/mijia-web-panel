#!/bin/bash
# 米家控制面板 - 卸载开机自启动

PLIST_DEST="$HOME/Library/LaunchAgents/com.mijia.panel.plist"

echo "=== 米家控制面板 - 卸载开机自启动 ==="
echo ""

if [ -f "$PLIST_DEST" ]; then
    echo "停止服务..."
    launchctl unload "$PLIST_DEST" 2>/dev/null
    
    echo "删除 LaunchAgent..."
    rm "$PLIST_DEST"
    
    echo "卸载完成"
else
    echo "服务未安装"
fi

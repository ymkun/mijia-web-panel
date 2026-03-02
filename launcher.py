#!/usr/bin/env python3
"""
米家控制面板启动器
自动启动服务并打开浏览器
"""
import subprocess
import sys
import time
import webbrowser
import os
from pathlib import Path

def get_script_dir():
    if getattr(sys, 'frozen', False):
        return Path(sys._MEIPASS)
    return Path(__file__).parent.absolute()

def main():
    script_dir = get_script_dir()
    app_py = script_dir / "app.py"
    
    if not app_py.exists():
        print(f"错误: 找不到 app.py")
        print(f"当前目录: {script_dir}")
        input("按回车键退出...")
        return
    
    print("=" * 50)
    print("  米家控制面板")
    print("=" * 50)
    print()
    print("正在启动服务...")
    print("访问地址: http://localhost:5001")
    print()
    print("按 Ctrl+C 停止服务")
    print()
    
    def open_browser():
        time.sleep(1.5)
        webbrowser.open('http://localhost:5001')
    
    import threading
    threading.Thread(target=open_browser, daemon=True).start()
    
    os.chdir(script_dir)
    subprocess.run([sys.executable, "app.py"])

if __name__ == "__main__":
    main()

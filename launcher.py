#!/usr/bin/env python3
"""
米家控制面板启动器
自动启动服务并打开 Edge PWA 应用
"""
import sys
import time
import os
import subprocess
from pathlib import Path

def get_script_dir():
    if getattr(sys, 'frozen', False):
        return Path(sys._MEIPASS)
    return Path(__file__).parent.absolute()

def get_pwa_app_path():
    """获取 Edge PWA 应用路径"""
    home = Path.home()
    pwa_path = home / "Applications" / "Edge Apps.localized" / "米家控制面板.app"
    if pwa_path.exists():
        return pwa_path
    
    # 备选路径
    alt_paths = [
        home / "Applications" / "Edge Apps" / "米家控制面板.app",
        home / "Applications" / "米家控制面板.app",
    ]
    for p in alt_paths:
        if p.exists():
            return p
    
    return None

def open_pwa_app():
    """打开 Edge PWA 应用或回退到浏览器"""
    pwa_app = get_pwa_app_path()
    
    if pwa_app:
        print(f"正在打开 PWA 应用: {pwa_app}")
        subprocess.run(["open", str(pwa_app)])
    else:
        print("未找到 PWA 应用，使用默认浏览器")
        import webbrowser
        webbrowser.open('http://localhost:5001')

def main():
    script_dir = get_script_dir()
    app_py = script_dir / "app.py"
    
    print("=" * 50)
    print("  米家控制面板")
    print("=" * 50)
    print()
    
    if not app_py.exists():
        print(f"错误: 找不到 app.py")
        print(f"脚本目录: {script_dir}")
        input("按回车键退出...")
        return
    
    print("正在启动服务...")
    print("访问地址: http://localhost:5001")
    print()
    print("关闭此窗口即可停止服务")
    print()
    
    def open_app():
        time.sleep(2)
        open_pwa_app()
    
    import threading
    threading.Thread(target=open_app, daemon=True).start()
    
    os.chdir(script_dir)
    
    # 直接导入并运行 app.py
    sys.path.insert(0, str(script_dir))
    import app
    app.main()

if __name__ == "__main__":
    main()

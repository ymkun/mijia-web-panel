#!/usr/bin/env python3
"""
米家控制面板 - 后台服务模式
不自动打开浏览器，仅启动 HTTP 服务
"""
import sys
import os
from pathlib import Path

def get_script_dir():
    if getattr(sys, 'frozen', False):
        return Path(sys._MEIPASS)
    return Path(__file__).parent.absolute()

def main():
    script_dir = get_script_dir()
    app_py = script_dir / "app.py"
    
    os.chdir(script_dir)
    sys.path.insert(0, str(script_dir))
    
    import app
    app.main()

if __name__ == "__main__":
    main()

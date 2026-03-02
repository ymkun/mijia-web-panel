#!/usr/bin/env python3
"""
米家控制面板 - PyInstaller 打包脚本
使用方法:
    pip install pyinstaller
    python build_app.py
"""
import subprocess
import sys
import shutil
from pathlib import Path

def main():
    project_dir = Path(__file__).parent
    
    print("开始打包米家控制面板...")
    
    cmd = [
        sys.executable, '-m', 'PyInstaller',
        '--name=米家控制面板',
        '--onedir',
        '--windowed',
        '--add-data=templates:templates',
        '--add-data=app.py:.',
        '--add-data=service.py:.',
        '--add-data=token_extractor.py:.',
        '--hidden-import=flask',
        '--hidden-import=miio',
        '--hidden-import=miio.device',
        '--hidden-import=miio.miioprotocol',
        '--hidden-import=requests',
        '--hidden-import=Crypto',
        '--hidden-import=Crypto.Cipher',
        '--hidden-import=Crypto.Cipher.AES',
        '--hidden-import=PIL',
        '--hidden-import=charset_normalizer',
        '--hidden-import=colorama',
        '--noconfirm',
        'launcher.py'
    ]
    
    subprocess.run(cmd, cwd=project_dir)
    
    print()
    print("=" * 50)
    print("打包完成!")
    print(f"应用位置: {project_dir / 'dist' / '米家控制面板.app'}")
    print("=" * 50)

if __name__ == "__main__":
    main()

"""
py2app setup script for 米家控制面板
使用方法:
    python setup.py py2app
"""
from setuptools import setup

APP = ['app.py']
DATA_FILES = [
    ('templates', ['templates/index.html', 'templates/manage.html']),
]
OPTIONS = {
    'argv_emulation': False,
    'packages': ['flask', 'miio', 'requests', 'Crypto', 'PIL', 'charset_normalizer', 'colorama'],
    'includes': [
        'flask',
        'miio',
        'miio.device',
        'miio.miioprotocol',
        'miio.discovery',
        'requests',
        'Crypto',
        'Crypto.Cipher',
        'Crypto.Cipher.AES',
        'PIL',
        'PIL.Image',
        'charset_normalizer',
        'colorama',
    ],
    'excludes': [
        'tkinter',
        'matplotlib',
        'numpy',
        'pandas',
        'scipy',
        'pytest',
    ],
    'iconfile': None,
    'plist': {
        'CFBundleName': '米家控制面板',
        'CFBundleDisplayName': '米家控制面板',
        'CFBundleIdentifier': 'com.mijia.panel',
        'CFBundleVersion': '1.0.0',
        'CFBundleShortVersionString': '1.0.0',
        'NSHighResolutionCapable': True,
        'LSMinimumSystemVersion': '10.13.0',
        'NSRequiresAquaSystemAppearance': False,
    }
}

setup(
    name='米家控制面板',
    app=APP,
    data_files=DATA_FILES,
    options={'py2app': OPTIONS},
    setup_requires=['py2app'],
)

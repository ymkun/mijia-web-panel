# 米家设备本地 Web 控制面板

在 Mac 浏览器中查看并控制家中所有本地 WiFi 米家设备的轻量 Web 面板。

---

## 目录

- [功能概览](#功能概览)
- [设备列表](#设备列表)
- [获取设备 Token 与 IP](#获取设备-token-与-ip)
- [快速启动](#快速启动)
- [开机自启动](#开机自启动)
- [macOS 应用打包](#macos-应用打包)
- [页面说明](#页面说明)
- [技术说明](#技术说明)
- [常见问题](#常见问题)

---

## 功能概览

| 功能 | 说明 |
|------|------|
| 设备状态查询 | 后台缓存 + 并行查询，页面加载即显示 |
| 开关控制 | 灯光、空调、加湿器、插座、Mesh 开关支持一键开关 |
| 空气质量实时读数 | 页面顶部常驻显示 CO₂、温度、湿度、PM2.5、TVOC |
| 自动刷新 | 后台每 10 秒刷新缓存，前端每 30 秒更新显示 |
| 单设备刷新 | 每个可控设备支持单独刷新按钮 |
| 开机自启动 | 支持 macOS LaunchAgent 开机自动启动服务 |
| macOS 应用打包 | 可打包为独立 .app 应用 |
| 离线可用 | 前端无外部依赖，断网仍可访问局域网设备 |

---

## 设备列表

### WiFi 直连设备

| 设备名称 | IP | 类型 | 可控制 |
|----------|----|------|--------|
| 护眼客厅吸顶灯 | 192.168.3.19 | 灯光 | ✅ |
| 护眼吸顶灯(主卧) | 192.168.3.18 | 灯光 | ✅ |
| 护眼吸顶灯(次卧) | 192.168.3.20 | 灯光 | ✅ |
| 卧室空调 | 192.168.3.27 | 空调 | ✅ |
| 加湿器(卧室) | 192.168.3.110 | 加湿器 | ✅ |
| 加湿器 | 192.168.3.39 | 加湿器 | ✅ |
| 马歇尔音响插座 | 192.168.3.72 | 插座 | ✅ |
| 空气检测仪 | 192.168.3.115 | 传感器 | 只读 |
| 天然气卫士(1) | 192.168.3.32 | 传感器 | 只读 |
| 天然气卫士(2) | 192.168.3.38 | 传感器 | 只读 |
| 小爱-主卧室 | 192.168.3.74 | 音响 | 只读 |
| 小爱-厨房 | 192.168.3.75 | 音响 | 只读 |
| 小爱-客厅 | 192.168.3.58 | 音响 | 只读 |
| 微波炉 | 192.168.3.44 | 家电 | 只读 |
| 破壁机 | 192.168.3.94 | 家电 | 只读 |

### 蓝牙 Mesh 设备（通过网关控制）

| 设备名称 | 网关 | 类型 | 可控制 |
|----------|------|------|--------|
| 客厅灯 | Xiaomi Home Hub | Mesh 开关 | ✅ |
| 餐厅灯 | Xiaomi Home Hub | Mesh 开关 | ✅ |
| 主卧室灯 | Xiaomi Home Hub | Mesh 开关 | ✅ |
| 卫生间灯 | Xiaomi Home Hub | Mesh 开关 | ✅ |
| 筒灯 | Xiaomi Home Hub | Mesh 开关 | ✅ |
| 次卧室开关 | Xiaomi Home Hub | Mesh 开关 | ✅ |
| 床头灯(衣柜) | Xiaomi Home Hub | Mesh 开关 | ✅ |
| 吸顶灯 | Xiaomi Home Hub | Mesh 开关 | ✅ |

> 网关：Xiaomi Home Hub (192.168.3.77)

---

## 获取设备 Token 与 IP

更换路由器、设备重置或添加新设备后，IP 和 Token 可能发生变化，需要重新获取并更新 `app.py` 中的设备列表。

### 工具说明

项目内置了 `token_extractor.py`，通过**小米云端账号**一次性拉取所有设备的 Token、IP、型号等信息，无需 root 手机。

**依赖安装（首次使用）：**

```bash
cd /Users/mingkun/claude_project/mijia-panel
pip3 install requests pycryptodome Pillow colorama --break-system-packages
```

### 使用步骤

**第一步：运行脚本**

```bash
cd /Users/mingkun/claude_project/mijia-panel
python3 token_extractor.py
```

**第二步：输入小米账号**

```
Username (email or phone): 你的小米账号
Password: 你的密码（输入时不显示）
```

> 脚本直接与小米云端通信，账号密码不会被存储或上传至任何第三方。

**第三步：选择服务器**

```
Server (China Mainland / International): China Mainland
```
选择 **China Mainland**（中国大陆账号）。

**第四步：查看输出**

成功后输出类似：

```
Name:     护眼客厅吸顶灯
ID:       826441775
MAC:      84:46:93:D6:E4:54
IP:       192.168.3.19
TOKEN:    ac572d894b94f6ff9152b0d4b83620e8
MODEL:    lipro.light.23x2
---------
Name:     卧室空调
ID:       845466214
IP:       192.168.3.27
TOKEN:    d0f0996992aefabaf404e0b1ccd27e72
MODEL:    xiaomi.airc.r27r00
---------
...
```

- **有 IP 的设备**：WiFi 直连设备，可用于本面板
- **无 IP 的设备**：蓝牙/红外设备，本面板不支持

### 更新设备信息

获取新的 Token/IP 后，编辑 `app.py` 顶部的 `DEVICES` 列表：

```python
DEVICES = [
    {"id": "light_living", "name": "护眼客厅吸顶灯",
     "ip": "192.168.3.19",                        # ← 更新此处
     "token": "ac572d894b94f6ff9152b0d4b83620e8",  # ← 更新此处
     "type": "light"},
    # ... 其他设备
]
```

修改后重启服务即可生效：

```bash
pkill -f "python3 app.py"
python3 app.py
```

---

## 快速启动

### 前提条件

- Mac 与设备处于**同一局域网**（Wi-Fi：HUAWEI-51EFL1）
- 已安装 Python 3 及依赖库

### 检查依赖

```bash
python3 -c "import flask, miio; print('OK')"
```

如未安装：

```bash
pip3 install flask python-miio --break-system-packages
```

### 启动服务

```bash
cd /Users/mingkun/claude_project/mijia-panel
python3 app.py
```

出现以下输出即表示启动成功：

```
启动米家控制面板，访问 http://localhost:5001
 * Running on http://127.0.0.1:5001
```

### 访问面板

打开浏览器，访问：

```
http://localhost:5001
```

### 停止服务

在终端按 `Ctrl + C`。

> **注意**：macOS Monterey 及以上系统的 AirPlay 会占用 5000 端口，因此本项目使用 **5001** 端口。

---

## 开机自启动

使用 macOS LaunchAgent 实现开机自动启动后台服务。

### 安装服务

```bash
./install-service.sh
```

安装后：
- 服务会立即启动
- 开机后自动在后台运行
- 访问地址：http://localhost:5001

### 卸载服务

```bash
./uninstall-service.sh
```

### 常用命令

| 命令 | 说明 |
|------|------|
| `launchctl list \| grep mijia` | 查看服务状态 |
| `launchctl unload ~/Library/LaunchAgents/com.mijia.panel.plist` | 停止服务 |
| `launchctl load ~/Library/LaunchAgents/com.mijia.panel.plist` | 启动服务 |
| `tail -f /tmp/mijia-panel.log` | 查看日志 |

### 工作原理

- 使用 macOS 原生 LaunchAgent 机制
- 服务以 `--service` 参数启动，不会自动打开浏览器
- 用户按需打开 Edge PWA 应用或浏览器访问

---

## macOS 应用打包

将项目打包为独立的 macOS 应用（.app）。

### 打包步骤

```bash
# 1. 创建虚拟环境并安装依赖
python3 -m venv build_env
source build_env/bin/activate
pip install pyinstaller flask python-miio requests pycryptodome Pillow charset-normalizer colorama

# 2. 执行打包
python build_app.py
```

### 输出位置

```
dist/米家控制面板.app
```

### 两种启动模式

| 模式 | 命令 | 说明 |
|------|------|------|
| 交互模式 | 双击应用 | 启动服务 + 自动打开 Edge PWA |
| 服务模式 | 应用路径 `--service` | 仅启动后台服务 |

### Edge PWA 应用

如果已通过 Edge 浏览器将网页封装为 PWA 应用，启动器会自动打开它：

- 默认路径：`~/Applications/Edge Apps.localized/米家控制面板.app`
- 如未找到 PWA，会回退到默认浏览器

---

## 页面说明

### 顶部空气质量条

页面顶部常驻显示空气检测仪的实时数据：

| 指标 | 单位 | 颜色含义 |
|------|------|----------|
| CO₂ | ppm | 绿色 < 800 / 黄色 < 1200 / 红色 ≥ 1200 |
| 温度 | °C | — |
| 湿度 | % | — |
| PM2.5 | μg/m³ | — |
| TVOC | ppb | — |

### 设备卡片

- **绿点**：设备在线
- **红点**：设备离线或无法连接
- **橙色边框**：设备已开启
- **拨动开关**：仅在设备在线时显示，点击后约 2 秒生效

### 刷新机制

- 页面加载后自动查询所有设备，约 5 秒内完成
- 之后每 15 秒静默刷新一次
- 只有状态发生变化的卡片才会更新（无全页闪烁）
- 点击右上角「↻ 刷新」按钮可立即刷新

---

## 技术说明

### 文件结构

```
mijia-panel/
├── app.py                 # Flask 后端，API 路由及设备通信
├── launcher.py            # 应用启动器（支持交互/服务模式）
├── service.py             # 后台服务入口
├── build_app.py           # PyInstaller 打包脚本
├── install-service.sh     # 开机自启动安装脚本
├── uninstall-service.sh   # 开机自启动卸载脚本
├── com.mijia.panel.plist  # LaunchAgent 配置文件
├── templates/
│   ├── index.html         # 主页面（设备控制）
│   └── manage.html        # 设备管理页面
├── ARCHITECTURE.md        # 架构文档
└── README.md              # 本文档
```

### API 接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/` | 返回控制面板页面 |
| GET | `/manage` | 返回设备管理页面 |
| GET | `/api/status/all` | 批量查询所有设备状态（返回缓存） |
| GET | `/api/status/<id>` | 查询单个设备状态（实时查询） |
| POST | `/api/control/<id>` | 控制设备，body: `{"power": true/false}` |
| GET | `/api/devices/all` | 获取所有设备列表 |
| POST | `/api/devices/display` | 设置设备显示/隐藏 |

### 设备通信原理

- 使用 `python-miio` 库通过 UDP 与设备直接通信（局域网，无需云端）
- **WiFi 设备**：直接通过 IP + Token 通信
- **蓝牙 Mesh 设备**：通过网关中转通信，同一网关下的设备批量查询
- **后台缓存**：每 10 秒自动刷新设备状态，前端请求直接返回缓存
- **异步控制**：控制操作立即返回，后台线程执行实际指令

详细架构说明请参阅 [ARCHITECTURE.md](ARCHITECTURE.md)

---

## 常见问题

**Q: 设备显示离线但实际在线？**

可能原因：
1. Mac 与设备不在同一 Wi-Fi 网络
2. 设备 IP 已变更（路由器重新分配）
3. 设备暂时无响应，等待下一次自动刷新

**Q: 控制灯/插座后没有反应？**

- 确认设备状态显示为「在线」后再操作
- 命令发送后约 2 秒生效
- 如多次无响应，检查网络连接

**Q: 页面打不开（连接被拒绝）？**

服务未启动，执行：

```bash
cd /Users/mingkun/claude_project/mijia-panel
python3 app.py
```

**Q: 如何在后台运行？**

```bash
cd /Users/mingkun/claude_project/mijia-panel
nohup python3 app.py > mijia.log 2>&1 &
echo "PID: $!"
```

停止：

```bash
pkill -f "python3 app.py"
```

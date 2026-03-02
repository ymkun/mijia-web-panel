# 米家蓝牙Mesh设备浏览器控制 - 产品需求文档

## 概述
- **Summary**: 扩展现有米家设备本地Web控制面板，使其能够控制通过蓝牙Mesh协议连接到米家中枢网关的智能设备，如智能开关等。
- **Purpose**: 解决当前系统只能控制WiFi直连设备的限制，实现对蓝牙Mesh设备的局域网控制。
- **Target Users**: 家庭用户，希望在Mac浏览器中通过局域网统一控制所有米家智能设备。

## Goals
- 实现对蓝牙Mesh设备的状态查询功能
- 实现对蓝牙Mesh设备的开关控制功能
- 保持与现有WiFi设备控制的一致性和用户体验
- 确保在家庭局域网环境下的稳定运行

## Non-Goals (Out of Scope)
- 支持云端控制（仅局域网控制）
- 支持非米家品牌的蓝牙设备
- 支持复杂的场景自动化
- 支持设备固件更新

## Background & Context
- 现有系统使用python-miio库通过UDP与WiFi直连设备通信
- 蓝牙Mesh设备不直接连接WiFi，而是通过米家中枢网关进行通信
- 米家中枢网关本身是WiFi设备，可以作为控制蓝牙Mesh设备的桥梁

## Functional Requirements
- **FR-1**: 识别并添加米家中枢网关到设备列表
- **FR-2**: 通过米家中枢网关查询蓝牙Mesh设备的在线状态
- **FR-3**: 通过米家中枢网关控制蓝牙Mesh设备的开关状态
- **FR-4**: 在前端页面上显示蓝牙Mesh设备，与现有WiFi设备保持一致的UI体验
- **FR-5**: 支持批量查询所有设备（包括WiFi和蓝牙Mesh）的状态

## Non-Functional Requirements
- **NFR-1**: 蓝牙Mesh设备的控制响应时间不超过3秒
- **NFR-2**: 系统稳定性：即使网关离线，也不影响其他WiFi设备的控制
- **NFR-3**: 代码可维护性：保持与现有代码风格一致
- **NFR-4**: 安全性：所有通信均在局域网内进行，不涉及云端

## Constraints
- **Technical**: 依赖米家中枢网关作为蓝牙Mesh设备的控制桥梁
- **Business**: 仅支持米家生态链内的蓝牙Mesh设备
- **Dependencies**: 需要python-miio库支持与米家中枢网关的通信

## Assumptions
- 用户拥有至少一个米家中枢网关，且已配置并连接到家庭WiFi
- 蓝牙Mesh设备已通过米家App添加到米家中枢网关
- 米家中枢网关与Mac设备处于同一局域网

## Acceptance Criteria

### AC-1: 米家中枢网关添加
- **Given**: 用户已获取米家中枢网关的IP和Token
- **When**: 在app.py中添加网关设备信息
- **Then**: 系统能够识别网关并通过其查询蓝牙Mesh设备
- **Verification**: `programmatic`

### AC-2: 蓝牙Mesh设备状态查询
- **Given**: 米家中枢网关在线
- **When**: 系统通过网关查询蓝牙Mesh设备状态
- **Then**: 能够正确获取设备的在线状态和开关状态
- **Verification**: `programmatic`

### AC-3: 蓝牙Mesh设备控制
- **Given**: 米家中枢网关和蓝牙Mesh设备均在线
- **When**: 用户在Web界面上操作蓝牙Mesh设备的开关
- **Then**: 设备状态应在3秒内响应并更新
- **Verification**: `programmatic`

### AC-4: 前端UI显示
- **Given**: 系统已添加蓝牙Mesh设备
- **When**: 用户访问控制面板
- **Then**: 蓝牙Mesh设备应与WiFi设备显示在同一界面，具有相同的控制元素
- **Verification**: `human-judgment`

### AC-5: 批量状态查询
- **Given**: 系统同时包含WiFi设备和蓝牙Mesh设备
- **When**: 页面加载或刷新时
- **Then**: 所有设备（包括蓝牙Mesh）的状态应在5秒内完成查询
- **Verification**: `programmatic`

## Open Questions
- [ ] 如何通过米家中枢网关识别和获取其下的蓝牙Mesh设备列表？
- [ ] 米家中枢网关的MioT协议与普通WiFi设备是否有差异？
- [ ] 蓝牙Mesh设备的控制命令格式是什么？
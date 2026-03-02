# 米家蓝牙Mesh设备浏览器控制 - 实现计划

## [x] 任务1: 研究米家中枢网关的通信协议
- **Priority**: P0
- **Depends On**: None
- **Description**:
  - 研究米家中枢网关的MioT协议
  - 了解如何通过网关查询和控制蓝牙Mesh设备
  - 确定网关的设备类型和控制命令格式
- **Acceptance Criteria Addressed**: AC-1, AC-2, AC-3
- **Test Requirements**:
  - `programmatic` TR-1.1: 能够通过python-miio成功连接到米家中枢网关
  - `programmatic` TR-1.2: 能够获取网关的基本信息和状态
- **Notes**: 需要使用token_extractor.py获取网关的IP和Token

## [x] 任务2: 扩展设备配置结构
- **Priority**: P0
- **Depends On**: 任务1
- **Description**:
  - 在app.py的DEVICES列表中添加米家中枢网关
  - 为蓝牙Mesh设备设计配置结构，包含网关ID关联
  - 扩展CONTROLLABLE_TYPES以支持蓝牙Mesh设备
- **Acceptance Criteria Addressed**: AC-1, AC-4
- **Test Requirements**:
  - `programmatic` TR-2.1: 网关设备能够被系统正确识别
  - `programmatic` TR-2.2: 蓝牙Mesh设备配置能够被正确加载
- **Notes**: 蓝牙Mesh设备需要关联到特定的网关

## [x] 任务3: 实现网关通信模块
- **Priority**: P0
- **Depends On**: 任务2
- **Description**:
  - 编写通过网关查询蓝牙Mesh设备状态的代码
  - 编写通过网关控制蓝牙Mesh设备的代码
  - 处理网关离线的异常情况
- **Acceptance Criteria Addressed**: AC-2, AC-3
- **Test Requirements**:
  - `programmatic` TR-3.1: 能够通过网关获取蓝牙Mesh设备状态
  - `programmatic` TR-3.2: 能够通过网关控制蓝牙Mesh设备开关
  - `programmatic` TR-3.3: 网关离线时能够优雅处理
- **Notes**: 可能需要使用特定的MioT命令与网关通信

## [x] 任务4: 扩展批量查询功能
- **Priority**: P1
- **Depends On**: 任务3
- **Description**:
  - 修改现有的批量查询逻辑，支持同时查询WiFi设备和蓝牙Mesh设备
  - 优化查询速度，确保在5秒内完成所有设备的状态查询
- **Acceptance Criteria Addressed**: AC-5
- **Test Requirements**:
  - `programmatic` TR-4.1: 批量查询能够包含所有设备类型
  - `programmatic` TR-4.2: 批量查询响应时间不超过5秒
- **Notes**: 可以考虑使用多线程并行查询不同网关下的设备

## [x] 任务5: 前端页面适配
- **Priority**: P1
- **Depends On**: 任务2, 任务3
- **Description**:
  - 确保蓝牙Mesh设备在前端页面上正确显示
  - 保持与现有WiFi设备一致的UI体验
  - 确保控制操作能够正确触发后端API
- **Acceptance Criteria Addressed**: AC-4
- **Test Requirements**:
  - `human-judgment` TR-5.1: 蓝牙Mesh设备显示与WiFi设备一致
  - `programmatic` TR-5.2: 前端控制操作能够正确发送到后端
- **Notes**: 可能需要在前端添加设备类型标识

## [x] 任务6: 测试与调试
- **Priority**: P1
- **Depends On**: 任务4, 任务5
- **Description**:
  - 测试所有功能点的正确性
  - 调试可能的问题和异常情况
  - 确保系统稳定性和响应速度
- **Acceptance Criteria Addressed**: AC-1, AC-2, AC-3, AC-4, AC-5
- **Test Requirements**:
  - `programmatic` TR-6.1: 所有API接口正常工作
  - `programmatic` TR-6.2: 设备状态查询和控制响应时间符合要求
  - `human-judgment` TR-6.3: 整体用户体验流畅
- **Notes**: 需要在实际环境中测试，确保网关和蓝牙Mesh设备都在线
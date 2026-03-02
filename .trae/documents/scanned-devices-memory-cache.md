# scanned_devices 优化计划

## 问题分析

当前实现将扫描结果写入配置文件的 `scanned_devices` 字段，存在以下问题：
- 需要手动清理
- 持久化临时数据
- 可能造成数据冗余

## 优化方案

**使用内存缓存替代配置文件存储**

### 优点
1. 扫描数据是临时的，不需要持久化
2. 批量添加后无需清理
3. 服务重启后自然清除，避免脏数据
4. 简化代码逻辑

## 实施步骤

### 步骤1：添加内存缓存变量

```python
# 在全局变量区域添加
scanned_devices_cache = []
```

### 步骤2：修改 `/api/cloud/scan` 接口

将扫描结果存入内存而非配置文件：

```python
# 修改前
config["scanned_devices"] = new_devices
save_config(config)

# 修改后
global scanned_devices_cache
scanned_devices_cache = new_devices
```

### 步骤3：修改 `/api/cloud/scanned` 接口

从内存读取而非配置文件：

```python
# 修改前
scanned = config.get("scanned_devices", [])

# 修改后
global scanned_devices_cache
return jsonify(scanned_devices_cache)
```

### 步骤4：修改 `/api/devices/scanned` 接口

同样从内存读取

```python
# 修改前
scanned = config.get("scanned_devices", [])

# 修改后
global scanned_devices_cache
for d in scanned_devices_cache:
    ...
```

### 歪骤5：在 load_config 中清理旧的 scanned_devices 字段

```python
config.pop("scanned_devices", None)
```

这样配置文件中的旧字段会被自动清除。

## 文件修改清单

| 文件 | 修改位置 | 修改内容 |
|------|----------|----------|
| `app.py` | 全局变量区 | 添加 `scanned_devices_cache = []` |
| `app.py` | `api_cloud_scan()` | 存入内存而非配置文件 |
| `app.py` | `api_cloud_scanned()` | 从内存读取 |
| `app.py` | `api_devices_scanned()` | 从内存读取 |
| `app.py` | `load_config()` | 清理旧的 scanned_devices 字段 |
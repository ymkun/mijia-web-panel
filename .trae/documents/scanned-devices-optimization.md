# scanned\_devices 字段分析与优化计划

## 当前设计分析

### scanned\_devices 的作用

`scanned_devices` 是一个**临时缓存**，用于存储从米家云端扫描到的新设备：

| API                    | 方法   | 作用                              |
| ---------------------- | ---- | ------------------------------- |
| `/api/cloud/scan`      | POST | 扫描米家云端设备，结果存入 `scanned_devices` |
| `/api/cloud/scanned`   | GET  | 返回已扫描的设备列表                      |
| `/api/devices/scanned` | GET  | 返回已扫描设备列表（带display状态）           |

### 工作流程

```
扫描设备 → 存入 scanned_devices → 用户选择 → 批量添加到 devices
```

### 当前问题

1. **数据冗余** - 批量添加后 `scanned_devices` 未清除
2. **状态混乱** - 同一设备可能同时存在于 `scanned_devices` 和 `devices`
3. **重复添加** - 之前扫描的设备可能被重复添加

***

## 优化方案

### 方案A：废除 scanned\_devices（不推荐）

**缺点**：

* 每次扫描都会将所有设备添加到 `devices`

* 用户无法选择性添加设备

* 会添加很多用户不需要的设备

### 方案B：保留但优化（推荐）

**改进点**：

1. 批量添加后清除 `scanned_devices`
2. 添加时间戳标记，定期清理过期数据
3. 前端展示时区分"已添加"和"待添加"状态

***

## 实施步骤

### 步骤1：批量添加后清除 scanned\_devices

修改 `api_batch_add_devices()` 函数，添加成功后清除 `scanned_devices`：

```python
# 在 save_config(config) 之前添加
if "scanned_devices" in config:
    del config["scanned_devices"]
```

### 步骤2：添加扫描时间戳

修改 `api_cloud_scan()` 函数，记录扫描时间：

```python
config["scanned_devices"] = new_devices
config["scanned_at"] = time.time()
```

### 步骤3：添加清理过期数据逻辑

在 `load_config()` 中添加过期数据清理（超过24小时的扫描数据）：

```python
if config.get("scanned_at") and time.time() - config["scanned_at"] > 86400:
    config.pop("scanned_devices", None)
    config.pop("scanned_at", None)
```

***

## 文件修改清单

| 文件       | 修改内容                     |
| -------- | ------------------------ |
| `app.py` | 批量添加后清除 scanned\_devices |
| `app.py` | 添加扫描时间戳                  |
| `app.py` | 添加过期数据清理逻辑               |


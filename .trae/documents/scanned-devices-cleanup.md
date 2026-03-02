# scanned_devices 优化计划

## 需求

批量添加设备后清除 `scanned_devices`，避免数据冗余。

## 当前问题

用户扫描设备后，数据存入 `scanned_devices`，批量添加到 `devices` 后，`scanned_devices` 未清除，导致：
- 配置文件冗余
- 可能造成混淆

## 实施步骤

### 修改 `api_batch_add_devices()` 函数

在批量添加成功后，清除 `scanned_devices` 字段：

```python
# 在 save_config(config) 之前添加
config.pop("scanned_devices", None)
```

## 文件修改

| 文件 | 修改位置 | 修改内容 |
|------|----------|----------|
| `app.py` | `api_batch_add_devices()` | 添加成功后清除 scanned_devices |

# 设备扫描格式统一优化计划

## 问题分析

### 当前扫描格式（问题格式）
```json
{
  "id": "added_438236a6", 
  "name": "次卧室灯", 
  "ip": "111.199.83.253", 
  "token": "7ecbc7293965c38de1f77c2acdeec407", 
  "type": "light", 
  "model": "yeelink.switch.ylsw4"
}
```

### 手动创建格式（期望格式）
```json
{
  "id": "mesh_switch_living_lamp", 
  "name": "客厅灯", 
  "gateway_id": "gateway_main", 
  "did": "1132827761", 
  "siid": 2, 
  "type": "mesh_switch"
}
```

### 关键差异

| 字段 | 扫描格式 | 手动格式 | 说明 |
|------|---------|---------|------|
| `id` | `added_xxxxxxxx` | 自定义ID | 扫描时生成随机ID |
| `gateway_id` | ❌ 缺失 | ✅ 有 | 蓝牙Mesh设备必需 |
| `did` | ✅ 有 | ✅ 有 | 设备ID |
| `siid` | ❌ 缺失 | ✅ 有 | 服务ID（蓝牙Mesh设备必需） |
| `ip` | ✅ 有 | ❌ 无（Mesh设备） | WiFi设备需要 |
| `token` | ✅ 有 | ❌ 无（Mesh设备） | WiFi设备需要 |
| `model` | ✅ 有 | ❌ 可选 | 设备型号 |

### 问题根源

1. **扫描阶段**（`api_cloud_scan()` 函数，第727-782行）：
   - WiFi设备：生成格式正确，但缺少 `id` 字段
   - 蓝牙Mesh设备：缺少 `id`、`gateway_id`、`siid` 字段

2. **批量添加阶段**（`api_batch_add_devices()` 函数，第552-651行）：
   - 在此阶段才解析 `siid` 并添加 `gateway_id`
   - 在此阶段才生成 `id`

## 优化方案

**将格式转换提前到扫描阶段**，使扫描结果直接呈现最终格式。

### 优点
1. 扫描结果即可预览最终设备格式
2. 前端展示更清晰
3. 批量添加逻辑简化
4. 用户可以直观看到设备类型和关键信息

## 实施步骤

### 步骤1：修改 `api_cloud_scan()` 函数

**位置**：`app.py` 第727-782行

**修改内容**：

1. 获取网关信息（用于蓝牙Mesh设备的 `gateway_id`）
2. 为每个设备生成 `id`
3. 对于蓝牙Mesh设备：
   - 解析 `did` 中的 `siid` 信息（格式：`did.siid` 如 `1132827761.s2`）
   - 添加 `gateway_id` 字段
   - 添加 `siid` 字段
4. 统一设备格式

**修改前**：
```python
new_devices = []
for d in devices:
    device_type = get_device_type_from_model(d.get("model"))
    ip = d.get("ip")
    did = d.get("did")
    
    if ip and ip not in existing_ips:
        new_devices.append({
            "name": d["name"],
            "did": did,
            "ip": ip,
            "token": d["token"],
            "mac": d["mac"],
            "model": d["model"],
            "type": device_type,
            "controllable": device_type in CONTROLLABLE_TYPES
        })
    elif did and did not in existing_dids and not ip:
        new_devices.append({
            "name": d["name"],
            "did": did,
            "ip": "",
            "token": d.get("token", ""),
            "mac": d.get("mac", ""),
            "model": d["model"],
            "type": device_type,
            "controllable": False,
            "is_ble_mesh": True
        })
```

**修改后**：
```python
new_devices = []
gateways = {d["id"]: d for d in existing_devices if d.get("type") == "gateway"}
default_gateway = list(gateways.keys())[0] if gateways else None

for d in devices:
    device_type = get_device_type_from_model(d.get("model"))
    ip = d.get("ip")
    did = d.get("did")
    
    if ip and ip not in existing_ips:
        device_id = f"added_{uuid.uuid4().hex[:8]}"
        new_devices.append({
            "id": device_id,
            "name": d["name"],
            "did": did,
            "ip": ip,
            "token": d["token"],
            "mac": d["mac"],
            "model": d["model"],
            "type": device_type,
            "controllable": device_type in CONTROLLABLE_TYPES
        })
    elif did and did not in existing_dids and not ip:
        device_id = f"added_{uuid.uuid4().hex[:8]}"
        
        parsed_did = did
        siid = None
        if "." in did and did.split(".")[-1].startswith("s"):
            parts = did.split(".")
            parsed_did = parts[0]
            try:
                siid = int(parts[1][1:])
            except ValueError:
                pass
        
        device_data = {
            "id": device_id,
            "name": d["name"],
            "did": parsed_did,
            "ip": "",
            "token": d.get("token", ""),
            "mac": d.get("mac", ""),
            "model": d["model"],
            "type": device_type,
            "controllable": False,
            "is_ble_mesh": True
        }
        
        if siid is not None:
            device_data["siid"] = siid
            device_data["gateway_id"] = default_gateway
            device_data["type"] = "mesh_switch"
        
        new_devices.append(device_data)
```

### 步骤2：简化 `api_batch_add_devices()` 函数

**位置**：`app.py` 第552-651行

**修改内容**：
由于扫描结果已经包含完整格式，批量添加时直接使用，无需再次解析和转换。

**简化逻辑**：
```python
for device in devices:
    device_id = device.get("id")
    if not device_id:
        continue
    
    if device_id in {d.get("id") for d in existing_devices}:
        for d in existing_devices:
            if d.get("id") == device_id:
                d["name"] = device.get("name", d.get("name"))
                break
    else:
        existing_devices.append(device)
        added_count += 1
```

### 步骤3：更新前端显示逻辑（可选）

**位置**：`templates/manage.html`

**修改内容**：
前端可以根据 `gateway_id` 或 `siid` 字段的存在，更准确地判断设备类型并显示相应信息。

## 文件修改清单

| 文件 | 修改位置 | 修改内容 |
|------|----------|----------|
| `app.py` | 第727-782行 `api_cloud_scan()` | 添加网关获取、ID生成、siid解析、gateway_id添加 |
| `app.py` | 第552-651行 `api_batch_add_devices()` | 简化逻辑，直接使用扫描结果的格式 |

## 预期结果

### WiFi设备扫描结果
```json
{
  "id": "added_438236a6",
  "name": "次卧室灯",
  "did": "123456",
  "ip": "192.168.3.100",
  "token": "7ecbc7293965c38de1f77c2acdeec407",
  "mac": "AA:BB:CC:DD:EE:FF",
  "model": "yeelink.switch.ylsw4",
  "type": "light",
  "controllable": true
}
```

### 蓝牙Mesh设备扫描结果
```json
{
  "id": "added_87654321",
  "name": "客厅灯",
  "did": "1132827761",
  "siid": 2,
  "gateway_id": "gateway_main",
  "ip": "",
  "token": "",
  "mac": "",
  "model": "lumi.ctrl_switch",
  "type": "mesh_switch",
  "controllable": false,
  "is_ble_mesh": true
}
```

## 注意事项

1. **向后兼容**：批量添加接口需要兼容旧格式（如果有缓存的扫描结果）
2. **网关缺失**：如果没有配置网关，`gateway_id` 将为 `None`，需要在前端提示用户
3. **siid解析**：只有 `did` 格式为 `xxxxx.sN` 时才能解析出 `siid`，否则为 `None`

# 智能开关聚合重构计划

## 需求分析

**当前逻辑**：
- 扫描时：每个智能开关按键作为单独设备返回（相同 `did`，不同 `siid`）
- 存储时：每个按键单独存储为 `mesh_switch` 类型设备
- 展示时：前端/后端通过 `did` 聚合展示

**目标逻辑**：
- 扫描时：后端按 `did` 聚合智能开关，返回聚合后的设备
- 存储时：存储聚合后的智能开关（包含 `sub_switches` 子设备列表）
- 展示时：直接展示聚合后的设备，无需再次聚合

---

## 数据结构变更

### 聚合后的智能开关数据结构

```json
{
  "name": "客厅开关",
  "did": "1132827761",
  "model": "lumi.switch.n4acn4",
  "type": "mesh_switch_group",
  "is_ble_mesh": true,
  "is_existing": false,
  "sub_switches": [
    {"name": "客厅灯", "siid": 2},
    {"name": "餐厅灯", "siid": 3},
    {"name": "客厅开关按键3", "siid": 4},
    {"name": "客厅开关按键4", "siid": 12}
  ]
}
```

---

## 实施步骤

### 步骤1：修改后端扫描接口 - 聚合智能开关

**文件**: `app.py` 的 `api_cloud_scan()` 函数

**修改内容**：
1. 扫描完成后，识别所有 `mesh_switch` 类型设备
2. 按 `did` 分组聚合
3. 返回聚合后的设备列表

```python
def aggregate_scanned_mesh_switches(devices):
    mesh_switches = [d for d in devices if d.get("type") == "mesh_switch"]
    other_devices = [d for d in devices if d.get("type") != "mesh_switch"]
    
    grouped = {}
    for d in mesh_switches:
        did = d.get("did")
        if did not in grouped:
            grouped[did] = {
                "name": d.get("name", "智能开关"),
                "did": did,
                "model": d.get("model"),
                "type": "mesh_switch_group",
                "is_ble_mesh": True,
                "is_existing": d.get("is_existing", False),
                "sub_switches": []
            }
        grouped[did]["sub_switches"].append({
            "name": d.get("name", "开关"),
            "siid": d.get("siid", 2)
        })
        if d.get("is_existing"):
            grouped[did]["is_existing"] = True
    
    for group in grouped.values():
        group["sub_switches"].sort(key=lambda x: x["siid"])
    
    return other_devices + list(grouped.values())
```

---

### 步骤2：修改后端添加接口 - 支持聚合设备

**文件**: `app.py` 的 `api_add_device()` 和 `api_batch_add_devices()` 函数

**修改内容**：
1. 识别 `mesh_switch_group` 类型设备
2. 将 `sub_switches` 展开为多个 `mesh_switch` 设备存储
3. 保持与现有存储格式兼容

```python
if device_type == "mesh_switch_group":
    # 展开子设备存储
    for sub in device.get("sub_switches", []):
        device_id = uuid.uuid4().hex[:8]
        new_device = {
            "id": device_id,
            "name": sub.get("name", "开关"),
            "did": did,
            "siid": sub.get("siid", 2),
            "ip": "",
            "token": token,
            "type": "mesh_switch",
            "gateway_id": default_gateway,
            "model": model
        }
        devices.append(new_device)
```

---

### 步骤3：修改前端扫描结果展示

**文件**: `templates/manage.html` 的 `startScan()` 函数

**修改内容**：
1. 识别 `mesh_switch_group` 类型设备
2. 显示聚合后的智能开关，展开子设备列表
3. 添加/批量添加时传递完整聚合数据

```javascript
if (d.type === 'mesh_switch_group') {
    html += '<div class="scan-item mesh-group-item">' +
        '<div class="scan-item-info">' +
            '<div class="scan-item-name">' + d.name + ' <span style="font-size:10px;color:#888;">(智能开关 ' + d.sub_switches.length + '键)</span></div>' +
            '<div class="scan-item-model">' + (d.model || '未知型号') + '</div>' +
            '<div class="scan-item-sub">' + 
                d.sub_switches.map(s => s.name + '(siid:' + s.siid + ')').join(' / ') + 
            '</div>' +
        '</div>' +
        actionBtn +
    '</div>';
}
```

---

### 步骤4：修改前端添加逻辑

**文件**: `templates/manage.html` 的 `addScannedDevice()` 和 `getSelectedDevices()` 函数

**修改内容**：
- 传递 `sub_switches` 数据到后端

---

## 文件修改清单

| 文件 | 修改位置 | 修改内容 |
|------|----------|----------|
| `app.py` | `api_cloud_scan()` | 添加聚合函数，返回聚合后的设备 |
| `app.py` | `api_add_device()` | 支持 `mesh_switch_group` 类型 |
| `app.py` | `api_batch_add_devices()` | 支持 `mesh_switch_group` 类型 |
| `templates/manage.html` | `startScan()` | 展示聚合后的智能开关 |
| `templates/manage.html` | `addScannedDevice()` | 传递聚合数据 |
| `templates/manage.html` | `getSelectedDevices()` | 传递聚合数据 |

---

## 测试要点

1. 扫描后智能开关按键按 `did` 聚合显示
2. 添加聚合设备后，存储为多个 `mesh_switch` 子设备
3. 一级页面正常展示聚合后的智能开关
4. 管理页面正常展示和管理子设备
5. 批量添加功能正常工作

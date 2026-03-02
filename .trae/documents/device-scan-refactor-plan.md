# 设备扫描逻辑重构计划

## 需求分析

**当前逻辑**：
- 后端扫描时过滤掉已有设备，只返回"新设备"
- 前端只显示新设备，用户只能添加新设备

**目标逻辑**：
- 后端返回所有扫描到的设备，并标记是否已在本地
- 前端显示所有设备，区分"已添加"和"未添加"状态
- 用户可以查看所有设备，但只能添加未添加的设备

---

## 实施步骤

### 步骤1：修改后端 `/api/cloud/scan` 接口

**文件**: `app.py` (第 727-782 行)

**修改内容**：
- 移除过滤逻辑，返回所有扫描到的设备
- 为每个设备添加 `is_existing` 字段，标记是否已在本地配置中

**修改前**：
```python
existing_devices = get_all_devices()
existing_ips = {d.get("ip") for d in existing_devices if d.get("ip")}
existing_dids = {d.get("did") for d in existing_devices if d.get("did")}

new_devices = []
for d in devices:
    # 过滤逻辑...
    if ip and ip not in existing_ips:
        new_devices.append({...})
    elif did and did not in existing_dids and not ip:
        new_devices.append({...})

return jsonify({
    "ok": True,
    "devices": new_devices,
    "total": len(devices),
    "new_count": len(new_devices)
})
```

**修改后**：
```python
existing_devices = get_all_devices()
existing_ips = {d.get("ip") for d in existing_devices if d.get("ip")}
existing_dids = {d.get("did") for d in existing_devices if d.get("did")}

all_scanned = []
for d in devices:
    device_type = get_device_type_from_model(d.get("model"))
    ip = d.get("ip")
    did = d.get("did")
    
    # 判断是否已存在
    is_existing = False
    if ip and ip in existing_ips:
        is_existing = True
    elif did and did in existing_dids and not ip:
        is_existing = True
    
    all_scanned.append({
        "name": d["name"],
        "did": did,
        "ip": ip or "",
        "token": d.get("token", ""),
        "mac": d.get("mac", ""),
        "model": d["model"],
        "type": device_type,
        "controllable": device_type in CONTROLLABLE_TYPES,
        "is_existing": is_existing,
        "is_ble_mesh": not ip and did
    })

global scanned_devices_cache
scanned_devices_cache = all_scanned

return jsonify({
    "ok": True,
    "devices": all_scanned,
    "total": len(devices)
})
```

---

### 步骤2：修改前端扫描结果显示逻辑

**文件**: `templates/manage.html` (第 477-527 行)

**修改内容**：
- 更新扫描状态显示文案
- 为已添加的设备显示不同的 UI 状态
- 已添加的设备禁用添加按钮

**修改前**：
```javascript
statusEl.textContent = '扫描完成: 共 ' + scanResult.total + ' 个设备，发现 ' + scanResult.new_count + ' 个新设备';

if (scanResult.devices.length === 0) {
    devicesEl.innerHTML = '<div class="empty">没有发现新设备</div>';
}
```

**修改后**：
```javascript
statusEl.textContent = '扫描完成: 共 ' + scanResult.total + ' 个设备';

if (scanResult.devices.length === 0) {
    devicesEl.innerHTML = '<div class="empty">没有扫描到设备</div>';
}
```

**设备列表渲染修改**：
```javascript
for (let i = 0; i < scanResult.devices.length; i++) {
    const d = scanResult.devices[i];
    const isBleMesh = d.is_ble_mesh || !d.ip;
    const isExisting = d.is_existing;
    
    let actionBtn = '';
    if (isExisting) {
        actionBtn = '<span class="status-tag existing">已添加</span>';
    } else {
        actionBtn = '<button class="btn btn-success btn-small" onclick="addScannedDevice(' + i + ')">添加</button>';
    }
    
    html += '<div class="scan-item' + (isExisting ? ' existing-device' : '') + '">' +
        '<div style="display: flex; align-items: center; gap: 10px;">' +
            (isExisting ? '' : '<input type="checkbox" class="device-checkbox" data-index="' + i + '" onchange="updateBatchButton()">') +
            '<div class="scan-item-info">' +
                '<div class="scan-item-name">' + d.name + (isBleMesh ? ' <span style="font-size:10px;color:#888;">(蓝牙Mesh)</span>' : '') + '</div>' +
                '<div class="scan-item-model">' + (d.model || '未知型号') + '</div>' +
                '<div class="scan-item-ip">' + (d.ip || '无IP地址') + '</div>' +
            '</div>' +
        '</div>' +
        actionBtn +
    '</div>';
}
```

---

### 步骤3：修改批量添加逻辑

**文件**: `templates/manage.html` (第 544-552 行)

**修改内容**：
- `getSelectedDevices` 函数过滤掉已添加的设备

```javascript
function getSelectedDevices() {
    const checkboxes = document.querySelectorAll('.device-checkbox:checked');
    const devices = [];
    for (let i = 0; i < checkboxes.length; i++) {
        const index = parseInt(checkboxes[i].dataset.index);
        const device = scannedDevicesList[index];
        if (!device.is_existing) {
            devices.push(device);
        }
    }
    return devices;
}
```

---

### 步骤4：添加 CSS 样式

**文件**: `templates/manage.html` (样式区域)

**添加内容**：
```css
.scan-item.existing-device {
    opacity: 0.7;
    background-color: #f5f5f5;
}

.status-tag.existing {
    background-color: #e0e0e0;
    color: #666;
    padding: 4px 12px;
    border-radius: 4px;
    font-size: 12px;
}
```

---

## 文件修改清单

| 文件 | 修改位置 | 修改内容 |
|------|----------|----------|
| `app.py` | 第 740-782 行 | 移除过滤逻辑，添加 `is_existing` 字段 |
| `templates/manage.html` | 第 477-527 行 | 更新扫描结果显示逻辑 |
| `templates/manage.html` | 第 544-552 行 | 修改批量添加过滤逻辑 |
| `templates/manage.html` | 样式区域 | 添加已添加设备的样式 |

---

## 测试要点

1. 扫描后应显示所有设备（包括已添加的）
2. 已添加的设备应显示"已添加"标签，无复选框
3. 未添加的设备应显示"添加"按钮和复选框
4. 批量添加时只添加未添加的设备
5. 单个添加功能正常工作

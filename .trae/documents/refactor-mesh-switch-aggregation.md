# 智能开关设备聚合逻辑重构计划

## 背景

当前系统中智能开关的聚合逻辑分布在后端和前端多处，根据需求需要简化：
- **后端聚合逻辑**：全部下线，设备以原始形式存储和返回
- **前端聚合逻辑**：仅保留一级展示页面（index.html）的聚合展示

## 聚合逻辑说明

聚合依据：
- `did`：设备ID（如 `1132827761`）
- `siid`：服务ID/按键ID（如 `2`, `3`, `4`）

一个多键智能开关在米家中会显示为多个设备，DID格式为 `1132827761.s2`、`1132827761.s3` 等，需要聚合为一个设备组展示。

---

## 需要修改的内容

### 一、后端修改 (app.py)

#### 1. 删除函数

| 函数名 | 行号 | 说明 |
|--------|------|------|
| `aggregate_scanned_mesh_switches()` | L97-127 | 扫描设备时的聚合函数 |
| `aggregate_mesh_switches()` | L182-247 | 展示设备时的聚合函数 |
| `build_aggregated_status()` | L473-495 | 构建聚合状态的函数 |

#### 2. 修改 `get_display_devices()` (L162-176)

**修改前**：
```python
def get_display_devices():
    ...
    return aggregate_mesh_switches(devices)
```

**修改后**：
```python
def get_display_devices():
    ...
    return devices  # 直接返回，不聚合
```

#### 3. 修改 `index()` 路由 (L439-452)

**修改前**：
```python
@app.route("/")
def index():
    devices = get_display_devices()
    aggregated_devices = aggregate_mesh_switches(devices)
    ...
```

**修改后**：
```python
@app.route("/")
def index():
    devices = get_display_devices()
    # 传递原始设备数据，前端负责聚合
    devices_meta = []
    for d in devices:
        meta = {"id": d["id"], "name": d["name"], "type": d["type"],
                "controllable": d.get("controllable", d["type"] in CONTROLLABLE_TYPES)}
        if d["type"] == "mesh_switch":
            meta["did"] = d.get("did")
            meta["siid"] = d.get("siid")
            meta["gateway_id"] = d.get("gateway_id")
        devices_meta.append(meta)
    return render_template("index.html", devices=devices_meta)
```

#### 4. 修改 `api_status_all()` (L458-471)

**修改前**：
```python
@app.route("/api/status/all")
def api_status_all():
    ...
    return jsonify(build_aggregated_status(device_cache))
```

**修改后**：
```python
@app.route("/api/status/all")
def api_status_all():
    ...
    return jsonify(device_cache)  # 直接返回原始状态
```

#### 5. 修改 `api_cloud_scan()` (L822-909)

**修改前** (L900)：
```python
aggregated = aggregate_scanned_mesh_switches(all_scanned)
scanned_devices_cache = aggregated
return jsonify({"ok": True, "devices": aggregated, "total": len(devices)})
```

**修改后**：
```python
scanned_devices_cache = all_scanned
return jsonify({"ok": True, "devices": all_scanned, "total": len(devices)})
```

#### 6. 修改 `api_mesh_status()` (L510-540)

该 API 用于查询聚合组的状态，由于前端不再使用聚合组ID，可以删除或标记为废弃。

#### 7. 修改 `query_all_devices_parallel()` (L299-387)

移除 `mesh_switch_group` 类型的处理分支，仅保留 `mesh_switch` 类型的批量查询逻辑。

---

### 二、前端修改

#### 1. 一级展示页面 (templates/index.html)

**新增前端聚合逻辑**：

在 JavaScript 中添加聚合函数，将 `mesh_switch` 类型设备按 `did` 聚合：

```javascript
function aggregateMeshSwitches(devices) {
    const meshDevices = devices.filter(d => d.type === 'mesh_switch');
    const otherDevices = devices.filter(d => d.type !== 'mesh_switch');
    
    const grouped = {};
    meshDevices.forEach(d => {
        const did = d.did;
        if (!did) {
            otherDevices.push(d);
            return;
        }
        if (!grouped[did]) {
            grouped[did] = {
                id: `mesh_group_${did}`,
                name: d.name,  // 第一个设备的名字作为组名（父设备名字）
                type: 'mesh_switch_group',
                did: did,
                gateway_id: d.gateway_id,
                controllable: true,
                sub_switches: []
            };
        }
        grouped[did].sub_switches.push({
            id: d.id,
            name: d.name,  // 按键名字
            siid: d.siid,
            did: did
        });
    });
    
    const result = [...otherDevices];
    Object.values(grouped).forEach(group => {
        if (group.sub_switches.length > 1) {
            // 多个按键：聚合展示，名字是第一个设备的名字（父设备名字）
            group.sub_switches.sort((a, b) => (a.siid || 0) - (b.siid || 0));
            result.push(group);
        } else if (group.sub_switches.length === 1) {
            // 只添加了1个按键：显示该按键，名字是按键的名字
            result.push({
                id: group.sub_switches[0].id,
                name: group.sub_switches[0].name,
                type: 'mesh_switch',
                did: group.did,
                siid: group.sub_switches[0].siid,
                controllable: true
            });
        }
    });
    
    return result;
}
```

修改 `DEVICES` 的初始化：
```javascript
const RAW_DEVICES = {{ devices | tojson }};
const DEVICES = aggregateMeshSwitches(RAW_DEVICES);
```

#### 2. 设备管理页面 (templates/manage.html)

**修改显示逻辑**：不聚合，但按 `did` 排序展示

修改 `renderDevices()` 函数：

```javascript
function renderDevices(devices) {
    const listEl = document.getElementById('device-list');
    if (devices.length === 0) {
        listEl.innerHTML = '<div class="empty">暂无设备</div>';
        return;
    }
    
    // 按 did 排序：有 did 的 mesh_switch 设备按 did 分组排列
    const sortedDevices = [...devices].sort((a, b) => {
        // mesh_switch 类型按 did 排序
        if (a.type === 'mesh_switch' && b.type === 'mesh_switch') {
            const didA = a.did || '';
            const didB = b.did || '';
            if (didA !== didB) {
                return didA.localeCompare(didB);
            }
            // 同一 did 按 siid 排序
            const siidA = a.siid || 0;
            const siidB = b.siid || 0;
            return siidA - siidB;
        }
        // mesh_switch 优先显示
        if (a.type === 'mesh_switch') return -1;
        if (b.type === 'mesh_switch') return 1;
        // 其他设备按名字排序
        return (a.name || '').localeCompare(b.name || '');
    });
    
    let html = '';
    let currentDid = null;
    
    for (let i = 0; i < sortedDevices.length; i++) {
        const d = sortedDevices[i];
        const typeLabel = TYPE_LABELS[d.type] || d.type;
        const siidInfo = d.type === 'mesh_switch' ? ' · siid:' + (d.siid || '-') : '';
        const didInfo = d.type === 'mesh_switch' && d.did ? ' · did:' + d.did : '';
        
        // 如果是 mesh_switch 且 did 变化，添加分隔提示
        if (d.type === 'mesh_switch' && d.did && d.did !== currentDid) {
            currentDid = d.did;
            html += '<div class="did-separator">智能开关组 (DID: ' + d.did + ')</div>';
        }
        
        html += '<div class="device-item">' +
            '<div class="device-info">' +
                '<div class="device-name">' + d.name + '</div>' +
                '<div class="device-type">' + typeLabel + siidInfo + didInfo + (d.controllable ? ' · 可控制' : '') + '</div>' +
            '</div>' +
            '<div class="device-actions">' +
                '<button class="btn btn-secondary btn-small" onclick="showRenameModal(\'' + d.id + '\', \'' + d.name + '\')">重命名</button> ' +
                '<button class="btn btn-danger btn-small" onclick="deleteDevice(\'' + d.id + '\')">删除</button> ' +
                '<label class="toggle-switch">' +
                    '<input type="checkbox" ' + (d.display ? 'checked' : '') + ' onchange="toggleDisplay(\'' + d.id + '\', this.checked)">' +
                    '<span class="slider"></span>' +
                '</label>' +
                '<span class="status ' + (d.display ? 'online' : 'offline') + '">' + (d.display ? '显示' : '隐藏') + '</span>' +
            '</div>' +
        '</div>';
    }
    listEl.innerHTML = html;
}
```

添加 CSS 样式：
```css
.did-separator {
    background: #f0f0f0;
    padding: 8px 15px;
    font-size: 13px;
    color: #666;
    margin-top: 15px;
    margin-bottom: 5px;
    border-radius: 6px;
}
.did-separator:first-child {
    margin-top: 0;
}
```

移除原有的聚合显示相关 CSS 样式（`.mesh-group`, `.mesh-group-header`, `.mesh-sub-item`）。

---

### 三、扫描设备页面修改

扫描结果页面需要调整，不再显示聚合后的 `mesh_switch_group`，而是显示原始的 `mesh_switch` 设备。

修改 `startScan()` 函数中的设备渲染逻辑，移除 `mesh_switch_group` 类型的特殊处理，改为按 `did` 分组显示。

---

## 实施步骤

1. **后端修改**：
   - [ ] 删除 `aggregate_scanned_mesh_switches()` 函数
   - [ ] 删除 `aggregate_mesh_switches()` 函数
   - [ ] 删除 `build_aggregated_status()` 函数
   - [ ] 修改 `get_display_devices()` 函数
   - [ ] 修改 `index()` 路由
   - [ ] 修改 `api_status_all()` 路由
   - [ ] 修改 `api_cloud_scan()` 路由
   - [ ] 修改 `query_all_devices_parallel()` 函数
   - [ ] 删除或废弃 `api_mesh_status()` 路由

2. **前端修改**：
   - [ ] index.html: 添加前端聚合函数
   - [ ] index.html: 修改设备初始化逻辑
   - [ ] manage.html: 修改为按 did 排序显示
   - [ ] manage.html: 添加 did 分隔符样式
   - [ ] manage.html: 移除原有聚合显示 CSS

3. **测试验证**：
   - [ ] 测试一级页面展示是否正常聚合
   - [ ] 测试设备管理页面是否按 did 排序
   - [ ] 测试扫描设备功能
   - [ ] 测试设备控制功能

---

## 展示逻辑说明

### 一级页面展示规则

| 场景 | 展示方式 | 设备名字 |
|------|----------|----------|
| 只添加了1个按键 | 单独显示该按键 | 按键的名字 |
| 添加了多个按键 | 聚合显示 | 第一个设备的名字（父设备名字） |
| 智能开关只有1个按键 | 单独显示 | 该按键的名字 |

### 设备管理页面展示规则

- 不聚合显示
- 按 `did` 排序，同一 `did` 的设备相邻显示
- 同一 `did` 内按 `siid` 排序
- 添加 `did` 分隔符，便于识别同一智能开关的多个按键

---

## 注意事项

1. **数据兼容性**：已存储的设备配置不需要修改，因为存储的就是原始 `mesh_switch` 设备
2. **API 兼容性**：`/api/mesh/status/<id>` API 将被废弃
3. **状态缓存**：`device_cache` 的数据结构保持不变，仍然是按设备 ID 存储状态

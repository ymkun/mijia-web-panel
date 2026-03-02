import json
import subprocess
import sys
import time
import os
from datetime import datetime

from flask import Flask, jsonify, request, render_template

app = Flask(__name__)

CONFIG_FILE = "devices_config.json"

ALL_DEVICES = [
    {"id": "light_living",   "name": "护眼客厅吸顶灯", "ip": "192.168.3.19",  "token": "ac572d894b94f6ff9152b0d4b83620e8", "type": "light"},
    {"id": "light_master",   "name": "护眼吸顶灯(主卧)", "ip": "192.168.3.18", "token": "e71ca3aa999c0915bb35dcfd129ee833",  "type": "light"},
    {"id": "light_second",   "name": "护眼吸顶灯(次卧)", "ip": "192.168.3.20", "token": "7744f2b0e25fa12a4c89e0665188ceff",  "type": "light"},
    {"id": "ac_bedroom",     "name": "卧室空调",          "ip": "192.168.3.27",  "token": "d0f0996992aefabaf404e0b1ccd27e72",  "type": "airconditioner"},
    {"id": "humi_bedroom",   "name": "加湿器(卧室)",      "ip": "192.168.3.110", "token": "7ccbd60fafc3cb292598e98bf6861875",  "type": "humidifier"},
    {"id": "humi_main",      "name": "加湿器",            "ip": "192.168.3.39",  "token": "42e51253e3c9a68a523a23f3cb7bdcd8",  "type": "humidifier"},
    {"id": "plug_marshall",  "name": "马歇尔音响插座",    "ip": "192.168.3.72",  "token": "b832b9071f03b8de61796fcd5d1f0528",  "type": "plug"},
    {"id": "sensor_air",     "name": "空气检测仪",        "ip": "192.168.3.115", "token": "574c5776754746564a78474d33546159",  "type": "sensor"},
    {"id": "sensor_gas1",    "name": "天然气卫士(1)",     "ip": "192.168.3.32",  "token": "6afa85ffb8c8ceaabe74a2499c54c7e2",  "type": "sensor"},
    {"id": "sensor_gas2",    "name": "天然气卫士(2)",     "ip": "192.168.3.38",  "token": "2491754b1a1a59050841e42cc304e98f",  "type": "sensor"},
    {"id": "speaker_master", "name": "小爱-主卧室",       "ip": "192.168.3.74",  "token": "75706f514f65776c5645624b38505a51",  "type": "speaker"},
    {"id": "speaker_kitchen","name": "小爱-厨房",         "ip": "192.168.3.75",  "token": "71664179645a743230337142476d6c6f",  "type": "speaker"},
    {"id": "speaker_living", "name": "小爱-客厅",         "ip": "192.168.3.58",  "token": "515451347978707a754956526c4d7268",  "type": "speaker"},
    {"id": "microwave",      "name": "微波炉",            "ip": "192.168.3.44",  "token": "ac1c03087158c82a711c99eff86951ae",  "type": "appliance"},
    {"id": "blender",        "name": "破壁机",            "ip": "192.168.3.94",  "token": "04c591c36b8b74c85cc43e5d3dea934f",  "type": "appliance"},
    {"id": "gateway_main",   "name": "Xiaomi Home Hub",      "ip": "192.168.3.77", "token": "33665268384134384864456b7a434537", "type": "gateway"},
    {"id": "mesh_switch_living_lamp",   "name": "客厅灯",      "gateway_id": "gateway_main", "did": "1132827761", "siid": 2, "type": "mesh_switch"},
    {"id": "mesh_switch_dining",   "name": "餐厅灯",      "gateway_id": "gateway_main", "did": "1132827761", "siid": 3, "type": "mesh_switch"},
    {"id": "mesh_switch_living_key3",   "name": "客厅开关按键3",      "gateway_id": "gateway_main", "did": "1132827761", "siid": 4, "type": "mesh_switch"},
    {"id": "mesh_switch_living_key4",   "name": "客厅开关按键4",      "gateway_id": "gateway_main", "did": "1132827761", "siid": 12, "type": "mesh_switch"},
    {"id": "mesh_switch_master_left",   "name": "主卧室灯",      "gateway_id": "gateway_main", "did": "1133876907", "siid": 2, "type": "mesh_switch"},
    {"id": "mesh_switch_master_right",   "name": "主卧室右键",      "gateway_id": "gateway_main", "did": "1133876907", "siid": 3, "type": "mesh_switch"},
    {"id": "mesh_switch_bedside_wardrobe_left",   "name": "床头灯(衣柜)",      "gateway_id": "gateway_main", "did": "1133877605", "siid": 2, "type": "mesh_switch"},
    {"id": "mesh_switch_bedside_wardrobe_right",   "name": "床头灯右键(衣柜)",      "gateway_id": "gateway_main", "did": "1133877605", "siid": 3, "type": "mesh_switch"},
    {"id": "mesh_switch_bathroom_left",   "name": "卫生间灯",      "gateway_id": "gateway_main", "did": "1133877109", "siid": 2, "type": "mesh_switch"},
    {"id": "mesh_switch_bathroom_right",   "name": "卫生间右键",      "gateway_id": "gateway_main", "did": "1133877109", "siid": 3, "type": "mesh_switch"},
    {"id": "mesh_switch_hall_downlight",   "name": "筒灯",      "gateway_id": "gateway_main", "did": "1133878182", "siid": 2, "type": "mesh_switch"},
    {"id": "mesh_switch_hall_right",   "name": "门厅右键",      "gateway_id": "gateway_main", "did": "1133878182", "siid": 3, "type": "mesh_switch"},
    {"id": "mesh_switch_bedside_window_left",   "name": "吸顶灯",      "gateway_id": "gateway_main", "did": "1133877047", "siid": 2, "type": "mesh_switch"},
    {"id": "mesh_switch_bedside_window_right",   "name": "床头灯右键(窗)",      "gateway_id": "gateway_main", "did": "1133877047", "siid": 3, "type": "mesh_switch"},
    # 次卧室Yeelight智能开关
    {"id": "mesh_switch_second_bedroom",   "name": "次卧室开关",      "gateway_id": "gateway_main", "did": "1095536654", "siid": 2, "type": "mesh_switch"},
]

CONTROLLABLE_TYPES = {"light", "airconditioner", "humidifier", "plug", "mesh_switch"}

def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {"display_devices": [d["id"] for d in ALL_DEVICES], "scanned_devices": []}

def save_config(config):
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=2)

def get_display_devices():
    config = load_config()
    display_ids = set(config.get("display_devices", []))
    devices = [d for d in ALL_DEVICES if d["id"] in display_ids]
    
    # 始终包含网关设备（用于蓝牙Mesh设备通信）
    for d in ALL_DEVICES:
        if d.get("type") == "gateway" and d["id"] not in display_ids:
            devices.append(d)
    
    # 始终包含空气质量检测仪（用于环境监测）
    for d in ALL_DEVICES:
        if d.get("id") == "sensor_air" and d["id"] not in display_ids:
            devices.append(d)
    
    return devices

def get_device_map():
    return {d["id"]: d for d in ALL_DEVICES}

DEVICE_MAP = get_device_map()

_MIIO_GET = """
import warnings; warnings.filterwarnings("ignore")
import json, sys
from miio import Device
ip, token, did, device_type, gateway_id, mesh_did, siid = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5], sys.argv[6], sys.argv[7]
if device_type == "gateway":
    try:
        gateway = Device(ip=ip, token=token, timeout=4)
        info = gateway.send("miIO.info", [], retry_count=1)
        print(json.dumps({"online": True, "power": None}))
    except Exception as e:
        print(json.dumps({"online": False, "power": None, "error": str(e)}))
elif device_type == "mesh_switch" and gateway_id and mesh_did:
    try:
        gateway = Device(ip=ip, token=token, timeout=5)
        props = gateway.send("get_properties", [{"siid": int(siid), "piid": 1, "did": mesh_did}], retry_count=3)
        power = props[0].get("value") if props and props[0].get("code") == 0 else None
        print(json.dumps({"online": True, "power": power}))
    except Exception as e:
        print(json.dumps({"online": False, "power": None, "error": str(e)}))
else:
    try:
        dev = Device(ip=ip, token=token, timeout=4)
        props = dev.send("get_properties", [{"siid": 2, "piid": 1, "did": did}], retry_count=1)
        power = props[0].get("value") if props and props[0].get("code") == 0 else None
        print(json.dumps({"online": True, "power": power}))
    except Exception as e:
        print(json.dumps({"online": False, "power": None, "error": str(e)}))
"""

_MIIO_GET_ALL = """
import warnings; warnings.filterwarnings("ignore")
import json, sys, threading
from miio import Device
devices = json.loads(sys.argv[1])
results = {}
AIR_PROPS = ["co2", "humidity", "temperature", "pm25", "tvoc"]
gateway_map = {d["id"]: d for d in devices if d.get("type") == "gateway"}
def query(d):
    try:
        if d.get("type") == "gateway":
            try:
                dev = Device(ip=d["ip"], token=d["token"], timeout=4)
                info = dev.send("miIO.info", [], retry_count=1)
                results[d["id"]] = {"online": True, "power": None}
            except Exception:
                results[d["id"]] = {"online": False, "power": None}
            return
        elif d.get("type") == "mesh_switch" and d.get("gateway_id"):
            gateway = gateway_map.get(d["gateway_id"])
            if gateway:
                try:
                    dev = Device(ip=gateway["ip"], token=gateway["token"], timeout=5)
                    siid = d.get("siid", 2)
                    props = dev.send("get_properties", [{"siid": siid, "piid": 1, "did": d.get("did")}], retry_count=3)
                    if isinstance(props, list) and props and props[0].get("code") == 0:
                        power = props[0].get("value")
                    else:
                        power = None
                    results[d["id"]] = {"online": True, "power": power}
                except Exception:
                    results[d["id"]] = {"online": False, "power": None}
            else:
                results[d["id"]] = {"online": False, "power": None}
            return
        elif d.get("type") == "sensor" and d.get("id") == "sensor_air":
            dev = Device(ip=d["ip"], token=d["token"], timeout=3)
            r = dev.send("get_prop", AIR_PROPS, retry_count=0)
            if isinstance(r, dict):
                readings = {k: r[k] for k in AIR_PROPS if k in r}
                results[d["id"]] = {"online": True, "power": None, "readings": readings}
            else:
                results[d["id"]] = {"online": True, "power": None}
            return
        elif d.get("type") == "speaker":
            dev = Device(ip=d["ip"], token=d["token"], timeout=3)
            dev.send("miIO.info", [], retry_count=0)
            results[d["id"]] = {"online": True, "power": None}
            return
        else:
            dev = Device(ip=d["ip"], token=d["token"], timeout=3)
            props = dev.send("get_properties", [{"siid": 2, "piid": 1, "did": d["id"]}], retry_count=0)
            if isinstance(props, list) and props and props[0].get("code") == 0:
                power = props[0].get("value")
            else:
                power = None
            results[d["id"]] = {"online": True, "power": power}
    except Exception:
        results[d["id"]] = {"online": False, "power": None}
mesh_devices = [d for d in devices if d.get("type") == "mesh_switch"]
other_devices = [d for d in devices if d.get("type") != "mesh_switch"]
threads = [threading.Thread(target=query, args=(d,)) for d in other_devices]
for t in threads: t.start()
for t in threads: t.join()
for d in mesh_devices:
    query(d)
print(json.dumps(results))
"""

_MIIO_SET = """
import warnings; warnings.filterwarnings("ignore")
import json, sys
from miio import Device
ip, token, did, val, device_type, gateway_id, mesh_did, siid = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5], sys.argv[6], sys.argv[7], sys.argv[8]
if device_type == "mesh_switch" and gateway_id and mesh_did:
    try:
        gateway = Device(ip=ip, token=token, timeout=5)
        gateway.send("set_properties", [{"siid": int(siid), "piid": 1, "value": val == "true", "did": mesh_did}], retry_count=3)
        print(json.dumps({"ok": True}))
    except Exception as e:
        print(json.dumps({"ok": False, "error": str(e)}))
else:
    try:
        dev = Device(ip=ip, token=token, timeout=4)
        dev.send("set_properties", [{"siid": 2, "piid": 1, "value": val == "true", "did": did}], retry_count=1)
        print(json.dumps({"ok": True}))
    except Exception as e:
        print(json.dumps({"ok": False, "error": str(e)}))
"""

def _run_miio(script, args, timeout=7):
    result = subprocess.run(
        [sys.executable, "-c", script] + args,
        capture_output=True, text=True, timeout=timeout
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip().splitlines()[-1] if result.stderr.strip() else "error")
    return json.loads(result.stdout.strip())

@app.route("/")
def index():
    devices = get_display_devices()
    devices_meta = [
        {"id": d["id"], "name": d["name"], "type": d["type"],
         "controllable": d["type"] in CONTROLLABLE_TYPES}
        for d in devices
    ]
    return render_template("index.html", devices=devices_meta)

@app.route("/manage")
def manage_page():
    return render_template("manage.html")

@app.route("/api/status/all")
def api_status_all():
    devices = get_display_devices()
    payload = json.dumps([{
        "id": d["id"], 
        "ip": d.get("ip", ""), 
        "token": d.get("token", ""), 
        "type": d["type"],
        "gateway_id": d.get("gateway_id", ""),
        "did": d.get("did", ""),
        "siid": d.get("siid", 2)
    } for d in devices])
    try:
        result = _run_miio(_MIIO_GET_ALL, [payload], timeout=60)
        return jsonify(result)
    except subprocess.TimeoutExpired:
        return jsonify({d["id"]: {"online": False, "power": None} for d in devices})
    except Exception as e:
        return jsonify({d["id"]: {"online": False, "power": None} for d in devices})

@app.route("/api/status/<device_id>")
def api_status(device_id):
    dev = DEVICE_MAP.get(device_id)
    if not dev:
        return jsonify({"error": "Device not found"}), 404
    try:
        if dev.get("type") == "mesh_switch" and dev.get("gateway_id"):
            gateway = DEVICE_MAP.get(dev["gateway_id"])
            if gateway:
                result = _run_miio(_MIIO_GET, [gateway["ip"], gateway["token"], device_id, dev["type"], dev["gateway_id"], dev.get("did", ""), str(dev.get("siid", 2))])
                return jsonify(result)
            else:
                return jsonify({"online": False, "power": None, "error": "Gateway not found"})
        else:
            result = _run_miio(_MIIO_GET, [dev["ip"], dev["token"], device_id, dev["type"], "", "", ""])
            return jsonify(result)
    except subprocess.TimeoutExpired:
        return jsonify({"online": False, "power": None, "error": "timeout"})
    except Exception as e:
        return jsonify({"online": False, "power": None, "error": str(e)})

@app.route("/api/control/<device_id>", methods=["POST"])
def api_control(device_id):
    dev = DEVICE_MAP.get(device_id)
    if not dev:
        return jsonify({"error": "Device not found"}), 404
    if dev["type"] not in CONTROLLABLE_TYPES:
        return jsonify({"error": "Device is not controllable"}), 400
    body = request.get_json() or {}
    if "power" not in body:
        return jsonify({"error": "Missing 'power' field"}), 400
    power_str = "true" if body["power"] else "false"
    try:
        if dev.get("type") == "mesh_switch" and dev.get("gateway_id"):
            gateway = DEVICE_MAP.get(dev["gateway_id"])
            if gateway:
                result = _run_miio(_MIIO_SET, [gateway["ip"], gateway["token"], device_id, power_str, dev["type"], dev["gateway_id"], dev.get("did", ""), str(dev.get("siid", 2))])
                result["power"] = body["power"]
                return jsonify(result)
            else:
                return jsonify({"ok": False, "error": "Gateway not found"})
        else:
            result = _run_miio(_MIIO_SET, [dev["ip"], dev["token"], device_id, power_str, dev["type"], "", "", ""])
            result["power"] = body["power"]
            return jsonify(result)
    except subprocess.TimeoutExpired:
        return jsonify({"ok": False, "error": "timeout"})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)})

@app.route("/api/devices/all")
def api_devices_all():
    config = load_config()
    display_ids = set(config.get("display_devices", []))
    devices_info = []
    for d in ALL_DEVICES:
        devices_info.append({
            "id": d["id"],
            "name": d["name"],
            "type": d["type"],
            "controllable": d["type"] in CONTROLLABLE_TYPES,
            "display": d["id"] in display_ids
        })
    return jsonify(devices_info)

@app.route("/api/devices/scanned")
def api_devices_scanned():
    config = load_config()
    scanned = config.get("scanned_devices", [])
    display_ids = set(config.get("display_devices", []))
    devices_info = []
    for d in scanned:
        devices_info.append({
            "id": d["id"],
            "name": d["name"],
            "type": d["type"],
            "controllable": d["type"] in CONTROLLABLE_TYPES,
            "display": d["id"] in display_ids
        })
    return jsonify(devices_info)

@app.route("/api/devices/display", methods=["POST"])
def api_set_display():
    body = request.get_json() or {}
    device_id = body.get("device_id")
    display = body.get("display", True)
    if not device_id:
        return jsonify({"error": "Missing device_id"}), 400
    config = load_config()
    display_devices = set(config.get("display_devices", []))
    if display:
        display_devices.add(device_id)
    else:
        display_devices.discard(device_id)
    config["display_devices"] = list(display_devices)
    save_config(config)
    return jsonify({"ok": True})

@app.route("/api/devices/scan", methods=["POST"])
def api_scan_devices():
    try:
        result = subprocess.run(
            [sys.executable, "token_extractor.py"],
            capture_output=True, text=True, timeout=120
        )
        if result.returncode != 0:
            return jsonify({"error": result.stderr}), 500
        output = result.stdout
        devices = []
        for line in output.split('\n'):
            if 'model:' in line.lower() or 'did:' in line.lower():
                pass
        return jsonify({"ok": True, "message": "扫描完成，请查看设备列表"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    print("启动米家控制面板，访问 http://localhost:5001")
    print("设备管理页面，访问 http://localhost:5001/manage")
    app.run(host="127.0.0.1", port=5001, debug=False)

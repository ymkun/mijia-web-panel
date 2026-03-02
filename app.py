import json
import subprocess
import sys
import time
import os
import threading
from datetime import datetime
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

from flask import Flask, jsonify, request, render_template

app = Flask(__name__)

CONFIG_DIR = Path.home() / ".mijia-panel"
CONFIG_FILE = CONFIG_DIR / "devices_config.json"

CONFIG_DIR.mkdir(parents=True, exist_ok=True)

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
    {"id": "mesh_switch_second_bedroom",   "name": "次卧室开关",      "gateway_id": "gateway_main", "did": "1095536654", "siid": 2, "type": "mesh_switch"},
]

CONTROLLABLE_TYPES = {"light", "airconditioner", "humidifier", "plug", "mesh_switch"}

device_cache = {}
cache_lock = threading.Lock()
cache_last_update = 0
background_refresh_running = False

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
    
    for d in ALL_DEVICES:
        if d.get("type") == "gateway" and d["id"] not in display_ids:
            devices.append(d)
    
    for d in ALL_DEVICES:
        if d.get("id") == "sensor_air" and d["id"] not in display_ids:
            devices.append(d)
    
    return devices

def get_device_map():
    return {d["id"]: d for d in ALL_DEVICES}

DEVICE_MAP = get_device_map()

_MIIO_GET_ALL_PARALLEL = """
import warnings; warnings.filterwarnings("ignore")
import json, sys
from miio import Device
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

devices = json.loads(sys.argv[1])
results = {}
results_lock = threading.Lock()
AIR_PROPS = ["co2", "humidity", "temperature", "pm25", "tvoc"]
gateway_map = {d["id"]: d for d in devices if d.get("type") == "gateway"}

def query_gateway_mesh_devices(gateway_id, gateway_info, mesh_devices):
    gateway_results = {}
    try:
        dev = Device(ip=gateway_info["ip"], token=gateway_info["token"], timeout=5)
        props_list = [{"siid": d.get("siid", 2), "piid": 1, "did": d.get("did")} for d in mesh_devices]
        props = dev.send("get_properties", props_list, retry_count=2)
        if isinstance(props, list):
            for i, p in enumerate(props):
                if i < len(mesh_devices):
                    d = mesh_devices[i]
                    if p.get("code") == 0:
                        gateway_results[d["id"]] = {"online": True, "power": p.get("value")}
                    else:
                        gateway_results[d["id"]] = {"online": True, "power": None}
    except Exception:
        for d in mesh_devices:
            gateway_results[d["id"]] = {"online": False, "power": None}
    return gateway_results

def query_single(d):
    device_result = {"online": False, "power": None}
    try:
        if d.get("type") == "gateway":
            try:
                dev = Device(ip=d["ip"], token=d["token"], timeout=2)
                info = dev.send("miIO.info", [], retry_count=0)
                device_result = {"online": True, "power": None}
            except Exception:
                device_result = {"online": False, "power": None}
        elif d.get("type") == "sensor" and d.get("id") == "sensor_air":
            dev = Device(ip=d["ip"], token=d["token"], timeout=2)
            r = dev.send("get_prop", AIR_PROPS, retry_count=0)
            if isinstance(r, dict):
                readings = {k: r[k] for k in AIR_PROPS if k in r}
                device_result = {"online": True, "power": None, "readings": readings}
            else:
                device_result = {"online": True, "power": None}
        elif d.get("type") == "speaker":
            dev = Device(ip=d["ip"], token=d["token"], timeout=2)
            dev.send("miIO.info", [], retry_count=0)
            device_result = {"online": True, "power": None}
        else:
            dev = Device(ip=d["ip"], token=d["token"], timeout=2)
            props = dev.send("get_properties", [{"siid": 2, "piid": 1, "did": d["id"]}], retry_count=0)
            if isinstance(props, list) and props and props[0].get("code") == 0:
                power = props[0].get("value")
            else:
                power = None
            device_result = {"online": True, "power": power}
    except Exception:
        device_result = {"online": False, "power": None}
    return d["id"], device_result

mesh_by_gateway = {}
non_mesh_devices = []
for d in devices:
    if d.get("type") == "mesh_switch" and d.get("gateway_id"):
        gid = d["gateway_id"]
        if gid not in mesh_by_gateway:
            mesh_by_gateway[gid] = []
        mesh_by_gateway[gid].append(d)
    else:
        non_mesh_devices.append(d)

with ThreadPoolExecutor(max_workers=15) as executor:
    futures = {executor.submit(query_single, d): d for d in non_mesh_devices}
    for gid, mesh_devices in mesh_by_gateway.items():
        gateway_info = gateway_map.get(gid)
        if gateway_info:
            futures[executor.submit(query_gateway_mesh_devices, gid, gateway_info, mesh_devices)] = ("mesh_batch", gid)
    
    for future in as_completed(futures, timeout=30):
        try:
            result = future.result(timeout=8)
            with results_lock:
                if isinstance(result, dict) and "mesh_batch" not in result:
                    for device_id, device_result in result.items():
                        results[device_id] = device_result
                elif isinstance(result, tuple):
                    device_id, device_result = result
                    results[device_id] = device_result
        except Exception:
            pass

print(json.dumps(results))
"""

_MIIO_SET = """
import warnings; warnings.filterwarnings("ignore")
import json, sys
from miio import Device
ip, token, did, val, device_type, gateway_id, mesh_did, siid = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5], sys.argv[6], sys.argv[7], sys.argv[8]
if device_type == "mesh_switch" and gateway_id and mesh_did:
    try:
        gateway = Device(ip=ip, token=token, timeout=3)
        gateway.send("set_properties", [{"siid": int(siid), "piid": 1, "value": val == "true", "did": mesh_did}], retry_count=1)
        print(json.dumps({"ok": True}))
    except Exception as e:
        print(json.dumps({"ok": False, "error": str(e)}))
else:
    try:
        dev = Device(ip=ip, token=token, timeout=3)
        dev.send("set_properties", [{"siid": 2, "piid": 1, "value": val == "true", "did": did}], retry_count=1)
        print(json.dumps({"ok": True}))
    except Exception as e:
        print(json.dumps({"ok": False, "error": str(e)}))
"""

_MIIO_GET_SINGLE = """
import warnings; warnings.filterwarnings("ignore")
import json, sys
from miio import Device

ip, token, device_id, device_type, gateway_ip, gateway_token, mesh_did, siid = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5], sys.argv[6], sys.argv[7], sys.argv[8]

result = {"online": False, "power": None}
try:
    if device_type == "mesh_switch" and gateway_ip and mesh_did:
        dev = Device(ip=gateway_ip, token=gateway_token, timeout=3)
        props = dev.send("get_properties", [{"siid": int(siid), "piid": 1, "did": mesh_did}], retry_count=2)
        if isinstance(props, list) and props and props[0].get("code") == 0:
            result = {"online": True, "power": props[0].get("value")}
        else:
            result = {"online": True, "power": None}
    elif device_type == "gateway":
        dev = Device(ip=ip, token=token, timeout=2)
        dev.send("miIO.info", [], retry_count=0)
        result = {"online": True, "power": None}
    elif device_type == "sensor":
        AIR_PROPS = ["co2", "humidity", "temperature", "pm25", "tvoc"]
        dev = Device(ip=ip, token=token, timeout=2)
        r = dev.send("get_prop", AIR_PROPS, retry_count=0)
        if isinstance(r, dict):
            readings = {k: r[k] for k in AIR_PROPS if k in r}
            result = {"online": True, "power": None, "readings": readings}
        else:
            result = {"online": True, "power": None}
    elif device_type == "speaker":
        dev = Device(ip=ip, token=token, timeout=2)
        dev.send("miIO.info", [], retry_count=0)
        result = {"online": True, "power": None}
    else:
        dev = Device(ip=ip, token=token, timeout=2)
        props = dev.send("get_properties", [{"siid": 2, "piid": 1, "did": device_id}], retry_count=0)
        if isinstance(props, list) and props and props[0].get("code") == 0:
            result = {"online": True, "power": props[0].get("value")}
        else:
            result = {"online": True, "power": None}
except Exception:
    pass

print(json.dumps(result))
"""

def _run_miio(script, args, timeout=10):
    result = subprocess.run(
        [sys.executable, "-c", script] + args,
        capture_output=True, text=True, timeout=timeout
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip().splitlines()[-1] if result.stderr.strip() else "error")
    return json.loads(result.stdout.strip())

def refresh_cache_background():
    global device_cache, cache_last_update, background_refresh_running
    
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
        result = _run_miio(_MIIO_GET_ALL_PARALLEL, [payload], timeout=35)
        with cache_lock:
            device_cache = result
            cache_last_update = time.time()
    except Exception as e:
        pass

def start_background_refresh():
    global background_refresh_running
    
    def refresh_loop():
        while True:
            refresh_cache_background()
            time.sleep(10)
    
    if not background_refresh_running:
        background_refresh_running = True
        thread = threading.Thread(target=refresh_loop, daemon=True)
        thread.start()

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
    global device_cache, cache_last_update
    devices = get_display_devices()
    
    with cache_lock:
        if device_cache:
            return jsonify(device_cache)
    
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
        result = _run_miio(_MIIO_GET_ALL_PARALLEL, [payload], timeout=35)
        with cache_lock:
            device_cache = result
            cache_last_update = time.time()
        return jsonify(result)
    except subprocess.TimeoutExpired:
        return jsonify({d["id"]: {"online": False, "power": None} for d in devices})
    except Exception as e:
        return jsonify({d["id"]: {"online": False, "power": None} for d in devices})

@app.route("/api/status/<device_id>")
def api_status(device_id):
    global device_cache
    dev = DEVICE_MAP.get(device_id)
    if not dev:
        return jsonify({"error": "Device not found"}), 404
    
    gateway_ip = ""
    gateway_token = ""
    mesh_did = ""
    siid = str(dev.get("siid", 2))
    
    if dev.get("type") == "mesh_switch" and dev.get("gateway_id"):
        gateway = DEVICE_MAP.get(dev["gateway_id"])
        if gateway:
            gateway_ip = gateway.get("ip", "")
            gateway_token = gateway.get("token", "")
            mesh_did = dev.get("did", "")
    
    try:
        result = _run_miio(_MIIO_GET_SINGLE, [
            dev.get("ip", ""),
            dev.get("token", ""),
            device_id,
            dev.get("type", ""),
            gateway_ip,
            gateway_token,
            mesh_did,
            siid
        ], timeout=5)
        with cache_lock:
            if device_cache is not None:
                device_cache[device_id] = result
        return jsonify(result)
    except Exception as e:
        return jsonify({"online": False, "power": None})

@app.route("/api/control/<device_id>", methods=["POST"])
def api_control(device_id):
    global device_cache
    dev = DEVICE_MAP.get(device_id)
    if not dev:
        return jsonify({"error": "Device not found"}), 404
    if dev["type"] not in CONTROLLABLE_TYPES:
        return jsonify({"error": "Device is not controllable"}), 400
    body = request.get_json() or {}
    if "power" not in body:
        return jsonify({"error": "Missing 'power' field"}), 400
    power_str = "true" if body["power"] else "false"
    
    with cache_lock:
        if device_id in device_cache:
            device_cache[device_id]["power"] = body["power"]
            device_cache[device_id]["online"] = True
    
    def async_control():
        try:
            if dev.get("type") == "mesh_switch" and dev.get("gateway_id"):
                gateway = DEVICE_MAP.get(dev["gateway_id"])
                if gateway:
                    _run_miio(_MIIO_SET, [gateway["ip"], gateway["token"], device_id, power_str, dev["type"], dev["gateway_id"], dev.get("did", ""), str(dev.get("siid", 2))], timeout=5)
            else:
                _run_miio(_MIIO_SET, [dev["ip"], dev["token"], device_id, power_str, dev["type"], "", "", ""], timeout=5)
        except Exception:
            pass
    
    threading.Thread(target=async_control, daemon=True).start()
    
    return jsonify({"ok": True, "power": body["power"]})

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
    start_background_refresh()
    app.run(host="127.0.0.1", port=5001, debug=False, threaded=True)

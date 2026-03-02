import json
import subprocess
import sys
import time
import os
import threading
from datetime import datetime
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
import warnings
import uuid

warnings.filterwarnings("ignore")

from flask import Flask, jsonify, request, render_template

app = Flask(__name__)

CONFIG_DIR = Path.home() / ".mijia-panel"
CONFIG_FILE = CONFIG_DIR / "devices_config.json"

CONFIG_DIR.mkdir(parents=True, exist_ok=True)

from mijia_cloud import MijiaCloudConnector

cloud_connector = MijiaCloudConnector(CONFIG_DIR)

DEFAULT_DEVICES = [
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
AIR_PROPS = ["co2", "humidity", "temperature", "pm25", "tvoc"]

MODEL_TYPE_MAP = {
    "yeelink.": "light",
    "zhimi.airpurifier.": "airconditioner",
    "zhimi.humidifier.": "humidifier",
    "zhimi.airmonitor.": "sensor",
    "lumi.gateway.": "gateway",
    "lumi.sensor_": "sensor",
    "cuco.plug.": "plug",
    "chuangmi.plug.": "plug",
    "qmi.powerstrip.": "plug",
    "xiaomi.aircondition.": "airconditioner",
    "xiaomi.airpurifier.": "airconditioner",
    "xiaomi.humidifier.": "humidifier",
    "xiaomi.relay.": "plug",
    "xiaomi.wifispeaker.": "speaker",
    "xiaomi.smartpad.": "speaker",
    "mijia.camera.": "sensor",
    "mijia.vacuum.": "appliance",
    "roborock.vacuum.": "appliance",
    "dreame.vacuum.": "appliance",
    "viomi.vacuum.": "appliance",
    "viomi.waterheater.": "appliance",
    "viomi.fridge.": "appliance",
    "viomi.hood.": "appliance",
    "mmgg.feeder.": "appliance",
    "mmgg.pet_waterer.": "appliance",
    "yunmi.waterheater.": "appliance",
    "yunmi.kettle.": "appliance",
    "zhimi.heater.": "airconditioner",
    "leshow.heater.": "airconditioner",
    "leshow.fan.": "airconditioner",
    "dmaker.fan.": "airconditioner",
    "zhimi.fan.": "airconditioner",
    "roome.fan.": "airconditioner",
    "isa.camera.": "sensor",
    "isa.kettle.": "appliance",
    "shuii.humidifier.": "humidifier",
    "deerma.humidifier.": "humidifier",
    "nwt.derh.": "humidifier",
    "nwt.wetscrub.": "appliance",
    "tinymu.toiletlid.": "appliance",
    "mrbond.airer.": "appliance",
    "dooya.curtain.": "appliance",
    "giot.curtain.": "appliance",
    "lumi.curtain.": "appliance",
    "lumi.airrtc.": "airconditioner",
    "lumi.ctrl_": "mesh_switch",
    "lumi.switch.": "mesh_switch",
    "zimi.powerstrip.": "plug",
    "huayi.light.": "light",
    "opple.light.": "light",
    "philips.light.": "light",
    "philips.lightstrip.": "light",
    "mijia.light.": "light",
    "mesh_switch": "mesh_switch",
}

device_cache = {}
cache_lock = threading.Lock()
cache_last_update = 0
background_refresh_running = False

def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {
        "devices": DEFAULT_DEVICES,
        "display_devices": [d["id"] for d in DEFAULT_DEVICES]
    }

def save_config(config):
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=2)

def get_all_devices():
    config = load_config()
    return config.get("devices", DEFAULT_DEVICES)

def get_device_type_from_model(model):
    if not model:
        return "appliance"
    for model_prefix, device_type in MODEL_TYPE_MAP.items():
        if model.startswith(model_prefix):
            return device_type
    return "appliance"

def get_display_devices():
    config = load_config()
    all_devices = get_all_devices()
    display_ids = set(config.get("display_devices", []))
    devices = [d for d in all_devices if d["id"] in display_ids]
    
    for d in all_devices:
        if d.get("type") == "gateway" and d["id"] not in display_ids:
            devices.append(d)
    
    for d in all_devices:
        if d.get("id") == "sensor_air" and d["id"] not in display_ids:
            devices.append(d)
    
    return devices

def get_device_map():
    all_devices = get_all_devices()
    return {d["id"]: d for d in all_devices}

DEVICE_MAP = get_device_map()

from miio import Device

def query_single_device(d, gateway_map):
    device_result = {"online": False, "power": None}
    try:
        if d.get("type") == "gateway":
            try:
                dev = Device(ip=d["ip"], token=d["token"], timeout=2)
                dev.send("miIO.info", [], retry_count=0)
                device_result = {"online": True, "power": None}
            except Exception:
                device_result = {"online": False, "power": None}
        elif d.get("type") == "mesh_switch" and d.get("gateway_id"):
            gateway = gateway_map.get(d["gateway_id"])
            if gateway:
                try:
                    dev = Device(ip=gateway["ip"], token=gateway["token"], timeout=3)
                    siid = d.get("siid", 2)
                    props = dev.send("get_properties", [{"siid": siid, "piid": 1, "did": d.get("did")}], retry_count=1)
                    if isinstance(props, list) and props and props[0].get("code") == 0:
                        device_result = {"online": True, "power": props[0].get("value")}
                    else:
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
                device_result = {"online": True, "power": props[0].get("value")}
            else:
                device_result = {"online": True, "power": None}
    except Exception:
        device_result = {"online": False, "power": None}
    return d["id"], device_result

def query_all_devices_parallel(devices):
    results = {}
    gateway_map = {d["id"]: d for d in devices if d.get("type") == "gateway"}
    
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
    
    def query_mesh_batch(gateway_id, gateway_info, mesh_devices):
        batch_results = {}
        try:
            dev = Device(ip=gateway_info["ip"], token=gateway_info["token"], timeout=5)
            props_list = [{"siid": d.get("siid", 2), "piid": 1, "did": d.get("did")} for d in mesh_devices]
            props = dev.send("get_properties", props_list, retry_count=2)
            if isinstance(props, list):
                for i, p in enumerate(props):
                    if i < len(mesh_devices):
                        d = mesh_devices[i]
                        if p.get("code") == 0:
                            batch_results[d["id"]] = {"online": True, "power": p.get("value")}
                        else:
                            batch_results[d["id"]] = {"online": True, "power": None}
        except Exception:
            for d in mesh_devices:
                batch_results[d["id"]] = {"online": False, "power": None}
        return batch_results
    
    with ThreadPoolExecutor(max_workers=15) as executor:
        futures = {executor.submit(query_single_device, d, gateway_map): d for d in non_mesh_devices}
        
        for gid, mesh_devices in mesh_by_gateway.items():
            gateway_info = gateway_map.get(gid)
            if gateway_info:
                futures[executor.submit(query_mesh_batch, gid, gateway_info, mesh_devices)] = ("mesh_batch", gid)
        
        for future in as_completed(futures, timeout=30):
            try:
                result = future.result(timeout=8)
                if isinstance(result, dict):
                    for device_id, device_result in result.items():
                        results[device_id] = device_result
                elif isinstance(result, tuple):
                    device_id, device_result = result
                    results[device_id] = device_result
            except Exception:
                pass
    
    return results

def query_single_device_status(dev):
    gateway_map = {d["id"]: d for d in ALL_DEVICES if d.get("type") == "gateway"}
    _, result = query_single_device(dev, gateway_map)
    return result

def control_device(dev, power_on):
    try:
        if dev.get("type") == "mesh_switch" and dev.get("gateway_id"):
            gateway = DEVICE_MAP.get(dev["gateway_id"])
            if gateway:
                gw = Device(ip=gateway["ip"], token=gateway["token"], timeout=3)
                siid = dev.get("siid", 2)
                gw.send("set_properties", [{"siid": siid, "piid": 1, "value": power_on, "did": dev.get("did")}], retry_count=1)
                return True
        else:
            d = Device(ip=dev["ip"], token=dev["token"], timeout=3)
            d.send("set_properties", [{"siid": 2, "piid": 1, "value": power_on, "did": dev["id"]}], retry_count=1)
            return True
    except Exception:
        return False
    return False

def refresh_cache_background():
    global device_cache, cache_last_update
    
    devices = get_display_devices()
    result = query_all_devices_parallel(devices)
    
    with cache_lock:
        device_cache = result
        cache_last_update = time.time()

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
    
    result = query_all_devices_parallel(devices)
    with cache_lock:
        device_cache = result
        cache_last_update = time.time()
    return jsonify(result)

@app.route("/api/status/<device_id>")
def api_status(device_id):
    global device_cache
    dev = DEVICE_MAP.get(device_id)
    if not dev:
        return jsonify({"error": "Device not found"}), 404
    
    result = query_single_device_status(dev)
    with cache_lock:
        if device_cache is not None:
            device_cache[device_id] = result
    return jsonify(result)

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
    
    with cache_lock:
        if device_cache is not None:
            device_cache[device_id]["power"] = body["power"]
            device_cache[device_id]["online"] = True
    
    def async_control():
        control_device(dev, body["power"])
    
    threading.Thread(target=async_control, daemon=True).start()
    
    return jsonify({"ok": True, "power": body["power"]})

@app.route("/api/devices/all")
def api_devices_all():
    config = load_config()
    all_devices = get_all_devices()
    display_ids = set(config.get("display_devices", []))
    devices_info = []
    for d in all_devices:
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

@app.route("/api/devices/batch-add", methods=["POST"])
def api_batch_add_devices():
    body = request.get_json() or {}
    devices = body.get("devices", [])
    
    if not devices:
        return jsonify({"error": "没有选择设备"}), 400
    
    try:
        config = load_config()
        existing_devices = config.get("devices", [])
        existing_ips = {d.get("ip") for d in existing_devices if d.get("ip")}
        display_devices = config.get("display_devices", [])
        
        added_count = 0
        for device in devices:
            ip = device.get("ip")
            token = device.get("token")
            
            if not ip or not token:
                continue
            
            if ip in existing_ips:
                for d in existing_devices:
                    if d.get("ip") == ip:
                        d["name"] = device.get("name", d.get("name"))
                        d["token"] = token
                        break
            else:
                device_id = f"added_{uuid.uuid4().hex[:8]}"
                device_type = device.get("type") or get_device_type_from_model(device.get("model"))
                new_device = {
                    "id": device_id,
                    "name": device.get("name", device.get("model", "新设备")),
                    "ip": ip,
                    "token": token,
                    "type": device_type,
                    "model": device.get("model")
                }
                existing_devices.append(new_device)
            added_count += 1
        
        config["devices"] = existing_devices
        config["display_devices"] = display_devices
        
        save_config(config)
        
        global DEVICE_MAP
        DEVICE_MAP = get_device_map()
        
        return jsonify({"ok": True, "added_count": added_count})
    except PermissionError as e:
        return jsonify({"error": f"保存配置失败: 权限不足 ({str(e)})"}), 500
    except Exception as e:
        return jsonify({"error": f"批量添加失败: {str(e)}"}), 500

@app.route("/api/devices/scan", methods=["POST"])
def api_scan_devices():
    return jsonify({"ok": True, "message": "扫描功能暂不可用"})

@app.route("/api/cloud/status")
def api_cloud_status():
    has_credentials = cloud_connector.load_credentials()
    return jsonify({
        "has_credentials": has_credentials,
        "username": cloud_connector._username if has_credentials else None
    })

@app.route("/api/cloud/qr", methods=["POST"])
def api_cloud_qr():
    info = cloud_connector.get_qr_login_info()
    if info:
        return jsonify({"ok": True, "login_url": info["login_url"]})
    return jsonify({"error": "获取二维码失败"}), 500

@app.route("/api/cloud/qr/image")
def api_cloud_qr_image():
    image_data = cloud_connector.get_qr_image()
    if image_data:
        from flask import Response
        return Response(image_data, mimetype='image/png')
    return jsonify({"error": "获取二维码图片失败"}), 500

@app.route("/api/cloud/qr/wait", methods=["POST"])
def api_cloud_qr_wait():
    success, message = cloud_connector.wait_for_qr_scan()
    if success:
        cloud_connector.save_credentials()
        return jsonify({"ok": True, "message": message})
    return jsonify({"ok": False, "error": message}), 401

@app.route("/api/cloud/qr/check", methods=["POST"])
def api_cloud_qr_check():
    success, message = cloud_connector.check_qr_status()
    if success is None:
        return jsonify({"status": "waiting", "message": message})
    elif success:
        try:
            cloud_connector.save_credentials()
        except Exception:
            pass
        return jsonify({"status": "success", "message": message})
    else:
        return jsonify({"status": "error", "error": message})

@app.route("/api/cloud/login", methods=["POST"])
def api_cloud_login():
    success, message = cloud_connector.login()
    if success:
        return jsonify({"ok": True, "message": message})
    return jsonify({"ok": False, "error": message}), 401

@app.route("/api/cloud/scan", methods=["POST"])
def api_cloud_scan():
    if not cloud_connector._serviceToken:
        if not cloud_connector.load_credentials():
            return jsonify({"error": "请先登录米家账号"}), 401
        success, message = cloud_connector.login()
        if not success:
            return jsonify({"error": message}), 401
    
    devices = cloud_connector.scan_all_devices()
    if devices is None:
        return jsonify({"error": "扫描设备失败，请重新登录"}), 500
    
    existing_devices = get_all_devices()
    existing_ips = {d.get("ip") for d in existing_devices if d.get("ip")}
    existing_dids = {d.get("did") for d in existing_devices if d.get("did")}
    
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
    
    try:
        config = load_config()
        config["scanned_devices"] = new_devices
        save_config(config)
    except Exception:
        pass
    
    return jsonify({
        "ok": True,
        "devices": new_devices,
        "total": len(devices),
        "new_count": len(new_devices)
    })

@app.route("/api/cloud/scanned")
def api_cloud_scanned():
    config = load_config()
    scanned = config.get("scanned_devices", [])
    return jsonify(scanned)

@app.route("/api/devices/add", methods=["POST"])
def api_add_device():
    body = request.get_json() or {}
    name = body.get("name")
    ip = body.get("ip")
    token = body.get("token")
    model = body.get("model")
    device_type = body.get("type")
    
    if not ip or not token:
        return jsonify({"error": "缺少必要参数"}), 400
    
    if not device_type:
        device_type = get_device_type_from_model(model)
    
    device_id = f"added_{uuid.uuid4().hex[:8]}"
    
    new_device = {
        "id": device_id,
        "name": name or model or "新设备",
        "ip": ip,
        "token": token,
        "type": device_type,
        "model": model
    }
    
    try:
        config = load_config()
        devices = config.get("devices", [])
        
        for d in devices:
            if d.get("ip") == ip:
                d["name"] = new_device["name"]
                d["token"] = token
                d["type"] = device_type
                save_config(config)
                global DEVICE_MAP
                DEVICE_MAP = get_device_map()
                return jsonify({"ok": True, "device": d, "updated": True})
        
        devices.append(new_device)
        config["devices"] = devices
        
        if device_id not in config.get("display_devices", []):
            config["display_devices"] = config.get("display_devices", []) + [device_id]
        
        save_config(config)
        
        DEVICE_MAP = get_device_map()
        
        return jsonify({"ok": True, "device": new_device, "updated": False})
    except Exception as e:
        return jsonify({"error": f"添加设备失败: {str(e)}"}), 500

@app.route("/api/devices/delete/<device_id>", methods=["POST"])
def api_delete_device(device_id):
    config = load_config()
    devices = config.get("devices", [])
    
    device_to_delete = None
    for d in devices:
        if d["id"] == device_id:
            device_to_delete = d
            break
    
    if not device_to_delete:
        return jsonify({"error": "设备不存在"}), 404
    
    if not device_id.startswith("added_"):
        return jsonify({"error": "只能删除通过扫描添加的设备"}), 400
    
    devices = [d for d in devices if d["id"] != device_id]
    config["devices"] = devices
    
    if device_id in config.get("display_devices", []):
        config["display_devices"] = [d for d in config.get("display_devices", []) if d != device_id]
    
    save_config(config)
    
    global DEVICE_MAP
    DEVICE_MAP = get_device_map()
    
    return jsonify({"ok": True})

@app.route("/api/devices/rename/<device_id>", methods=["POST"])
def api_rename_device(device_id):
    body = request.get_json() or {}
    new_name = body.get("name")
    
    if not new_name:
        return jsonify({"error": "请提供新名称"}), 400
    
    config = load_config()
    devices = config.get("devices", [])
    
    found = False
    for d in devices:
        if d["id"] == device_id:
            d["name"] = new_name
            found = True
            break
    
    if not found:
        return jsonify({"error": "设备不存在或无法重命名"}), 404
    
    save_config(config)
    
    global DEVICE_MAP
    DEVICE_MAP = get_device_map()
    
    return jsonify({"ok": True, "name": new_name})

def main():
    print("启动米家控制面板，访问 http://localhost:5001")
    print("设备管理页面，访问 http://localhost:5001/manage")
    start_background_refresh()
    app.run(host="127.0.0.1", port=5001, debug=False, threaded=True)

if __name__ == "__main__":
    main()

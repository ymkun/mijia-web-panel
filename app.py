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

CONTROLLABLE_TYPES = {"light", "airconditioner", "humidifier", "plug", "mesh_switch"}
AIR_PROPS = ["co2", "humidity", "temperature", "pm25", "tvoc"]

MODEL_TYPE_MAP = {
    "yeelink.switch.": "mesh_switch",
    "yeelink.": "light",
    "zhimi.airpurifier.": "airconditioner",
    "zhimi.humidifier.": "humidifier",
    "zhimi.airmonitor.": "sensor",
    "cgllc.airmonitor.": "sensor",
    "lumi.gateway.": "gateway",
    "lumi.sensor_": "sensor",
    "lumi.ctrl_": "mesh_switch",
    "lumi.switch.": "mesh_switch",
    "xiaomi.gateway.": "gateway",
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
scanned_devices_cache = []

def aggregate_scanned_mesh_switches(devices):
    mesh_switches = [d for d in devices if d.get("type") == "mesh_switch"]
    other_devices = [d for d in devices if d.get("type") != "mesh_switch"]
    
    grouped = {}
    for d in mesh_switches:
        did = d.get("did")
        if not did:
            other_devices.append(d)
            continue
        if did not in grouped:
            grouped[did] = {
                "name": d.get("name", "智能开关"),
                "did": did,
                "model": d.get("model"),
                "type": "mesh_switch_group",
                "is_ble_mesh": True,
                "is_existing": False,
                "sub_switches": []
            }
        grouped[did]["sub_switches"].append({
            "name": d.get("name", "开关"),
            "siid": d.get("siid", 2)
        })
        if d.get("is_existing"):
            grouped[did]["is_existing"] = True
    
    for group in grouped.values():
        group["sub_switches"].sort(key=lambda x: x.get("siid") or 0)
    
    return other_devices + list(grouped.values())

def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                config = json.load(f)
            config.pop("scanned_devices", None)
            if "gateways" not in config:
                config["gateways"] = []
            return config
        except (json.JSONDecodeError, Exception):
            pass
    return {
        "devices": [],
        "display_devices": [],
        "gateways": []
    }

def save_config(config):
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=2)

def get_all_devices():
    config = load_config()
    return config.get("devices", [])

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
    
    return aggregate_mesh_switches(devices)

def get_device_map():
    all_devices = get_all_devices()
    return {d["id"]: d for d in all_devices}

def aggregate_mesh_switches(devices):
    mesh_devices = [d for d in devices if d.get("type") == "mesh_switch"]
    non_mesh_devices = [d for d in devices if d.get("type") != "mesh_switch"]
    
    grouped = {}
    for d in mesh_devices:
        did = d.get("did")
        siid = d.get("siid")
        
        if did not in grouped:
            grouped[did] = {
                "id": f"mesh_group_{did}",
                "name": d.get("name", "智能开关"),
                "type": "mesh_switch_group",
                "gateway_id": d.get("gateway_id"),
                "did": did,
                "controllable": True,
                "sub_switches": [],
                "main_device": None
            }
        
        if siid is None:
            grouped[did]["name"] = d.get("name", grouped[did]["name"])
            grouped[did]["main_device"] = d
        else:
            grouped[did]["sub_switches"].append({
                "id": d["id"],
                "name": d.get("name", "开关"),
                "siid": siid,
                "did": did
            })
    
    result_groups = []
    for group in grouped.values():
        sub_count = len(group["sub_switches"])
        
        if sub_count == 0 and group["main_device"]:
            main = group["main_device"]
            single_device = {
                "id": main["id"],
                "name": main["name"],
                "type": "mesh_switch",
                "gateway_id": group["gateway_id"],
                "did": group["did"],
                "siid": 2,
                "controllable": True,
                "is_single_switch": True
            }
            result_groups.append(single_device)
        elif sub_count == 1:
            single_device = {
                "id": group["sub_switches"][0]["id"],
                "name": group["sub_switches"][0]["name"],
                "type": "mesh_switch",
                "gateway_id": group["gateway_id"],
                "did": group["did"],
                "siid": group["sub_switches"][0]["siid"],
                "controllable": True,
                "is_single_switch": True
            }
            result_groups.append(single_device)
        elif sub_count > 1:
            group["sub_switches"].sort(key=lambda x: x.get("siid") or 0)
            result_groups.append(group)
    
    return non_mesh_devices + result_groups

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
        elif d.get("type") == "sensor":
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
    config = load_config()
    gateways_list = config.get("gateways", [])
    gateway_map = {g.get("did"): g for g in gateways_list}
    
    mesh_by_gateway = {}
    non_mesh_devices = []
    for d in devices:
        if d.get("type") == "mesh_switch_group":
            for sub in d.get("sub_switches", []):
                gid = d.get("gateway_id")
                if gid and gateway_map.get(gid):
                    if gid not in mesh_by_gateway:
                        mesh_by_gateway[gid] = []
                    mesh_by_gateway[gid].append({
                        "siid": sub.get("siid", 2),
                        "id": sub["id"],
                        "did": d.get("did"),
                        "group_id": d["id"]
                    })
        elif d.get("type") == "mesh_switch" and d.get("gateway_id"):
            gid = d["gateway_id"]
            siid = d.get("siid") or 2
            if gid not in mesh_by_gateway:
                mesh_by_gateway[gid] = []
            mesh_by_gateway[gid].append({"siid": siid, "id": d["id"], "did": d.get("did")})
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
                            batch_results[d["id"]] = {"online": False, "power": None}
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
    
    group_results = {}
    for d in devices:
        if d.get("type") == "mesh_switch_group":
            group_id = d["id"]
            sub_results = {}
            all_online = False
            for sub in d.get("sub_switches", []):
                sub_id = sub["id"]
                if sub_id in results:
                    sub_results[sub_id] = results[sub_id]
                    if results[sub_id].get("online"):
                        all_online = True
            group_results[group_id] = {
                "online": all_online,
                "sub_switches": sub_results
            }
    
    results.update(group_results)
    
    return results

def query_single_device_status(dev):
    config = load_config()
    gateways_list = config.get("gateways", [])
    gateway_map = {g.get("did"): g for g in gateways_list}
    _, result = query_single_device(dev, gateway_map)
    return result

def control_device(dev, power_on):
    try:
        if dev.get("type") == "mesh_switch" and dev.get("gateway_id"):
            config = load_config()
            gateways_list = config.get("gateways", [])
            gateway_map = {g.get("did"): g for g in gateways_list}
            gateway = gateway_map.get(dev["gateway_id"])
            if gateway:
                gw = Device(ip=gateway["ip"], token=gateway["token"], timeout=3)
                siid = dev.get("siid") or 2
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
    aggregated_devices = aggregate_mesh_switches(devices)
    devices_meta = []
    for d in aggregated_devices:
        meta = {"id": d["id"], "name": d["name"], "type": d["type"],
                "controllable": d.get("controllable", d["type"] in CONTROLLABLE_TYPES)}
        if d["type"] == "mesh_switch_group":
            meta["sub_switches"] = d.get("sub_switches", [])
            meta["gateway_id"] = d.get("gateway_id")
            meta["did"] = d.get("did")
        devices_meta.append(meta)
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
            return jsonify(build_aggregated_status(device_cache))
    
    result = query_all_devices_parallel(devices)
    with cache_lock:
        device_cache = result
        cache_last_update = time.time()
    return jsonify(build_aggregated_status(result))

def build_aggregated_status(raw_status):
    devices = get_display_devices()
    aggregated = aggregate_mesh_switches(devices)
    result = {}
    
    for d in aggregated:
        if d["type"] == "mesh_switch_group":
            group_status = {
                "online": False,
                "sub_switches": {}
            }
            any_online = False
            for sub in d.get("sub_switches", []):
                sub_status = raw_status.get(sub["id"], {"online": False, "power": None})
                group_status["sub_switches"][sub["id"]] = sub_status
                if sub_status.get("online"):
                    any_online = True
            group_status["online"] = any_online
            result[d["id"]] = group_status
        else:
            result[d["id"]] = raw_status.get(d["id"], {"online": False, "power": None})
    
    return result

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

@app.route("/api/mesh/status/<mesh_group_id>")
def api_mesh_status(mesh_group_id):
    global device_cache
    devices = get_display_devices()
    aggregated = aggregate_mesh_switches(devices)
    
    mesh_group = None
    for d in aggregated:
        if d["id"] == mesh_group_id and d["type"] == "mesh_switch_group":
            mesh_group = d
            break
    
    if not mesh_group:
        return jsonify({"error": "Mesh group not found"}), 404
    
    result = {"online": False, "sub_switches": {}}
    any_online = False
    
    for sub in mesh_group.get("sub_switches", []):
        sub_dev = DEVICE_MAP.get(sub["id"])
        if sub_dev:
            sub_status = query_single_device_status(sub_dev)
            result["sub_switches"][sub["id"]] = sub_status
            if sub_status.get("online"):
                any_online = True
            with cache_lock:
                if device_cache is not None:
                    device_cache[sub["id"]] = sub_status
    
    result["online"] = any_online
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
    global scanned_devices_cache
    config = load_config()
    display_ids = set(config.get("display_devices", []))
    devices_info = []
    for d in scanned_devices_cache:
        devices_info.append({
            "id": d.get("id", d.get("did", "")),
            "name": d["name"],
            "type": d["type"],
            "controllable": d["type"] in CONTROLLABLE_TYPES,
            "display": d.get("id", d.get("did", "")) in display_ids
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
        existing_mesh_keys = {(d.get("did"), d.get("siid")) for d in existing_devices if d.get("type") == "mesh_switch"}
        gateways = config.get("gateways", [])
        default_gateway = gateways[0].get("did") if gateways else None
        
        added_count = 0
        for device in devices:
            ip = device.get("ip", "")
            token = device.get("token", "")
            did = device.get("did", "")
            device_type = device.get("type", "")
            sub_switches = device.get("sub_switches", [])
            
            if device_type == "mesh_switch_group":
                if not did or not sub_switches:
                    continue
                
                for sub in sub_switches:
                    sub_siid = sub.get("siid", 2)
                    mesh_key = (did, sub_siid)
                    
                    if mesh_key in existing_mesh_keys:
                        for d in existing_devices:
                            if d.get("did") == did and d.get("siid") == sub_siid:
                                d["name"] = sub.get("name", d.get("name"))
                                break
                    else:
                        device_id = uuid.uuid4().hex[:8]
                        new_device = {
                            "id": device_id,
                            "name": sub.get("name", "开关"),
                            "did": did,
                            "siid": sub_siid,
                            "ip": "",
                            "token": token,
                            "type": "mesh_switch",
                            "gateway_id": default_gateway,
                            "model": device.get("model")
                        }
                        existing_devices.append(new_device)
                        existing_mesh_keys.add(mesh_key)
                        added_count += 1
                continue
            
            is_ble_mesh = device.get("is_ble_mesh") or not ip
            
            if is_ble_mesh:
                if not did:
                    continue
                
                parsed_did = did
                siid = None
                if "." in did and did.split(".")[-1].startswith("s"):
                    parts = did.split(".")
                    parsed_did = parts[0]
                    try:
                        siid = int(parts[1][1:])
                    except ValueError:
                        pass
                
                if siid is not None:
                    mesh_key = (parsed_did, siid)
                    if mesh_key in existing_mesh_keys:
                        for d in existing_devices:
                            if d.get("did") == parsed_did and d.get("siid") == siid:
                                d["name"] = device.get("name", d.get("name"))
                                break
                    else:
                        device_id = uuid.uuid4().hex[:8]
                        new_device = {
                            "id": device_id,
                            "name": device.get("name", device.get("model", "新设备")),
                            "did": parsed_did,
                            "siid": siid,
                            "ip": "",
                            "token": token,
                            "type": "mesh_switch",
                            "gateway_id": default_gateway,
                            "model": device.get("model")
                        }
                        existing_devices.append(new_device)
                        existing_mesh_keys.add(mesh_key)
                        added_count += 1
                else:
                    if did in {d.get("did") for d in existing_devices}:
                        for d in existing_devices:
                            if d.get("did") == did:
                                d["name"] = device.get("name", d.get("name"))
                                break
                    else:
                        device_id = uuid.uuid4().hex[:8]
                        device_type = device.get("type") or get_device_type_from_model(device.get("model"))
                        new_device = {
                            "id": device_id,
                            "name": device.get("name", device.get("model", "新设备")),
                            "did": did,
                            "ip": "",
                            "token": token,
                            "type": device_type,
                            "model": device.get("model"),
                            "is_ble_mesh": True
                        }
                        existing_devices.append(new_device)
                        added_count += 1
            else:
                if not ip or not token:
                    continue
                if ip in existing_ips:
                    for d in existing_devices:
                        if d.get("ip") == ip:
                            d["name"] = device.get("name", d.get("name"))
                            d["token"] = token
                            break
                else:
                    device_id = uuid.uuid4().hex[:8]
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
    existing_mesh_keys = {(d.get("did"), d.get("siid")) for d in existing_devices if d.get("type") == "mesh_switch"}
    
    config = load_config()
    saved_gateways = {g.get("did"): g for g in config.get("gateways", [])}
    
    all_scanned = []
    scanned_gateways = []
    for d in devices:
        device_type = get_device_type_from_model(d.get("model"))
        ip = d.get("ip")
        did = d.get("did")
        
        if device_type == "gateway" and ip:
            gateway_info = {
                "did": did,
                "name": d["name"],
                "ip": ip,
                "token": d.get("token", ""),
                "model": d["model"]
            }
            if did not in saved_gateways:
                scanned_gateways.append(gateway_info)
                saved_gateways[did] = gateway_info
            else:
                saved_gateways[did].update(gateway_info)
        
        parsed_did = did
        siid = None
        if did and "." in did and did.split(".")[-1].startswith("s"):
            parts = did.split(".")
            parsed_did = parts[0]
            try:
                siid = int(parts[1][1:])
            except ValueError:
                pass
        
        is_existing = False
        if ip and ip in existing_ips:
            is_existing = True
        elif parsed_did and siid and (parsed_did, siid) in existing_mesh_keys:
            is_existing = True
        elif did and did in {d.get("did") for d in existing_devices} and not ip:
            is_existing = True
        
        device_data = {
            "name": d["name"],
            "did": parsed_did or did,
            "siid": siid,
            "ip": ip or "",
            "token": d.get("token", ""),
            "mac": d.get("mac", ""),
            "model": d["model"],
            "type": device_type,
            "controllable": device_type in CONTROLLABLE_TYPES,
            "is_existing": is_existing,
            "is_ble_mesh": not ip and did
        }
        all_scanned.append(device_data)
    
    if scanned_gateways:
        config["gateways"] = list(saved_gateways.values())
        save_config(config)
    
    aggregated = aggregate_scanned_mesh_switches(all_scanned)
    
    global scanned_devices_cache
    scanned_devices_cache = aggregated
    
    return jsonify({
        "ok": True,
        "devices": aggregated,
        "total": len(devices)
    })

@app.route("/api/cloud/scanned")
def api_cloud_scanned():
    global scanned_devices_cache
    return jsonify(scanned_devices_cache)

@app.route("/api/devices/add", methods=["POST"])
def api_add_device():
    global DEVICE_MAP
    body = request.get_json() or {}
    name = body.get("name")
    ip = body.get("ip", "")
    token = body.get("token", "")
    model = body.get("model")
    device_type = body.get("type")
    did = body.get("did", "")
    siid = body.get("siid")
    is_ble_mesh = body.get("is_ble_mesh") or not ip
    sub_switches = body.get("sub_switches", [])
    
    if device_type == "mesh_switch_group":
        if not did:
            return jsonify({"error": "缺少设备DID"}), 400
        if not sub_switches:
            return jsonify({"error": "缺少子设备信息"}), 400
        
        try:
            config = load_config()
            devices = config.get("devices", [])
            gateways = config.get("gateways", [])
            default_gateway = gateways[0].get("did") if gateways else None
            
            if not default_gateway:
                return jsonify({"error": "未找到网关，请先扫描设备"}), 400
            
            added_count = 0
            for sub in sub_switches:
                sub_siid = sub.get("siid", 2)
                existing_mesh_keys = {(d.get("did"), d.get("siid")) for d in devices if d.get("type") == "mesh_switch"}
                
                if (did, sub_siid) not in existing_mesh_keys:
                    device_id = uuid.uuid4().hex[:8]
                    new_device = {
                        "id": device_id,
                        "name": sub.get("name", "开关"),
                        "did": did,
                        "siid": sub_siid,
                        "ip": "",
                        "token": token,
                        "type": "mesh_switch",
                        "gateway_id": default_gateway,
                        "model": model
                    }
                    devices.append(new_device)
                    added_count += 1
            
            config["devices"] = devices
            save_config(config)
            DEVICE_MAP = get_device_map()
            return jsonify({"ok": True, "added_count": added_count, "updated": False})
        except PermissionError as e:
            return jsonify({"error": f"保存配置失败: 权限不足 ({str(e)})"}), 500
        except Exception as e:
            return jsonify({"error": f"添加失败: {str(e)}"}), 500
    
    if is_ble_mesh:
        if not did:
            return jsonify({"error": "缺少设备DID"}), 400
        
        parsed_did = did
        parsed_siid = siid
        if "." in did and did.split(".")[-1].startswith("s"):
            parts = did.split(".")
            parsed_did = parts[0]
            try:
                parsed_siid = int(parts[1][1:])
            except ValueError:
                pass
        
        if parsed_siid is None:
            parsed_siid = 2
        
        try:
            config = load_config()
            devices = config.get("devices", [])
            gateways = {d["id"]: d for d in devices if d.get("type") == "gateway"}
            default_gateway = list(gateways.keys())[0] if gateways else None
            
            for d in devices:
                if d.get("did") == parsed_did and d.get("siid") == parsed_siid:
                    d["name"] = name or d.get("name")
                    save_config(config)
                    DEVICE_MAP = get_device_map()
                    return jsonify({"ok": True, "device": d, "updated": True})
            
            device_id = uuid.uuid4().hex[:8]
            new_device = {
                "id": device_id,
                "name": name or model or "新设备",
                "did": parsed_did,
                "siid": parsed_siid,
                "ip": "",
                "token": token,
                "type": "mesh_switch",
                "gateway_id": default_gateway,
                "model": model
            }
            devices.append(new_device)
            config["devices"] = devices
            
            if device_id not in config.get("display_devices", []):
                config["display_devices"] = config.get("display_devices", []) + [device_id]
            
            save_config(config)
            DEVICE_MAP = get_device_map()
            return jsonify({"ok": True, "device": new_device, "updated": False})
        except PermissionError as e:
            return jsonify({"error": f"保存配置失败: 权限不足 ({str(e)})"}), 500
        except Exception as e:
            return jsonify({"error": f"添加失败: {str(e)}"}), 500
    
    if not ip or not token:
        return jsonify({"error": "缺少必要参数"}), 400
    
    if not device_type:
        device_type = get_device_type_from_model(model)
    
    device_id = uuid.uuid4().hex[:8]
    
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

@app.route("/api/config/reset", methods=["POST"])
def api_reset_config():
    global DEVICE_MAP
    try:
        config = {"devices": [], "display_devices": []}
        save_config(config)
        DEVICE_MAP = {}
        return jsonify({"ok": True, "message": "配置已重置"})
    except Exception as e:
        return jsonify({"error": f"重置失败: {str(e)}"}), 500

def main():
    global DEVICE_MAP
    DEVICE_MAP = get_device_map()
    print("启动米家控制面板，访问 http://localhost:5001")
    print("设备管理页面，访问 http://localhost:5001/manage")
    start_background_refresh()
    app.run(host="127.0.0.1", port=5001, debug=False, threaded=True)

if __name__ == "__main__":
    main()

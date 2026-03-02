import json
import subprocess
import sys

from flask import Flask, jsonify, request, render_template

app = Flask(__name__)

DEVICES = [
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
]

CONTROLLABLE_TYPES = {"light", "airconditioner", "humidifier", "plug"}
DEVICE_MAP = {d["id"]: d for d in DEVICES}

_MIIO_GET = """\
import warnings; warnings.filterwarnings("ignore")
import json, sys
from miio import Device
ip, token, did = sys.argv[1], sys.argv[2], sys.argv[3]
dev = Device(ip=ip, token=token, timeout=4)
props = dev.send("get_properties", [{"siid": 2, "piid": 1, "did": did}], retry_count=1)
power = props[0].get("value") if props and props[0].get("code") == 0 else None
print(json.dumps({"online": True, "power": power}))
"""

# Batch query: reads a JSON list of {id,ip,token,type} from stdin, queries all in parallel threads
_MIIO_GET_ALL = """\
import warnings; warnings.filterwarnings("ignore")
import json, sys, threading
from miio import Device

devices = json.loads(sys.argv[1])
results = {}

AIR_PROPS = ["co2", "humidity", "temperature", "pm25", "tvoc"]

def query(d):
    try:
        dev = Device(ip=d["ip"], token=d["token"], timeout=3)
        # Sensors: use device-specific get_prop
        if d.get("type") == "sensor" and d.get("id") == "sensor_air":
            r = dev.send("get_prop", AIR_PROPS, retry_count=0)
            if isinstance(r, dict):
                readings = {k: r[k] for k in AIR_PROPS if k in r}
                results[d["id"]] = {"online": True, "power": None, "readings": readings}
                return
        # Speakers: get_properties not supported, use miIO.info to confirm online
        if d.get("type") == "speaker":
            dev.send("miIO.info", [], retry_count=0)
            results[d["id"]] = {"online": True, "power": None}
            return
        # All other devices: standard MioT get_properties
        props = dev.send("get_properties", [{"siid": 2, "piid": 1, "did": d["id"]}], retry_count=0)
        if isinstance(props, list) and props and props[0].get("code") == 0:
            power = props[0].get("value")
        else:
            power = None
        results[d["id"]] = {"online": True, "power": power}
    except Exception:
        results[d["id"]] = {"online": False, "power": None}

threads = [threading.Thread(target=query, args=(d,)) for d in devices]
for t in threads: t.start()
for t in threads: t.join()
print(json.dumps(results))
"""

_MIIO_SET = """\
import warnings; warnings.filterwarnings("ignore")
import json, sys
from miio import Device
ip, token, did, val = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]
dev = Device(ip=ip, token=token, timeout=4)
dev.send("set_properties", [{"siid": 2, "piid": 1, "value": val == "true", "did": did}], retry_count=1)
print(json.dumps({"ok": True}))
"""


def _run_miio(script, args, timeout=7):
    """Run a miio snippet in a subprocess with strict timeout."""
    result = subprocess.run(
        [sys.executable, "-c", script] + args,
        capture_output=True, text=True, timeout=timeout
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip().splitlines()[-1] if result.stderr.strip() else "error")
    return json.loads(result.stdout.strip())


@app.route("/")
def index():
    devices_meta = [
        {"id": d["id"], "name": d["name"], "type": d["type"],
         "controllable": d["type"] in CONTROLLABLE_TYPES}
        for d in DEVICES
    ]
    return render_template("index.html", devices=devices_meta)


@app.route("/api/status/all")
def api_status_all():
    """Query all devices in one subprocess (threads inside), much faster than 15 serial requests."""
    payload = json.dumps([{"id": d["id"], "ip": d["ip"], "token": d["token"], "type": d["type"]} for d in DEVICES])
    try:
        result = _run_miio(_MIIO_GET_ALL, [payload], timeout=10)
        return jsonify(result)
    except subprocess.TimeoutExpired:
        return jsonify({d["id"]: {"online": False, "power": None} for d in DEVICES})
    except Exception as e:
        return jsonify({d["id"]: {"online": False, "power": None} for d in DEVICES})


@app.route("/api/status/<device_id>")
def api_status(device_id):
    dev = DEVICE_MAP.get(device_id)
    if not dev:
        return jsonify({"error": "Device not found"}), 404
    try:
        result = _run_miio(_MIIO_GET, [dev["ip"], dev["token"], device_id])
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
        result = _run_miio(_MIIO_SET, [dev["ip"], dev["token"], device_id, power_str])
        result["power"] = body["power"]
        return jsonify(result)
    except subprocess.TimeoutExpired:
        return jsonify({"ok": False, "error": "timeout"})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)})


if __name__ == "__main__":
    print("启动米家控制面板，访问 http://localhost:5001")
    app.run(host="127.0.0.1", port=5001, debug=False)

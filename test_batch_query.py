import warnings
warnings.filterwarnings("ignore")
import json
import sys
import threading
from miio import Device

# 测试批量查询逻辑
def test_batch_query():
    # 模拟设备数据
    devices = [
        {
            "id": "light_master",
            "ip": "192.168.3.18",
            "token": "e71ca3aa999c0915bb35dcfd129ee833",
            "type": "light",
            "gateway_id": "",
            "did": ""
        }
    ]
    
    results = {}
    AIR_PROPS = ["co2", "humidity", "temperature", "pm25", "tvoc"]
    gateway_map = {d["id"]: d for d in devices if d.get("type") == "gateway"}
    
    def query(d):
        try:
            # 处理蓝牙Mesh设备
            if d.get("type") == "mesh_switch" and d.get("gateway_id"):
                gateway = gateway_map.get(d["gateway_id"])
                if gateway:
                    try:
                        # 连接到网关
                        dev = Device(ip=gateway["ip"], token=gateway["token"], timeout=3)
                        # 通过网关查询蓝牙Mesh设备状态
                        # 增加重试次数，提高成功率
                        props = dev.send("get_properties", [{"siid": 2, "piid": 1, "did": d.get("did")}], retry_count=2)
                        if isinstance(props, list) and props and props[0].get("code") == 0:
                            power = props[0].get("value")
                        else:
                            power = None
                        results[d["id"]] = {"online": True, "power": power}
                    except Exception as e:
                        # 单独处理网关查询失败的情况
                        print(f"Gateway query error: {e}")
                        results[d["id"]] = {"online": False, "power": None}
                else:
                    results[d["id"]] = {"online": False, "power": None}
                return
            
            # Sensors: use device-specific get_prop
            if d.get("type") == "sensor" and d.get("id") == "sensor_air":
                dev = Device(ip=d["ip"], token=d["token"], timeout=3)
                r = dev.send("get_prop", AIR_PROPS, retry_count=0)
                if isinstance(r, dict):
                    readings = {k: r[k] for k in AIR_PROPS if k in r}
                    results[d["id"]] = {"online": True, "power": None, "readings": readings}
                    return
            # Speakers: get_properties not supported, use miIO.info to confirm online
            if d.get("type") == "speaker":
                dev = Device(ip=d["ip"], token=d["token"], timeout=3)
                dev.send("miIO.info", [], retry_count=0)
                results[d["id"]] = {"online": True, "power": None}
                return
            # Gateways: use miIO.info to confirm online
            if d.get("type") == "gateway":
                dev = Device(ip=d["ip"], token=d["token"], timeout=3)
                dev.send("miIO.info", [], retry_count=0)
                results[d["id"]] = {"online": True, "power": None}
                return
            # All other devices: standard MioT get_properties
            dev = Device(ip=d["ip"], token=d["token"], timeout=3)
            props = dev.send("get_properties", [{"siid": 2, "piid": 1, "did": d["id"]}], retry_count=0)
            if isinstance(props, list) and props and props[0].get("code") == 0:
                power = props[0].get("value")
            else:
                power = None
            results[d["id"]] = {"online": True, "power": power}
        except Exception as e:
            print(f"Query error for {d['id']}: {e}")
            results[d["id"]] = {"online": False, "power": None}
    
    # 串行查询蓝牙Mesh设备，避免网关过载
    mesh_devices = [d for d in devices if d.get("type") == "mesh_switch"]
    other_devices = [d for d in devices if d.get("type") != "mesh_switch"]
    
    # 先并行查询非蓝牙Mesh设备
    threads = [threading.Thread(target=query, args=(d,)) for d in other_devices]
    for t in threads: t.start()
    for t in threads: t.join()
    
    # 再串行查询蓝牙Mesh设备，避免网关过载
    for d in mesh_devices:
        query(d)
    
    print(json.dumps(results, indent=2))

if __name__ == "__main__":
    test_batch_query()

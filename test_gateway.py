import json
import sys
from miio import Device

# 测试米家中枢网关通信
def test_gateway(ip, token):
    try:
        # 连接到网关
        dev = Device(ip=ip, token=token, timeout=4)
        
        # 获取网关信息
        print("获取网关信息...")
        info = dev.send("miIO.info", [])
        print(f"网关信息: {json.dumps(info, indent=2)}")
        
        # 尝试获取设备列表
        print("\n尝试获取设备列表...")
        try:
            devices = dev.send("get_device_list", [])
            print(f"设备列表: {json.dumps(devices, indent=2)}")
        except Exception as e:
            print(f"获取设备列表失败: {e}")
        
        # 尝试获取设备属性
        print("\n尝试获取设备属性...")
        try:
            props = dev.send("get_properties", [{"siid": 2, "piid": 1}])
            print(f"设备属性: {json.dumps(props, indent=2)}")
        except Exception as e:
            print(f"获取设备属性失败: {e}")
            
    except Exception as e:
        print(f"连接失败: {e}")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("用法: python test_gateway.py <网关IP> <网关Token>")
        sys.exit(1)
    
    ip = sys.argv[1]
    token = sys.argv[2]
    test_gateway(ip, token)

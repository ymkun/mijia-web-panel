import warnings
warnings.filterwarnings("ignore")
from miio import Device

# 测试不同的siid
gateway = Device(ip='192.168.3.77', token='33665268384134384864456b7a434537', timeout=5)

# 测试主设备
print("测试主设备 (siid=2):")
result = gateway.send('get_properties', [{'did': '1132827761', 'siid': 2, 'piid': 1}], retry_count=1)
print(f"结果: {result}")

# 测试siid=3
print("\n测试 siid=3:")
result = gateway.send('get_properties', [{'did': '1132827761', 'siid': 3, 'piid': 1}], retry_count=1)
print(f"结果: {result}")

# 测试siid=4
print("\n测试 siid=4:")
result = gateway.send('get_properties', [{'did': '1132827761', 'siid': 4, 'piid': 1}], retry_count=1)
print(f"结果: {result}")

# 测试siid=5
print("\n测试 siid=5:")
result = gateway.send('get_properties', [{'did': '1132827761', 'siid': 5, 'piid': 1}], retry_count=1)
print(f"结果: {result}")

# 测试siid=6
print("\n测试 siid=6:")
result = gateway.send('get_properties', [{'did': '1132827761', 'siid': 6, 'piid': 1}], retry_count=1)
print(f"结果: {result}")

# 测试siid=7
print("\n测试 siid=7:")
result = gateway.send('get_properties', [{'did': '1132827761', 'siid': 7, 'piid': 1}], retry_count=1)
print(f"结果: {result}")

# 测试siid=12
print("\n测试 siid=12:")
result = gateway.send('get_properties', [{'did': '1132827761', 'siid': 12, 'piid': 1}], retry_count=1)
print(f"结果: {result}")

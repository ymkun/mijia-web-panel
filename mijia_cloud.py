import base64
import hashlib
import json
import os
import time
import requests

try:
    from Crypto.Cipher import ARC4
except ModuleNotFoundError:
    from Cryptodome.Cipher import ARC4


class MijiaCloudConnector:
    CREDENTIALS_FILE = None

    def __init__(self, config_dir):
        from pathlib import Path
        self.CREDENTIALS_FILE = Path(config_dir) / "cloud_credentials.json"
        self._agent = self.generate_agent()
        self._device_id = self.generate_device_id()
        self._session = requests.session()
        self._ssecurity = None
        self.userId = None
        self._serviceToken = None
        self._server = "cn"
        self._qr_image_url = None
        self._login_url = None
        self._long_polling_url = None
        self._timeout = None

    def load_credentials(self):
        import os
        if self.CREDENTIALS_FILE and os.path.exists(self.CREDENTIALS_FILE):
            with open(self.CREDENTIALS_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self._ssecurity = data.get("ssecurity")
                self.userId = data.get("userId")
                self._serviceToken = data.get("serviceToken")
                return bool(self._ssecurity and self._serviceToken)
        return False

    def save_credentials(self):
        if self.CREDENTIALS_FILE:
            data = {
                "ssecurity": self._ssecurity,
                "userId": self.userId,
                "serviceToken": self._serviceToken,
                "server": self._server
            }
            with open(self.CREDENTIALS_FILE, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

    def get_qr_login_info(self):
        url = "https://account.xiaomi.com/longPolling/loginUrl"
        data = {
            "_qrsize": "480",
            "qs": "%3Fsid%3Dxiaomiio%26_json%3Dtrue",
            "callback": "https://sts.api.io.mi.com/sts",
            "_hasLogo": "false",
            "sid": "xiaomiio",
            "serviceParam": "",
            "_locale": "en_GB",
            "_dc": str(int(time.time() * 1000))
        }
        response = self._session.get(url, params=data)
        if response.status_code == 200:
            response_data = self._to_json(response.text)
            if "qr" in response_data:
                self._qr_image_url = response_data["qr"]
                self._login_url = response_data["loginUrl"]
                self._long_polling_url = response_data["lp"]
                self._timeout = response_data.get("timeout", 180)
                return {
                    "qr_url": self._qr_image_url,
                    "login_url": self._login_url
                }
        return None

    def get_qr_image(self):
        if not self._qr_image_url:
            return None
        response = self._session.get(self._qr_image_url)
        if response.status_code == 200:
            return response.content
        return None

    def check_qr_status(self):
        if not self._long_polling_url:
            return None, "未获取登录信息"
        
        try:
            response = self._session.get(self._long_polling_url, timeout=30)
        except requests.exceptions.Timeout:
            return None, "waiting"
        except requests.exceptions.RequestException as e:
            return None, f"网络错误: {str(e)}"
        
        if response.status_code == 200:
            response_data = self._to_json(response.text)
            self.userId = response_data.get("userId")
            self._ssecurity = response_data.get("ssecurity")
            self._location = response_data.get("location")
            
            if self._location:
                if self._login_step_4():
                    return True, "登录成功"
                else:
                    return False, "获取服务令牌失败"
            return False, "登录信息不完整"
        
        return None, "waiting"

    def wait_for_qr_scan(self):
        if not self._long_polling_url:
            return False, "未获取登录信息"
        
        start_time = time.time()
        while True:
            try:
                response = self._session.get(self._long_polling_url, timeout=10)
            except requests.exceptions.Timeout:
                if time.time() - start_time > self._timeout:
                    return False, "二维码已过期，请重新获取"
                continue
            except requests.exceptions.RequestException as e:
                return False, f"网络错误: {str(e)}"
            
            if response.status_code == 200:
                response_data = self._to_json(response.text)
                self.userId = response_data.get("userId")
                self._ssecurity = response_data.get("ssecurity")
                self._location = response_data.get("location")
                
                if self._location:
                    if self._login_step_4():
                        return True, "登录成功"
                    else:
                        return False, "获取服务令牌失败"
                return False, "登录信息不完整"
            
            if time.time() - start_time > self._timeout:
                return False, "二维码已过期，请重新获取"
        
        return False, "未知错误"

    def _login_step_4(self):
        if not self._location:
            return False
        response = self._session.get(self._location, headers={"content-type": "application/x-www-form-urlencoded"})
        if response.status_code != 200:
            return False
        self._serviceToken = response.cookies.get("serviceToken")
        return bool(self._serviceToken)

    def login(self):
        if self.load_credentials():
            return True, "使用已保存的凭证"
        return False, "请扫码登录"

    def scan_all_devices(self):
        all_devices = []
        homes = self.get_homes()
        if homes is None:
            return None

        home_list = []
        if "result" in homes and "homelist" in homes["result"]:
            for h in homes["result"]["homelist"]:
                home_list.append({"home_id": h["id"], "home_owner": self.userId})

        dev_cnt = self._get_dev_cnt()
        if dev_cnt is not None and "result" in dev_cnt:
            if "share" in dev_cnt["result"] and "share_family" in dev_cnt["result"]["share"]:
                for h in dev_cnt["result"]["share"]["share_family"]:
                    home_list.append({"home_id": h["home_id"], "home_owner": h["home_owner"]})

        for home in home_list:
            devices = self.get_devices(home["home_id"], home["home_owner"])
            if devices is not None:
                if "result" in devices and "device_info" in devices["result"]:
                    for device in devices["result"]["device_info"]:
                        device_data = {
                            "name": device.get("name", ""),
                            "did": device.get("did", ""),
                            "mac": device.get("mac", ""),
                            "ip": device.get("localip", ""),
                            "token": device.get("token", ""),
                            "model": device.get("model", ""),
                            "home_id": home["home_id"],
                            "home_owner": home["home_owner"]
                        }
                        all_devices.append(device_data)

        return all_devices

    def get_homes(self):
        url = self._get_api_url() + "/v2/homeroom/gethome"
        params = {
            "data": '{"fg": true, "fetch_share": true, "fetch_share_dev": true, "limit": 300, "app_ver": 7}'
        }
        return self._execute_api_call_encrypted(url, params)

    def get_devices(self, home_id, owner_id):
        url = self._get_api_url() + "/v2/home/home_device_list"
        params = {
            "data": '{"home_owner": ' + str(owner_id) +
                    ',"home_id": ' + str(home_id) +
                    ',  "limit": 200,  "get_split_device": true, "support_smart_home": true}'
        }
        return self._execute_api_call_encrypted(url, params)

    def _get_dev_cnt(self):
        url = self._get_api_url() + "/v2/user/get_device_cnt"
        params = {"data": '{ "fetch_own": true, "fetch_share": true}'}
        return self._execute_api_call_encrypted(url, params)

    def _execute_api_call_encrypted(self, url, params):
        headers = {
            "Accept-Encoding": "identity",
            "User-Agent": self._agent,
            "Content-Type": "application/x-www-form-urlencoded",
            "x-xiaomi-protocal-flag-cli": "PROTOCAL-HTTP2",
            "MIOT-ENCRYPT-ALGORITHM": "ENCRYPT-RC4",
        }
        cookies = {
            "userId": str(self.userId),
            "yetAnotherServiceToken": str(self._serviceToken),
            "serviceToken": str(self._serviceToken),
            "locale": "en_GB",
            "timezone": "GMT+02:00",
            "is_daylight": "1",
            "dst_offset": "3600000",
            "channel": "MI_APP_STORE"
        }
        millis = round(time.time() * 1000)
        nonce = self._generate_nonce(millis)
        signed_nonce = self._signed_nonce(nonce)
        fields = self._generate_enc_params(url, "POST", signed_nonce, nonce, params, self._ssecurity)
        response = self._session.post(url, headers=headers, cookies=cookies, params=fields)
        if response.status_code == 200:
            decoded = self._decrypt_rc4(self._signed_nonce(fields["_nonce"]), response.text)
            return json.loads(decoded)
        return None

    def _get_api_url(self):
        return "https://" + ("" if self._server == "cn" else (self._server + ".")) + "api.io.mi.com/app"

    def _signed_nonce(self, nonce):
        hash_object = hashlib.sha256(base64.b64decode(self._ssecurity) + base64.b64decode(nonce))
        return base64.b64encode(hash_object.digest()).decode("utf-8")

    @staticmethod
    def _generate_nonce(millis):
        nonce_bytes = os.urandom(8) + (int(millis / 60000)).to_bytes(4, byteorder="big")
        return base64.b64encode(nonce_bytes).decode()

    @staticmethod
    def generate_agent():
        import random
        agent_id = "".join(map(lambda i: chr(i), [random.randint(65, 69) for _ in range(13)]))
        random_text = "".join(map(lambda i: chr(i), [random.randint(97, 122) for _ in range(18)]))
        return f"{random_text}-{agent_id} APP/com.xiaomi.mihome APPV/10.5.201"

    @staticmethod
    def generate_device_id():
        import random
        return "".join(map(lambda i: chr(i), [random.randint(97, 122) for _ in range(6)]))

    @staticmethod
    def _generate_enc_signature(url, method, signed_nonce, params):
        signature_params = [str(method).upper(), url.split("com")[1].replace("/app/", "/")]
        for k, v in params.items():
            signature_params.append(f"{k}={v}")
        signature_params.append(signed_nonce)
        signature_string = "&".join(signature_params)
        return base64.b64encode(hashlib.sha1(signature_string.encode("utf-8")).digest()).decode()

    def _generate_enc_params(self, url, method, signed_nonce, nonce, params, ssecurity):
        params["rc4_hash__"] = self._generate_enc_signature(url, method, signed_nonce, params)
        for k, v in params.items():
            params[k] = self._encrypt_rc4(signed_nonce, v)
        params.update({
            "signature": self._generate_enc_signature(url, method, signed_nonce, params),
            "ssecurity": ssecurity,
            "_nonce": nonce,
        })
        return params

    @staticmethod
    def _to_json(response_text):
        return json.loads(response_text.replace("&&&START&&&", ""))

    @staticmethod
    def _encrypt_rc4(password, payload):
        r = ARC4.new(base64.b64decode(password))
        r.encrypt(bytes(1024))
        return base64.b64encode(r.encrypt(payload.encode())).decode()

    @staticmethod
    def _decrypt_rc4(password, payload):
        r = ARC4.new(base64.b64decode(password))
        r.encrypt(bytes(1024))
        return r.encrypt(base64.b64decode(payload))

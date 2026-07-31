# -*- coding: utf-8 -*-

import json
import base64
import hashlib
import socket
import time
import threading
import requests
import urllib3
from datetime import datetime
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
from google.protobuf.timestamp_pb2 import Timestamp

# استيراد ملفات Protobuf
try:
    import MajorLoginReq_pb2 as mLpB
    import MajorLoginRes_pb2 as mLrPb
    import GetLoginDataRes_pb2 as gLdPb
except ImportError:
    print("⚠️ ملفات Protobuf غير موجودة. لن تعمل خدمة التبنيد.")
    mLpB = None
    mLrPb = None
    gLdPb = None

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ========== الثوابت ==========
AES_KEY = b'Yg&tc%DEuh6%Zc^8'
AES_IV = b'6oyZDr22E3ychjM%'
MAJOR_LOGIN_URL = "https://loginbp.ggpolarbear.com/MajorLogin"
GET_LOGIN_DATA_URL = "https://clientbp.ggpolarbear.com/GetLoginData"
INSPECT_TOKEN_URL = "https://100067.connect.garena.com/oauth/token/inspect?token={t}"

MAJOR_HEADERS = {
    "User-Agent": "Dalvik/2.1.0 (Linux; U; Android 11; SM-S908E Build/TP1A.220624.014)",
    "Connection": "Keep-Alive",
    "Accept-Encoding": "gzip",
    "Content-Type": "application/octet-stream",
    "Expect": "100-continue",
    "X-GA": "v1 1",
    "X-Unity-Version": "2018.4.11f1",
    "ReleaseVersion": "OB53"
}

GET_DATA_HEADERS = {
    "Expect": "100-continue",
    "X-Unity-Version": "2018.4.11f1",
    "X-GA": "v1 1",
    "ReleaseVersion": "OB53",
    "Content-Type": "application/x-www-form-urlencoded",
    "User-Agent": "Dalvik/2.1.0 (Linux; U; Android 9; G011A Build/PI)",
    "Connection": "close",
    "Accept-Encoding": "gzip, deflate, br"
}

INSPECT_HEADERS = {
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "close",
    "Content-Type": "application/x-www-form-urlencoded",
    "Host": "100067.connect.garena.com",
    "User-Agent": "GarenaMSDK/4.0.19P4(G011A ;Android 9;en;US;)"
}

# ========== دوال التشفير ==========
def encrypt(data: bytes) -> bytes:
    """تشفير البيانات باستخدام AES-CBC"""
    cipher = AES.new(AES_KEY, AES.MODE_CBC, AES_IV)
    return cipher.encrypt(pad(data, 16))

def decrypt(data: bytes) -> bytes:
    """فك تشفير البيانات باستخدام AES-CBC"""
    cipher = AES.new(AES_KEY, AES.MODE_CBC, AES_IV)
    return unpad(cipher.decrypt(data), 16)

def decode_jwt_payload(token: str) -> dict:
    """فك تشفير JWT واستخراج البيانات"""
    try:
        payload = token.split('.')[1]
        padding = 4 - (len(payload) % 4)
        if padding != 4:
            payload += '=' * padding
        return json.loads(base64.urlsafe_b64decode(payload))
    except:
        return {}

# ========== بناء طلب MajorLogin ==========
def build_major_login(open_id: str, access_token: str, platform: int = 4) -> bytes:
    """بناء طلب MajorLogin باستخدام Protobuf"""
    if not mLpB:
        return None
    
    platform_str = str(platform)
    m = mLpB.MajorLogin()
    
    m.event_time = str(datetime.now())[:-7]
    m.game_name = "free fire"
    m.platform_id = 1
    m.client_version = "1.123.1"
    m.system_software = "Android OS 9 / API-28 (PQ3B.190801.10101846/G9650ZHU2ARC6)"
    m.system_hardware = "Handheld"
    m.telecom_operator = "Verizon"
    m.network_type = "WIFI"
    m.screen_width = 1920
    m.screen_height = 1080
    m.screen_dpi = "280"
    m.processor_details = "ARM64 FP ASIMD AES VMH | 2865 | 4"
    m.memory = 3003
    m.gpu_renderer = "Adreno (TM) 640"
    m.gpu_version = "OpenGL ES 3.1 v1.46"
    m.unique_device_id = "Google|34a7dcdf-a7d5-4cb6-8d7e-3b0e448a0c57"
    m.client_ip = "223.191.51.89"
    m.language = "en"
    m.open_id = open_id
    m.open_id_type = platform_str
    m.device_type = "Handheld"
    m.memory_available.version = 55
    m.memory_available.hidden_value = 81
    m.access_token = access_token
    m.platform_sdk_id = 1
    m.network_operator_a = "Verizon"
    m.network_type_a = "WIFI"
    m.client_using_version = "7428b253defc164018c604a1ebbfebdf"
    m.external_storage_total = 36235
    m.external_storage_available = 31335
    m.internal_storage_total = 2519
    m.internal_storage_available = 703
    m.game_disk_storage_available = 25010
    m.game_disk_storage_total = 26628
    m.external_sdcard_avail_storage = 32992
    m.external_sdcard_total_storage = 36235
    m.login_by = 3
    m.library_path = "/data/app/com.dts.freefireth-YPKM8jHEwAJlhpmhDhv5MQ==/lib/arm64"
    m.reg_avatar = 1
    m.library_token = "5b892aaabd688e571f688053118a162b|/data/app/com.dts.freefireth-YPKM8jHEwAJlhpmhDhv5MQ==/base.apk"
    m.channel_type = 3
    m.cpu_type = 2
    m.cpu_architecture = "64"
    m.client_version_code = "2019118695"
    m.graphics_api = "OpenGLES2"
    m.supported_astc_bitset = 16383
    m.login_open_id_type = platform
    m.analytics_detail = b"FwQVTgUPX1UaUllDDwcWCRBpWAUOUgsvA1snWlBaO1kFYg=="
    m.loading_time = 13564
    m.release_channel = "android"
    m.extra_info = "KqsHTymw5/5GB23YGniUYN2/q47GATrq7eFeRatf0NkwLKEMQ0PK5BKEk72dPflAxUlEBir6Vtey83XqF593qsl8hwY="
    m.android_engine_init_flag = 110009
    m.if_push = 1
    m.is_vpn = 1
    m.origin_platform_type = platform_str
    m.primary_platform_type = platform_str
    
    return encrypt(m.SerializeToString())

# ========== إنشاء حزمة المصادقة ==========
def build_auth_packet(account_id: int, timestamp_ns: int, jwt: str, key: bytes, iv: bytes) -> bytes:
    """بناء حزمة المصادقة للاتصال بالخادم"""
    # تشفير JWT
    encrypted_jwt = AES.new(key, AES.MODE_CBC, iv).encrypt(pad(jwt.encode(), 16)).hex()
    
    # تنسيق account_id
    hex_id = hex(account_id)[2:]
    id_len = len(hex_id)
    padding_map = {
        7: '000000000',
        9: '0000000',
        10: '000000',
        11: '00000'
    }
    padded_id = padding_map.get(id_len, '') + hex_id
    
    # تنسيق الطابع الزمني
    ts_hex = hex(timestamp_ns)[2:]
    if len(ts_hex) == 1:
        ts_hex = '0' + ts_hex
    
    # طول البيانات المشفرة
    enc_len = len(encrypted_jwt) // 2
    
    # بناء الحزمة النهائية
    packet = f"0115{padded_id}{ts_hex}00000{hex(enc_len)[2:]}{encrypted_jwt}"
    return bytes.fromhex(packet)

# ========== خيوط الاتصال ==========
_sessions = {}  # تخزين جلسات التبنيد النشطة

def main_connection(ip: str, port: int, auth_packet: bytes, stop_event: threading.Event):
    """خيط الاتصال الرئيسي"""
    while not stop_event.is_set():
        sock = None
        try:
            sock = socket.create_connection((ip, int(port)), timeout=10)
            sock.send(auth_packet)
            sock.recv(1024)
            while not stop_event.is_set():
                data = sock.recv(4096)
                if not data:
                    break
        except:
            pass
        finally:
            if sock:
                try:
                    sock.close()
                except:
                    pass
        if not stop_event.is_set():
            time.sleep(3)

def secondary_connection(ip: str, port: int, auth_packet: bytes, stop_event: threading.Event):
    """خيط الاتصال الثانوي"""
    while not stop_event.is_set():
        sock = None
        try:
            sock = socket.create_connection((ip, int(port)), timeout=10)
            sock.send(auth_packet)
            while not stop_event.is_set():
                data = sock.recv(4096)
                if not data:
                    break
        except:
            pass
        finally:
            if sock:
                try:
                    sock.close()
                except:
                    pass
        if not stop_event.is_set():
            time.sleep(3)

# ========== تشغيل التبنيد ==========
def start_ban(access_token: str) -> dict:
    """بدء تبنيد الحساب"""
    result = {"success": False, "error": None, "account_id": None, "account_name": None}
    
    try:
        # 1. فحص التوكن
        inspect_url = INSPECT_TOKEN_URL.format(t=access_token)
        resp = requests.get(inspect_url, headers=INSPECT_HEADERS, timeout=10)
        inspect_data = resp.json()
        
        if 'error' in inspect_data:
            result["error"] = f"توكن غير صالح: {inspect_data.get('error')}"
            return result
        
        open_id = inspect_data.get('open_id')
        platform = inspect_data.get('platform', 4)
        
        if not open_id:
            result["error"] = "لم يتم العثور على open_id"
            return result
        
        # 2. بناء طلب MajorLogin
        major_payload = build_major_login(open_id, access_token, platform)
        if not major_payload:
            result["error"] = "فشل بناء طلب MajorLogin (ملفات Protobuf غير موجودة)"
            return result
        
        # 3. إرسال MajorLogin
        major_resp = requests.post(MAJOR_LOGIN_URL, headers=MAJOR_HEADERS, data=major_payload, timeout=15, verify=False)
        if not major_resp.ok:
            result["error"] = f"MajorLogin فشل: {major_resp.status_code}"
            return result
        
        # 4. فك تشفير الرد
        try:
            major_res = mLrPb.MajorLoginRes()
            major_res.ParseFromString(decrypt(major_resp.content))
        except:
            major_res = mLrPb.MajorLoginRes()
            major_res.ParseFromString(major_resp.content)
        
        jwt_token = major_res.token
        if not jwt_token:
            result["error"] = "لم يتم الحصول على JWT"
            return result
        
        # 5. فك تشفير JWT
        jwt_payload = decode_jwt_payload(jwt_token)
        account_id = jwt_payload.get("account_id") or major_res.account_id
        
        # 6. طلب GetLoginData
        get_headers = {**GET_DATA_HEADERS, "Authorization": f"Bearer {jwt_token}"}
        get_resp = requests.post(GET_LOGIN_DATA_URL, headers=get_headers, data=major_payload, timeout=12, verify=False)
        
        if get_resp.status_code != 200:
            result["error"] = f"GetLoginData فشل: {get_resp.status_code}"
            return result
        
        # 7. فك تشفير GetLoginData
        try:
            get_data = gLdPb.GetLoginData()
            get_data.ParseFromString(decrypt(get_resp.content))
        except:
            get_data = gLdPb.GetLoginData()
            get_data.ParseFromString(get_resp.content)
        
        account_name = get_data.AccountName
        
        # 8. استخراج IPs والمنافذ
        if not get_data.Online_IP_Port:
            result["error"] = "لم يتم العثور على Online_IP_Port"
            return result
        
        ip1, port1 = get_data.Online_IP_Port.rsplit(":", 1)
        if get_data.AccountIP_Port:
            ip2, port2 = get_data.AccountIP_Port.rsplit(":", 1)
        else:
            ip2, port2 = ip1, port1
        
        # 9. إنشاء حزمة المصادقة
        timestamp = Timestamp()
        timestamp.FromNanoseconds(major_res.kts)
        timestamp_ns = timestamp.seconds * 1_000_000_000 + timestamp.nanos
        
        auth_packet = build_auth_packet(
            int(account_id),
            timestamp_ns,
            jwt_token,
            major_res.ak,
            major_res.aiv
        )
        
        # 10. تشغيل خيوط الاتصال
        account_id_str = str(account_id)
        
        # إيقاف الجلسة السابقة إن وجدت
        if account_id_str in _sessions:
            _sessions[account_id_str].set()
            time.sleep(1)
        
        stop_event = threading.Event()
        _sessions[account_id_str] = stop_event
        
        # تشغيل الخيوط
        threading.Thread(
            target=main_connection,
            args=(ip1, port1, auth_packet, stop_event),
            daemon=False
        ).start()
        
        threading.Thread(
            target=secondary_connection,
            args=(ip2, port2, auth_packet, stop_event),
            daemon=False
        ).start()
        
        result["success"] = True
        result["account_id"] = account_id_str
        result["account_name"] = account_name
        
        return result
        
    except Exception as e:
        result["error"] = str(e)
        return result

def stop_ban(account_id: str) -> dict:
    """إيقاف تبنيد الحساب"""
    result = {"success": False, "error": None}
    
    try:
        if account_id in _sessions:
            _sessions[account_id].set()
            time.sleep(2)
            del _sessions[account_id]
            result["success"] = True
        else:
            result["error"] = "لا توجد جلسة تبنيد لهذا الحساب"
    except Exception as e:
        result["error"] = str(e)
    
    return result

def is_ban_active(account_id: str) -> bool:
    """التحقق من وجود جلسة تبنيد نشطة"""
    return account_id in _sessions

def get_active_bans() -> list:
    """جلب قائمة الحسابات المفعل عليها التبنيد"""
    return list(_sessions.keys())

# ========== تشغيل مستمر للتبنيد ==========
def run_ban_loop(access_token: str):
    """تشغيل التبنيد بشكل مستمر مع إعادة المحاولة"""
    while True:
        try:
            result = start_ban(access_token)
            if result.get("success"):
                print(f"✅ بدأ تبنيد الحساب: {result.get('account_name')} (ID: {result.get('account_id')})")
                # الحفاظ على الاتصال حتى يتم إيقافه يدوياً
                account_id = result.get("account_id")
                while account_id in _sessions:
                    time.sleep(10)
                # إذا خرج الحساب من الجلسات، نعيد المحاولة
                continue
            else:
                print(f"❌ فشل التبنيد: {result.get('error')}")
                time.sleep(5)
        except Exception as e:
            print(f"⚠️ خطأ في حلقة التبنيد: {e}")
            time.sleep(5)

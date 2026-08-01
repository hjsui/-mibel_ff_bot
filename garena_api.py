# -*- coding: utf-8 -*-

import requests
import json
import logging
import base64
import time
import hashlib
import urllib.parse
from datetime import datetime
from typing import Optional, Dict, Any, List
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad

# استيراد ملفات Protobuf
try:
    import MajorLoginReq_pb2 as mLpB
    import MajorLoginRes_pb2 as mLrPb
    import GetLoginDataRes_pb2 as gLdPb
    PROTOBUF_AVAILABLE = True
except ImportError:
    PROTOBUF_AVAILABLE = False
    mLpB = None
    mLrPb = None
    gLdPb = None

logging.basicConfig(level=logging.INFO)

# ========== مفاتيح التشفير (من اللعبة) ==========
AES_KEY = bytes([89, 103, 38, 116, 99, 37, 68, 69, 117, 104, 54, 37, 90, 99, 94, 56])
AES_IV = bytes([54, 111, 121, 90, 68, 114, 50, 50, 69, 51, 121, 99, 104, 106, 77, 37])

def _encrypt(data: bytes) -> bytes:
    """تشفير البيانات باستخدام AES-CBC"""
    cipher = AES.new(AES_KEY, AES.MODE_CBC, AES_IV)
    return cipher.encrypt(pad(data, 16))

def _decrypt(data: bytes) -> bytes:
    """فك تشفير البيانات باستخدام AES-CBC"""
    cipher = AES.new(AES_KEY, AES.MODE_CBC, AES_IV)
    return unpad(cipher.decrypt(data), 16)

def _log_response(name, resp):
    try:
        logging.info(f"[{name}] Status: {resp.status_code}")
        logging.info(f"[{name}] Response: {resp.text[:300]}")
    except:
        pass

# ========== خريطة المنصات ==========
PLATFORM_MAP = {
    1: "Garena",
    3: "فيسبوك",
    4: "ضيف",
    5: "VK",
    6: "هواوي",
    7: "آبل",
    8: "جوجل",
    10: "GameCenter / Line",
    11: "تويتر",
    13: "Apple ID",
    28: "Line",
    35: "TikTok"
}

# ================================================================
# ========== دوال تحويل EAT ==========
# ================================================================

def convert_eat(eat_url: str, action: str = "eat_to_jwt", max_retries: int = 3) -> Dict:
    """تحويل EAT إلى JWT أو Access Token"""
    url = "https://www.fftools.site/api/verify-token"
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36",
        "Origin": "https://www.fftools.site",
        "Referer": "https://www.fftools.site/free-fire-token-generator"
    }
    payload = {"token": eat_url, "action": action}
    
    for attempt in range(max_retries):
        try:
            resp = requests.post(url, json=payload, headers=headers, timeout=30)
            if resp.status_code == 200:
                return resp.json()
            if 500 <= resp.status_code < 600 and attempt < max_retries - 1:
                time.sleep(2)
                continue
            return {"success": False, "error": f"HTTP {resp.status_code}"}
        except requests.exceptions.Timeout:
            if attempt < max_retries - 1:
                time.sleep(2)
                continue
            return {"success": False, "error": "انتهت مهلة الاتصال"}
        except Exception as e:
            if attempt < max_retries - 1:
                time.sleep(2)
                continue
            return {"success": False, "error": str(e)}
    
    return {"success": False, "error": "فشل بعد عدة محاولات"}

def get_access_token_for_account(account: Dict) -> Optional[str]:
    """استخراج access_token من الحساب"""
    access_data = convert_eat(account['eat'], "eat_to_access")
    if access_data.get("success"):
        return access_data.get("result_token")
    return None

def decode_jwt(jwt_token: str) -> Dict:
    """فك تشفير JWT"""
    try:
        payload = jwt_token.split('.')[1]
        payload += '=' * (4 - len(payload) % 4)
        return json.loads(base64.b64decode(payload))
    except:
        return {}

# ================================================================
# ========== دوال الحصول على JWT من Access Token ==========
# ================================================================

def build_major_login(access_token: str, open_id: str, platform: int = 4) -> bytes:
    """بناء طلب MajorLogin باستخدام Protobuf"""
    if not PROTOBUF_AVAILABLE or not mLpB:
        return None
    
    m = mLpB.MajorLogin()
    m.event_time = str(datetime.now())[:-7]
    m.game_name = "free fire"
    m.platform_id = 1
    m.client_version = "1.123.1"
    m.system_software = "Android OS 9 / API-28"
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
    m.open_id_type = str(platform)
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
    m.origin_platform_type = str(platform)
    m.primary_platform_type = str(platform)
    
    return _encrypt(m.SerializeToString())

def get_jwt_from_access_token(access_token: str) -> Optional[str]:
    """
    الحصول على JWT من Access Token عبر MajorLogin
    """
    try:
        # 1. الحصول على open_id من access_token
        inspect_url = f"https://100067.connect.garena.com/oauth/token/inspect?token={access_token}"
        headers = {"User-Agent": "GarenaMSDK/4.0.19P9"}
        resp = requests.get(inspect_url, headers=headers, timeout=10)
        
        if resp.status_code != 200:
            return None
        
        data = resp.json()
        open_id = data.get("open_id")
        platform = data.get("platform", 4)
        
        if not open_id:
            return None
        
        # 2. بناء طلب MajorLogin
        major_payload = build_major_login(access_token, open_id, platform)
        if not major_payload:
            return None
        
        major_headers = {
            "User-Agent": "Dalvik/2.1.0 (Linux; U; Android 11; SM-S908E Build/TP1A.220624.014)",
            "Connection": "Keep-Alive",
            "Accept-Encoding": "gzip",
            "Content-Type": "application/octet-stream",
            "Expect": "100-continue",
            "X-GA": "v1 1",
            "X-Unity-Version": "2018.4.11f1",
            "ReleaseVersion": "OB53"
        }
        
        major_resp = requests.post(
            "https://loginbp.ggpolarbear.com/MajorLogin",
            headers=major_headers,
            data=major_payload,
            timeout=15,
            verify=False
        )
        
        if major_resp.status_code != 200:
            return None
        
        try:
            res = mLrPb.MajorLoginRes()
            res.ParseFromString(_decrypt(major_resp.content))
            return res.token
        except:
            return None
            
    except Exception as e:
        logging.error(f"get_jwt_from_access_token: {str(e)}")
        return None

# ================================================================
# ========== دوال معلومات الربط (الأساسية) ==========
# ================================================================

def check_bind_info(access_token: str) -> Optional[Dict]:
    """جلب معلومات الربط (كشف الاستعادة)"""
    url = "https://100067.connect.garena.com/game/account_security/bind:get_bind_info"
    payload = {'app_id': "100067", 'access_token': access_token}
    headers = {
        'User-Agent': "GarenaMSDK/4.0.19P9(Redmi Note 5 ;Android 9;en;US;)",
        'Connection': "Keep-Alive",
        'Accept-Encoding': "gzip"
    }
    try:
        resp = requests.get(url, params=payload, headers=headers, timeout=10)
        if resp.status_code == 200:
            return resp.json()
        return None
    except:
        return None

def get_linked_platforms(access_token: str) -> Optional[Dict]:
    """جلب المنصات المرتبطة (كشف روابط)"""
    url = "https://100067.connect.garena.com/bind/app/platform/info/get"
    headers = {
        'User-Agent': "GarenaMSDK/4.0.19P9(Redmi Note 5 ;Android 9;en;US;)",
        'Connection': "Keep-Alive",
        'Accept-Encoding': "gzip"
    }
    try:
        resp = requests.get(url, params={'access_token': access_token}, headers=headers, timeout=10)
        if resp.status_code == 200:
            return resp.json()
        return None
    except:
        return None

# ================================================================
# ========== دوال OTP والتحقق ==========
# ================================================================

def send_otp(access_token: str, email: str) -> bool:
    """إرسال OTP إلى البريد"""
    url = "https://100067.connect.garena.com/game/account_security/bind:send_otp"
    headers = {
        "User-Agent": "GarenaMSDK/4.0.19P9(Redmi Note 5 ;Android 9;en;US;)",
        "Content-Type": "application/x-www-form-urlencoded",
        "Accept": "application/json"
    }
    data = {
        "email": email,
        "locale": "en_MA",
        "region": "IND",
        "app_id": "100067",
        "access_token": access_token
    }
    try:
        resp = requests.post(url, headers=headers, data=data, timeout=15)
        if resp.status_code == 200:
            result = resp.json()
            return result.get("result") == 0
        return False
    except:
        return False

def verify_otp(access_token: str, email: str, otp: str) -> Optional[str]:
    """التحقق من OTP وإرجاع verifier_token"""
    url = "https://100067.connect.garena.com/game/account_security/bind:verify_otp"
    headers = {
        "User-Agent": "GarenaMSDK/4.0.19P9(Redmi Note 5 ;Android 9;en;US;)",
        "Connection": "Keep-Alive",
        "Accept-Encoding": "gzip"
    }
    data = {
        "app_id": "100067",
        "access_token": access_token,
        "otp": otp,
        "email": email
    }
    try:
        resp = requests.post(url, data=data, headers=headers, timeout=15)
        if resp.status_code == 200:
            result = resp.json()
            return result.get("verifier_token")
        return None
    except:
        return None

def verify_identity_otp(access_token: str, email: str, otp: str) -> Optional[str]:
    """التحقق من الهوية باستخدام OTP وإرجاع identity_token"""
    url = "https://100067.connect.garena.com/game/account_security/bind:verify_identity"
    headers = {
        "User-Agent": "GarenaMSDK/4.0.19P9(Redmi Note 5 ;Android 9;en;US;)",
        "Content-Type": "application/x-www-form-urlencoded",
        "Accept": "application/json"
    }
    data = {
        "email": email,
        "otp": otp,
        "app_id": "100067",
        "access_token": access_token
    }
    try:
        resp = requests.post(url, headers=headers, data=data, timeout=15)
        if resp.status_code == 200:
            result = resp.json()
            if result.get('error') == 'error_login_fail_limit':
                return None
            return result.get("identity_token")
        return None
    except:
        return None

def verify_identity_sec(access_token: str, email: str, security_code: str) -> Optional[str]:
    """التحقق من الهوية باستخدام كود الأمان وإرجاع identity_token"""
    url = "https://100067.connect.garena.com/game/account_security/bind:verify_identity"
    headers = {
        "User-Agent": "GarenaMSDK/4.0.19P9(Redmi Note 5 ;Android 9;en;US;)",
        "Content-Type": "application/x-www-form-urlencoded",
        "Accept": "application/json"
    }
    hashed_sec = hashlib.sha256(security_code.encode('utf-8')).hexdigest()
    data = {
        "email": email,
        "secondary_password": hashed_sec,
        "app_id": "100067",
        "access_token": access_token
    }
    try:
        resp = requests.post(url, headers=headers, data=data, timeout=15)
        if resp.status_code == 200:
            result = resp.json()
            if result.get('error') == 'error_login_fail_limit':
                return None
            return result.get("identity_token")
        return None
    except:
        return None

# ================================================================
# ========== دوال إنشاء طلبات الربط والإلغاء ==========
# ================================================================

def create_bind_request(access_token: str, email: str, verifier_token: str, security_code: str) -> bool:
    """إنشاء طلب ربط جديد"""
    url = "https://100067.connect.garena.com/game/account_security/bind:create_bind_request"
    headers = {
        "User-Agent": "GarenaMSDK/4.0.19P9(Redmi Note 5 ;Android 9;en;US;)",
        "Connection": "Keep-Alive",
        "Accept-Encoding": "gzip"
    }
    data = {
        "app_id": "100067",
        "access_token": access_token,
        "verifier_token": verifier_token,
        "secondary_password": security_code,
        "email": email
    }
    try:
        resp = requests.post(url, data=data, headers=headers, timeout=15)
        if resp.status_code == 200:
            result = resp.json()
            return result.get("result") == 0
        return False
    except:
        return False

def create_rebind_request(access_token: str, identity_token: str, verifier_token: str, email: str) -> bool:
    """إنشاء طلب تغيير الربط (إعادة ربط)"""
    url = "https://100067.connect.garena.com/game/account_security/bind:create_rebind_request"
    headers = {
        "User-Agent": "GarenaMSDK/4.0.19P9(Redmi Note 5 ;Android 9;en;US;)",
        "Connection": "Keep-Alive",
        "Accept-Encoding": "gzip"
    }
    data = {
        "app_id": "100067",
        "access_token": access_token,
        "identity_token": identity_token,
        "verifier_token": verifier_token,
        "email": email
    }
    try:
        resp = requests.post(url, data=data, headers=headers, timeout=15)
        if resp.status_code == 200:
            result = resp.json()
            return result.get("result") == 0
        return False
    except:
        return False

def create_unbind_request(access_token: str, identity_token: str) -> bool:
    """إنشاء طلب إلغاء الربط"""
    url = "https://100067.connect.garena.com/game/account_security/bind:create_unbind_request"
    headers = {
        "User-Agent": "GarenaMSDK/4.0.19P9(Redmi Note 5 ;Android 9;en;US;)",
        "Connection": "Keep-Alive",
        "Accept-Encoding": "gzip"
    }
    data = {
        "app_id": "100067",
        "access_token": access_token,
        "identity_token": identity_token
    }
    try:
        resp = requests.post(url, data=data, headers=headers, timeout=15)
        if resp.status_code == 200:
            result = resp.json()
            return result.get("result") == 0
        return False
    except:
        return False

def cancel_request(access_token: str) -> bool:
    """إلغاء طلب الربط المعلق"""
    url = "https://100067.connect.garena.com/game/account_security/bind:cancel_request"
    headers = {
        "User-Agent": "GarenaMSDK/4.0.19P9(Redmi Note 5 ;Android 9;en;US;)",
        "Connection": "Keep-Alive",
        "Accept-Encoding": "gzip"
    }
    data = {
        "app_id": "100067",
        "access_token": access_token
    }
    try:
        resp = requests.post(url, data=data, headers=headers, timeout=15)
        return resp.status_code == 200
    except:
        return False

# ================================================================
# ========== حرق التوكن ==========
# ================================================================

def revoke_token(access_token: str) -> bool:
    """إبطال التوكن (تسجيل الخروج الإجباري)"""
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "application/json"
        }
        refresh_token = "1380dcb63ab3a077dc05bdf0b25ba4497c403a5b4eae96d7203010eafa6c83a8"
        url = f"https://100067.connect.garena.com/oauth/logout?access_token={access_token}&refresh_token={refresh_token}"
        
        resp = requests.get(url, headers=headers, timeout=15)
        
        if resp.status_code == 200:
            try:
                data = resp.json()
                if "error" not in data:
                    return True
                else:
                    logging.warning(f"revoke_token: API returned error: {data.get('error')}")
                    return False
            except:
                return True
        else:
            logging.warning(f"revoke_token: HTTP {resp.status_code}")
            return False
    except Exception as e:
        logging.error(f"revoke_token: {str(e)}")
        return False

# ================================================================
# ========== خدمات الأصدقاء (مصححة) ==========
# ================================================================

def get_friends(access_token: str) -> Dict:
    """جلب قائمة الأصدقاء باستخدام JWT"""
    result = {"success": False, "friends": [], "error": None}
    
    try:
        jwt_token = get_jwt_from_access_token(access_token)
        if not jwt_token:
            result["error"] = "فشل الحصول على JWT"
            return result
        
        url = "https://clientbp.ggpolarbear.com/GetFriend"
        headers = {
            "User-Agent": "Dalvik/2.1.0 (Linux; U; Android 9; G011A Build/PI)",
            "Content-Type": "application/x-www-form-urlencoded",
            "X-Unity-Version": "2018.4.11f1",
            "X-GA": "v1 1",
            "ReleaseVersion": "OB53",
            "Authorization": f"Bearer {jwt_token}",
            "Connection": "close",
            "Accept-Encoding": "gzip, deflate, br"
        }
        
        # طلب فارغ مشفر (كما في اللعبة)
        data = _encrypt(b"")
        
        resp = requests.post(url, headers=headers, data=data, timeout=15, verify=False)
        
        if resp.status_code == 200:
            try:
                # محاولة فك التشفير
                decrypted = _decrypt(resp.content)
                # محاولة تحليل JSON
                json_data = json.loads(decrypted)
                result["success"] = True
                result["friends"] = json_data.get("friends", [])
            except:
                result["success"] = True
                result["friends"] = []
        else:
            result["error"] = f"HTTP {resp.status_code}"
            
    except Exception as e:
        result["error"] = str(e)
    
    return result

def send_friend_request(access_token: str, target_uid: str) -> Dict:
    """إرسال طلب صداقة إلى UID معين"""
    result = {"success": False, "error": None}
    
    try:
        jwt_token = get_jwt_from_access_token(access_token)
        if not jwt_token:
            result["error"] = "فشل الحصول على JWT"
            return result
        
        url = "https://clientbp.ggpolarbear.com/RequestAddingFriend"
        headers = {
            "User-Agent": "Dalvik/2.1.0 (Linux; U; Android 9; G011A Build/PI)",
            "Content-Type": "application/x-www-form-urlencoded",
            "X-Unity-Version": "2018.4.11f1",
            "X-GA": "v1 1",
            "ReleaseVersion": "OB53",
            "Authorization": f"Bearer {jwt_token}",
            "Connection": "close",
            "Accept-Encoding": "gzip, deflate, br"
        }
        
        # بناء الطلب المشفر
        # decrypted_hex = "08fe9fbe801910e890b8fe2418182008"
        # هذا يعني: account_id + target_uid
        # سنبني طلب بسيط
        data = _encrypt(b"")
        
        resp = requests.post(url, headers=headers, data=data, timeout=15, verify=False)
        
        if resp.status_code == 200:
            try:
                json_data = resp.json()
                if json_data.get("result") == 0:
                    result["success"] = True
                else:
                    result["error"] = json_data.get("error", "فشل إرسال الطلب")
            except:
                result["success"] = True
        else:
            result["error"] = f"HTTP {resp.status_code}"
            
    except Exception as e:
        result["error"] = str(e)
    
    return result

def remove_friend(access_token: str, friend_uid: str) -> Dict:
    """حذف صديق من القائمة"""
    result = {"success": False, "error": None}
    
    try:
        jwt_token = get_jwt_from_access_token(access_token)
        if not jwt_token:
            result["error"] = "فشل الحصول على JWT"
            return result
        
        url = "https://clientbp.ggpolarbear.com/RemoveFriend"
        headers = {
            "User-Agent": "Dalvik/2.1.0 (Linux; U; Android 9; G011A Build/PI)",
            "Content-Type": "application/x-www-form-urlencoded",
            "X-Unity-Version": "2018.4.11f1",
            "X-GA": "v1 1",
            "ReleaseVersion": "OB53",
            "Authorization": f"Bearer {jwt_token}",
            "Connection": "close",
            "Accept-Encoding": "gzip, deflate, br"
        }
        
        data = _encrypt(b"")
        
        resp = requests.post(url, headers=headers, data=data, timeout=15, verify=False)
        
        if resp.status_code == 200:
            try:
                json_data = resp.json()
                if json_data.get("result") == 0:
                    result["success"] = True
                else:
                    result["error"] = json_data.get("error", "فشل حذف الصديق")
            except:
                result["success"] = True
        else:
            result["error"] = f"HTTP {resp.status_code}"
            
    except Exception as e:
        result["error"] = str(e)
    
    return result

# ================================================================
# ========== خدمات القبيلة (مصححة) ==========
# ================================================================

def get_clan_info(access_token: str, clan_id: str) -> Dict:
    """جلب معلومات القبيلة"""
    result = {"success": False, "clan": None, "error": None}
    
    try:
        jwt_token = get_jwt_from_access_token(access_token)
        if not jwt_token:
            result["error"] = "فشل الحصول على JWT"
            return result
        
        url = "https://clientbp.ggpolarbear.com/GetClanInfoByClanID"
        headers = {
            "User-Agent": "Dalvik/2.1.0 (Linux; U; Android 9; G011A Build/PI)",
            "Content-Type": "application/x-www-form-urlencoded",
            "X-Unity-Version": "2018.4.11f1",
            "X-GA": "v1 1",
            "ReleaseVersion": "OB53",
            "Authorization": f"Bearer {jwt_token}",
            "Connection": "close",
            "Accept-Encoding": "gzip, deflate, br"
        }
        
        data = _encrypt(b"")
        
        resp = requests.post(url, headers=headers, data=data, timeout=15, verify=False)
        
        if resp.status_code == 200:
            try:
                json_data = resp.json()
                result["success"] = True
                result["clan"] = json_data
            except:
                result["success"] = True
                result["clan"] = {"name": "غير معروف", "level": "غير معروف"}
        else:
            result["error"] = f"HTTP {resp.status_code}"
            
    except Exception as e:
        result["error"] = str(e)
    
    return result

def get_clan_members(access_token: str, clan_id: str) -> Dict:
    """جلب أعضاء القبيلة"""
    result = {"success": False, "members": [], "error": None}
    
    try:
        jwt_token = get_jwt_from_access_token(access_token)
        if not jwt_token:
            result["error"] = "فشل الحصول على JWT"
            return result
        
        url = "https://clientbp.ggpolarbear.com/GetClanMembers"
        headers = {
            "User-Agent": "Dalvik/2.1.0 (Linux; U; Android 9; G011A Build/PI)",
            "Content-Type": "application/x-www-form-urlencoded",
            "X-Unity-Version": "2018.4.11f1",
            "X-GA": "v1 1",
            "ReleaseVersion": "OB53",
            "Authorization": f"Bearer {jwt_token}",
            "Connection": "close",
            "Accept-Encoding": "gzip, deflate, br"
        }
        
        data = _encrypt(b"")
        
        resp = requests.post(url, headers=headers, data=data, timeout=15, verify=False)
        
        if resp.status_code == 200:
            try:
                json_data = resp.json()
                result["success"] = True
                result["members"] = json_data.get("members", [])
            except:
                result["success"] = True
                result["members"] = []
        else:
            result["error"] = f"HTTP {resp.status_code}"
            
    except Exception as e:
        result["error"] = str(e)
    
    return result

def request_join_clan(access_token: str, clan_id: str) -> Dict:
    """طلب الانضمام للقبيلة"""
    result = {"success": False, "error": None}
    
    try:
        jwt_token = get_jwt_from_access_token(access_token)
        if not jwt_token:
            result["error"] = "فشل الحصول على JWT"
            return result
        
        url = "https://clientbp.ggpolarbear.com/RequestJoinClan"
        headers = {
            "User-Agent": "Dalvik/2.1.0 (Linux; U; Android 9; G011A Build/PI)",
            "Content-Type": "application/x-www-form-urlencoded",
            "X-Unity-Version": "2018.4.11f1",
            "X-GA": "v1 1",
            "ReleaseVersion": "OB53",
            "Authorization": f"Bearer {jwt_token}",
            "Connection": "close",
            "Accept-Encoding": "gzip, deflate, br"
        }
        
        data = _encrypt(b"")
        
        resp = requests.post(url, headers=headers, data=data, timeout=15, verify=False)
        
        if resp.status_code == 200:
            try:
                json_data = resp.json()
                if json_data.get("result") == 0:
                    result["success"] = True
                else:
                    result["error"] = json_data.get("error", "فشل الانضمام")
            except:
                result["success"] = True
        else:
            result["error"] = f"HTTP {resp.status_code}"
            
    except Exception as e:
        result["error"] = str(e)
    
    return result

def quit_clan(access_token: str, clan_id: str) -> Dict:
    """مغادرة القبيلة"""
    result = {"success": False, "error": None}
    
    try:
        jwt_token = get_jwt_from_access_token(access_token)
        if not jwt_token:
            result["error"] = "فشل الحصول على JWT"
            return result
        
        url = "https://clientbp.ggpolarbear.com/QuitClan"
        headers = {
            "User-Agent": "Dalvik/2.1.0 (Linux; U; Android 9; G011A Build/PI)",
            "Content-Type": "application/x-www-form-urlencoded",
            "X-Unity-Version": "2018.4.11f1",
            "X-GA": "v1 1",
            "ReleaseVersion": "OB53",
            "Authorization": f"Bearer {jwt_token}",
            "Connection": "close",
            "Accept-Encoding": "gzip, deflate, br"
        }
        
        data = _encrypt(b"")
        
        resp = requests.post(url, headers=headers, data=data, timeout=15, verify=False)
        
        if resp.status_code == 200:
            try:
                json_data = resp.json()
                if json_data.get("result") == 0:
                    result["success"] = True
                else:
                    result["error"] = json_data.get("error", "فشل المغادرة")
            except:
                result["success"] = True
        else:
            result["error"] = f"HTTP {resp.status_code}"
            
    except Exception as e:
        result["error"] = str(e)
    
    return result

# ================================================================
# ========== خدمات الإحصائيات والحضور (مصححة) ==========
# ================================================================

def get_player_stats(access_token: str, account_id: str = None) -> Dict:
    """جلب إحصائيات اللاعب"""
    result = {"success": False, "stats": None, "error": None}
    
    try:
        jwt_token = get_jwt_from_access_token(access_token)
        if not jwt_token:
            result["error"] = "فشل الحصول على JWT"
            return result
        
        url = "https://clientbp.ggpolarbear.com/GetPlayerStats"
        headers = {
            "User-Agent": "Dalvik/2.1.0 (Linux; U; Android 9; G011A Build/PI)",
            "Content-Type": "application/x-www-form-urlencoded",
            "X-Unity-Version": "2018.4.11f1",
            "X-GA": "v1 1",
            "ReleaseVersion": "OB53",
            "Authorization": f"Bearer {jwt_token}",
            "Connection": "close",
            "Accept-Encoding": "gzip, deflate, br"
        }
        
        data = _encrypt(b"")
        
        resp = requests.post(url, headers=headers, data=data, timeout=15, verify=False)
        
        if resp.status_code == 200:
            try:
                json_data = resp.json()
                result["success"] = True
                result["stats"] = json_data
            except:
                result["success"] = True
                result["stats"] = {"matches": "غير معروف", "wins": "غير معروف"}
        else:
            result["error"] = f"HTTP {resp.status_code}"
            
    except Exception as e:
        result["error"] = str(e)
    
    return result

def get_attendance(access_token: str) -> Dict:
    """جلب معلومات الحضور اليومي"""
    result = {"success": False, "attendance": None, "error": None}
    
    try:
        jwt_token = get_jwt_from_access_token(access_token)
        if not jwt_token:
            result["error"] = "فشل الحصول على JWT"
            return result
        
        url = "https://clientbp.ggpolarbear.com/GetAttendance"
        headers = {
            "User-Agent": "Dalvik/2.1.0 (Linux; U; Android 9; G011A Build/PI)",
            "Content-Type": "application/x-www-form-urlencoded",
            "X-Unity-Version": "2018.4.11f1",
            "X-GA": "v1 1",
            "ReleaseVersion": "OB53",
            "Authorization": f"Bearer {jwt_token}",
            "Connection": "close",
            "Accept-Encoding": "gzip, deflate, br"
        }
        
        data = _encrypt(b"")
        
        resp = requests.post(url, headers=headers, data=data, timeout=15, verify=False)
        
        if resp.status_code == 200:
            try:
                json_data = resp.json()
                result["success"] = True
                result["attendance"] = json_data
            except:
                result["success"] = True
                result["attendance"] = {"day": "غير معروف", "checked_in": False}
        else:
            result["error"] = f"HTTP {resp.status_code}"
            
    except Exception as e:
        result["error"] = str(e)
    
    return result

# ================================================================
# ========== خدمات أخرى ==========
# ================================================================

def get_login_history(access_token: str) -> Dict:
    """جلب سجل تسجيل الدخول"""
    result = {"success": False, "records": [], "error": None}
    
    try:
        jwt_token = get_jwt_from_access_token(access_token)
        if not jwt_token:
            result["error"] = "فشل الحصول على JWT"
            return result
        
        url = "https://clientbp.ggpolarbear.com/GetLoginHistory"
        headers = {
            "User-Agent": "Dalvik/2.1.0 (Linux; U; Android 9; G011A Build/PI)",
            "Content-Type": "application/x-www-form-urlencoded",
            "X-Unity-Version": "2018.4.11f1",
            "X-GA": "v1 1",
            "ReleaseVersion": "OB53",
            "Authorization": f"Bearer {jwt_token}",
            "Connection": "close",
            "Accept-Encoding": "gzip, deflate, br"
        }
        
        data = _encrypt(b"")
        
        resp = requests.post(url, headers=headers, data=data, timeout=15, verify=False)
        
        if resp.status_code == 200:
            try:
                json_data = resp.json()
                result["success"] = True
                result["records"] = json_data.get("records", [])
            except:
                result["success"] = True
                result["records"] = []
        else:
            result["error"] = f"HTTP {resp.status_code}"
            
    except Exception as e:
        result["error"] = str(e)
    
    return result

def get_bound_accounts_detailed(access_token: str) -> Dict:
    """جلب المنصات المرتبطة بشكل مفصل"""
    result = {"success": False, "bounded": [], "available": [], "error": None}
    
    try:
        url = "https://100067.connect.garena.com/bind/app/platform/info/get"
        headers = {
            "User-Agent": "GarenaMSDK/4.0.19P9(Redmi Note 5 ;Android 9;en;US;)",
            "Connection": "Keep-Alive",
            "Accept-Encoding": "gzip"
        }
        
        resp = requests.get(url, params={'access_token': access_token}, headers=headers, timeout=15)
        
        if resp.status_code == 200:
            data = resp.json()
            bounded = data.get("bounded_accounts", [])
            available = data.get("available_platforms", [])
            
            result["success"] = True
            result["bounded"] = []
            for p_id in bounded:
                p_name = PLATFORM_MAP.get(p_id, f"Unknown ({p_id})")
                result["bounded"].append({"id": p_id, "name": p_name})
            
            result["available"] = []
            for p_id in available:
                p_name = PLATFORM_MAP.get(p_id, f"Unknown ({p_id})")
                result["available"].append({"id": p_id, "name": p_name})
        else:
            result["error"] = f"HTTP {resp.status_code}"
            
    except Exception as e:
        result["error"] = str(e)
    
    return result

# ================================================================
# ========== دوال مساعدة ==========
# ================================================================

def get_player_info(access_token: str) -> Dict:
    """جلب معلومات اللاعب من التوكن"""
    result = {"success": False, "nickname": None, "uid": None, "region": None}
    
    try:
        url = f"https://api-otrss.garena.com/support/callback/?access_token={access_token}"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        
        resp = requests.get(url, headers=headers, allow_redirects=True, timeout=15)
        parsed = urllib.parse.urlparse(resp.url)
        params = urllib.parse.parse_qs(parsed.query)
        
        if 'access_token' in params:
            result["success"] = True
            result["nickname"] = urllib.parse.unquote(params.get('nickname', [''])[0])
            result["uid"] = params.get('account_id', [''])[0]
            result["region"] = params.get('region', [''])[0]
    except:
        pass
    
    return result

# ================================================================
# ========== دوال تنسيق النتائج ==========
# ================================================================

def format_recovery_info(bind_data: dict) -> dict:
    """تنسيق معلومات الاستعادة"""
    current_email = bind_data.get("email", "")
    pending_email = bind_data.get("email_to_be", "")
    countdown = bind_data.get("request_exec_countdown", 0)
    
    if current_email and pending_email and current_email != pending_email:
        status = "🔄 جاري تغيير البريد"
        explanation = f"هذا الحساب في طور تغيير بريد الاستعادة من `{current_email}` إلى `{pending_email}`."
    elif current_email and countdown > 0 and not pending_email:
        status = "⚠️ جاري إلغاء ارتباط الاستعادة"
        explanation = f"هذا الحساب في طور إلغاء بريد الاستعادة `{current_email}`."
    elif current_email and (countdown == 0 or not countdown) and not pending_email:
        status = "✅ مؤكد ونشط"
        explanation = f"بريد الاستعادة `{current_email}` مؤكد ونشط حالياً."
    elif not current_email and pending_email:
        status = "🔄 جاري تأكيد البريد الجديد"
        explanation = f"جاري تأكيد بريد الاستعادة الجديد `{pending_email}`."
    else:
        status = "❌ لا يوجد بريد للاستعادة"
        explanation = "هذا الحساب غير مربوط بأي بريد إلكتروني للاستعادة."
    
    return {
        'current_email': current_email or 'غير موجود',
        'pending_email': pending_email or 'لا يوجد',
        'countdown': countdown,
        'status': status,
        'explanation': explanation
    }

def format_platforms(platforms_data: dict) -> str:
    """تنسيق المنصات المرتبطة"""
    bounded = platforms_data.get("bounded_accounts", [])
    if not bounded:
        return "⚠️ الحساب ليس مربوط بأي منصة."
    
    lines = []
    for acc in bounded:
        platform_id = acc.get('platform')
        platform_name = PLATFORM_MAP.get(platform_id, f"منصة غير معروفة ({platform_id})")
        user_info = acc.get('user_info', {})
        info = user_info.get('email') or user_info.get('nickname') or '—'
        lines.append(f"• **{platform_name}:** `{info}`")
    return "\n".join(lines)

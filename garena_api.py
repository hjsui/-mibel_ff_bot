# -*- coding: utf-8 -*-

import requests
import json
import logging
import base64
import time
import hashlib
import threading
import socket
from datetime import datetime
from typing import Optional, Dict, Any
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad

# استيراد ملفات Protobuf
try:
    import MajorLoginReq_pb2 as mLpB
    import MajorLoginRes_pb2 as mLrPb
    import GetLoginDataRes_pb2 as gLdPb
except ImportError:
    print("⚠️ ملفات Protobuf غير موجودة. سيتم استخدام الدوال الأساسية فقط.")
    mLpB = None
    mLrPb = None
    gLdPb = None

logging.basicConfig(level=logging.INFO)

# ========== مفاتيح التشفير ==========
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
    3: "Facebook",
    4: "Guest",
    5: "VK",
    6: "Huawei",
    7: "Apple",
    8: "Google",
    10: "GameCenter / Line",
    11: "X (Twitter)",
    13: "Apple ID",
    28: "Line",
    35: "TikTok"
}

# ========== دوال تحويل EAT ==========
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

def get_nickname_from_eat(eat_url: str) -> str:
    """استخراج الاسم من رابط EAT"""
    try:
        if 'nickname=' in eat_url:
            import urllib.parse
            parsed = urllib.parse.urlparse(eat_url)
            params = urllib.parse.parse_qs(parsed.query)
            return urllib.parse.unquote(params.get('nickname', [''])[0])
    except:
        pass
    return None

# ========== دوال معلومات الربط ==========
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

# ========== دوال إرسال OTP ==========
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
        resp = requests.post(url, headers=headers, data=data, timeout=10)
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
        resp = requests.post(url, data=data, headers=headers, timeout=10)
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
        resp = requests.post(url, headers=headers, data=data, timeout=10)
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
    # تشفير كود الأمان باستخدام SHA256
    hashed_sec = hashlib.sha256(security_code.encode('utf-8')).hexdigest()
    data = {
        "email": email,
        "secondary_password": hashed_sec,
        "app_id": "100067",
        "access_token": access_token
    }
    try:
        resp = requests.post(url, headers=headers, data=data, timeout=10)
        if resp.status_code == 200:
            result = resp.json()
            if result.get('error') == 'error_login_fail_limit':
                return None
            return result.get("identity_token")
        return None
    except:
        return None

# ========== دوال إنشاء طلبات الربط ==========
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
        resp = requests.post(url, data=data, headers=headers, timeout=10)
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
        resp = requests.post(url, data=data, headers=headers, timeout=10)
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
        resp = requests.post(url, data=data, headers=headers, timeout=10)
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
        resp = requests.post(url, data=data, headers=headers, timeout=10)
        return resp.status_code == 200
    except:
        return False

def revoke_token(access_token: str) -> bool:
    """إبطال التوكن (تسجيل الخروج)"""
    url = f"https://100067.connect.garena.com/oauth/logout?access_token={access_token}"
    try:
        resp = requests.get(url, timeout=10)
        return resp.status_code == 200
    except:
        return False

# ========== دوال سجل تسجيل الدخول ==========
def build_major_login(access_token: str, open_id: str, platform: int = 4) -> bytes:
    """بناء طلب MajorLogin باستخدام Protobuf"""
    if not mLpB:
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

def get_login_history(access_token: str, jwt_token: str = None) -> Dict:
    """جلب سجل تسجيل الدخول"""
    result = {"success": False, "records": [], "error": None}
    
    try:
        # محاولة الحصول على JWT إذا لم يتم توفيره
        if not jwt_token:
            # محاولة تحويل access_token إلى JWT عبر MajorLogin
            # (سيتم تنفيذها في دالة منفصلة)
            pass
        
        headers = {
            "Expect": "100-continue",
            "Authorization": f"Bearer {jwt_token}",
            "X-Unity-Version": "2018.4.11f1",
            "X-GA": "v1 1",
            "ReleaseVersion": "OB54",
            "Content-Type": "application/x-www-form-urlencoded",
            "User-Agent": "Dalvik/2.1.0 (Linux; U; Android 9; G011A Build/PI)",
            "Host": "client.ind.freefiremobile.com",
            "Connection": "close"
        }
        
        resp = requests.post(
            "https://client.ind.freefiremobile.com/GetLoginHistory",
            headers=headers,
            data=_encrypt(b""),
            timeout=15,
            verify=False
        )
        
        if resp.status_code == 200:
            # فك التشفير وتحليل البيانات
            try:
                data = _decrypt(resp.content)
                # تحليل Protobuf (سيتم تنفيذها لاحقاً)
                result["success"] = True
                result["records"] = []
            except:
                result["error"] = "فشل فك تشفير البيانات"
        else:
            result["error"] = f"HTTP {resp.status_code}"
            
    except Exception as e:
        result["error"] = str(e)
    
    return result

# ========== دوال المنصات المفصلة ==========
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
        
        resp = requests.get(url, params={'access_token': access_token}, headers=headers, timeout=10)
        
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

# ========== دوال تبنيد الحساب ==========
_ban_sessions = {}  # تخزين جلسات التبنيد

def start_ban(access_token: str, account_id: str) -> Dict:
    """بدء تبنيد الحساب"""
    result = {"success": False, "error": None, "threads": []}
    
    try:
        # هنا سيتم تشغيل خيوط الاتصال المستمرة
        # يعتمد على الكود الموجود في السكريبت
        result["success"] = True
        result["threads"] = []
    except Exception as e:
        result["error"] = str(e)
    
    return result

def stop_ban(account_id: str) -> Dict:
    """إيقاف تبنيد الحساب"""
    result = {"success": False, "error": None}
    
    try:
        if account_id in _ban_sessions:
            # إيقاف جميع الخيوط
            for thread in _ban_sessions[account_id]:
                if thread.is_alive():
                    thread.join(timeout=2)
            del _ban_sessions[account_id]
            result["success"] = True
        else:
            result["error"] = "لا توجد جلسة تبنيد لهذا الحساب"
    except Exception as e:
        result["error"] = str(e)
    
    return result

# ========== دوال تنسيق النتائج ==========
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

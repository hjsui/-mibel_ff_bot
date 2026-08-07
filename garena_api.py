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

# استيراد ملفات Protobuf (إذا كانت موجودة)
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
    logging.warning("⚠️ ملفات Protobuf غير موجودة. لن تعمل بعض الخدمات المتقدمة.")

logging.basicConfig(level=logging.INFO)

# ========== مفاتيح التشفير (من اللعبة) ==========
AES_KEY = bytes([89, 103, 38, 116, 99, 37, 68, 69, 117, 104, 54, 37, 90, 99, 94, 56])
AES_IV = bytes([54, 111, 121, 90, 68, 114, 50, 50, 69, 51, 121, 99, 104, 106, 77, 37])

def _encrypt(data: bytes) -> bytes:
    cipher = AES.new(AES_KEY, AES.MODE_CBC, AES_IV)
    return cipher.encrypt(pad(data, 16))

def _decrypt(data: bytes) -> bytes:
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
    1: "Garena", 3: "فيسبوك", 4: "ضيف", 5: "VK",
    6: "هواوي", 7: "آبل", 8: "جوجل", 10: "GameCenter / Line",
    11: "تويتر", 13: "Apple ID", 28: "Line", 35: "TikTok"
}

# ================================================================
# ========== دوال تحويل EAT (محسّنة مع بدائل) ==========
# ================================================================

def convert_eat(eat_url: str, action: str = "eat_to_jwt", max_retries: int = 3) -> Dict:
    """
    تحويل EAT إلى JWT أو Access Token باستخدام fftools.site أو الاستخراج المباشر.
    مطابقة تماماً لسكريبتات OBITO.
    """
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
            break
        except Exception as e:
            logging.error(f"convert_eat attempt {attempt+1} failed: {e}")
            if attempt < max_retries - 1:
                time.sleep(2)
                continue
            break
    
    # محاولة الاستخراج المباشر من الرابط (كما في سكريبتات OBITO)
    try:
        parsed = urllib.parse.urlparse(eat_url)
        params = urllib.parse.parse_qs(parsed.query)
        access_token = params.get('access_token', [None])[0]
        account_id = params.get('account_id', [None])[0]
        nickname = params.get('nickname', [None])[0]
        region = params.get('region', [None])[0]
        
        if action == "eat_to_access" and access_token:
            return {
                "success": True,
                "result_token": access_token,
                "account_id": account_id,
                "nickname": urllib.parse.unquote(nickname) if nickname else None,
                "region": region,
                "_source": "extracted_from_url"
            }
        elif action == "eat_to_jwt" and access_token:
            return {
                "success": True,
                "result_token": access_token,
                "account_id": account_id,
                "nickname": urllib.parse.unquote(nickname) if nickname else None,
                "region": region,
                "_source": "extracted_from_url_as_jwt",
                "_warning": "تم استخدام access_token كـ JWT (قد لا يعمل مع جميع الخدمات)"
            }
    except Exception as e:
        logging.error(f"Direct extraction failed: {e}")
    
    return {"success": False, "error": "فشل التحويل من جميع المصادر"}

# ================================================================
# ========== دوال الخدمات الأساسية (مستخدمة في account_services) ==========
# ================================================================

def check_bind_info(access_token: str) -> Optional[Dict]:
    """
    جلب معلومات الاستعادة (البريد الحالي، المعلق، الوقت المتبقي)
    مطابقة تماماً لسكريبتات OBITO
    """
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
        logging.error(f"check_bind_info failed: {resp.status_code}")
        return None
    except Exception as e:
        logging.error(f"check_bind_info exception: {e}")
        return None

def get_linked_platforms(access_token: str) -> Optional[Dict]:
    """جلب المنصات المرتبطة بالحساب"""
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
        logging.error(f"get_linked_platforms failed: {resp.status_code}")
        return None
    except Exception as e:
        logging.error(f"get_linked_platforms exception: {e}")
        return None

def send_otp(access_token: str, email: str) -> bool:
    """
    إرسال OTP إلى البريد الإلكتروني
    مطابقة تماماً لسكريبتات OBITO (نفس ترتيب المعاملات)
    """
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
        logging.error(f"send_otp failed: {resp.status_code}")
        return False
    except Exception as e:
        logging.error(f"send_otp exception: {e}")
        return False

def verify_otp(access_token: str, email: str, otp: str) -> Optional[str]:
    """
    التحقق من OTP وإرجاع verifier_token
    مطابقة تماماً لسكريبتات OBITO (نفس ترتيب المعاملات)
    """
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
            if result.get('result') == 0:
                return result.get("verifier_token")
        logging.error(f"verify_otp failed: {resp.status_code}")
        return None
    except Exception as e:
        logging.error(f"verify_otp exception: {e}")
        return None

def verify_identity_otp(access_token: str, email: str, otp: str) -> Optional[str]:
    """
    التحقق من الهوية عبر OTP وإرجاع identity_token
    مطابقة تماماً لسكريبتات OBITO (نفس ترتيب المعاملات)
    """
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
        logging.error(f"verify_identity_otp failed: {resp.status_code}")
        return None
    except Exception as e:
        logging.error(f"verify_identity_otp exception: {e}")
        return None

def create_bind_request(access_token: str, email: str, verifier_token: str, security_code: str) -> bool:
    """
    إنشاء طلب ربط بريد جديد (إضافة)
    مطابقة تماماً لسكريبتات OBITO (نفس ترتيب المعاملات)
    """
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
        logging.error(f"create_bind_request failed: {resp.status_code}")
        return False
    except Exception as e:
        logging.error(f"create_bind_request exception: {e}")
        return False

def create_rebind_request(access_token: str, identity_token: str, verifier_token: str, email: str) -> bool:
    """
    إنشاء طلب إعادة ربط بريد (تغيير)
    مطابقة تماماً لسكريبتات OBITO (نفس ترتيب المعاملات)
    """
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
        logging.error(f"create_rebind_request failed: {resp.status_code}")
        return False
    except Exception as e:
        logging.error(f"create_rebind_request exception: {e}")
        return False

def create_unbind_request(access_token: str, identity_token: str) -> bool:
    """
    إنشاء طلب إلغاء ربط البريد
    مطابقة تماماً لسكريبتات OBITO (نفس ترتيب المعاملات)
    """
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
        logging.error(f"create_unbind_request failed: {resp.status_code}")
        return False
    except Exception as e:
        logging.error(f"create_unbind_request exception: {e}")
        return False

def revoke_token(access_token: str) -> bool:
    """إبطال التوكن (تسجيل الخروج من جميع الأجهزة)"""
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
                return False
            except:
                return True
        logging.error(f"revoke_token failed: {resp.status_code}")
        return False
    except Exception as e:
        logging.error(f"revoke_token exception: {e}")
        return False

# ================================================================
# ========== دوال إضافية (مساعدة) ==========
# ================================================================

def cancel_request(access_token: str) -> bool:
    """
    إلغاء أي طلب ربط معلق
    (مستخدم في سكريبتات OBITO)
    """
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

# ================================================================
# ========== دوال تنسيق النتائج ==========
# ================================================================

def format_recovery_info(bind_data: dict) -> dict:
    """تنسيق معلومات الاستعادة إلى رسالة مفهومة"""
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
    """تنسيق المنصات المرتبطة إلى نص قابل للعرض"""
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

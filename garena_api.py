# -*- coding: utf-8 -*-

import requests
import json
import logging
import base64
import time
from typing import Optional, Dict, Any

logging.basicConfig(level=logging.INFO)

# ========== دوال مساعدة ==========
def _log_response(name, resp):
    try:
        logging.info(f"[{name}] Status: {resp.status_code}")
        logging.info(f"[{name}] Response: {resp.text[:300]}")
    except:
        pass

def _decode_nickname(encoded: str) -> str:
    XOR_SECRET = b"1e5898ccb8dfdd921f9bdea848768b64a201"
    try:
        raw = base64.b64decode(encoded)
        dec = bytearray()
        for i, b in enumerate(raw):
            dec.append(b ^ XOR_SECRET[i % len(XOR_SECRET)])
        return dec.decode('utf-8', errors='replace')
    except:
        return encoded

def _decode_jwt(token: str) -> Optional[Dict]:
    try:
        parts = token.split('.')
        if len(parts) != 3:
            return None
        payload_b64 = parts[1] + '=' * ((4 - len(parts[1]) % 4) % 4)
        payload = json.loads(base64.urlsafe_b64decode(payload_b64).decode('utf-8'))
        if 'nickname' in payload and isinstance(payload['nickname'], str):
            payload['nickname'] = _decode_nickname(payload['nickname'])
        return payload
    except:
        return None

# ========== دوال تحويل EAT ==========
def convert_eat(eat_url, action="eat_to_jwt"):
    url = "https://www.fftools.site/api/verify-token"
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36",
        "Origin": "https://www.fftools.site",
        "Referer": "https://www.fftools.site/free-fire-token-generator"
    }
    payload = {"token": eat_url, "action": action}
    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=15)
        if resp.status_code == 200:
            return resp.json()
        else:
            return {"success": False, "error": f"HTTP {resp.status_code}"}
    except Exception as e:
        return {"success": False, "error": str(e)}

# ========== دوال الخدمات الأساسية ==========
def check_bind_info(access_token: str) -> Optional[Dict]:
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

def send_otp(email: str, access_token: str) -> bool:
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

def verify_otp(otp: str, email: str, access_token: str) -> Optional[str]:
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

def cancel_request(access_token: str) -> bool:
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

def create_rebind_request(identity_token: str, verifier_token: str, access_token: str, email: str) -> bool:
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

def create_unbind_request(identity_token: str, access_token: str) -> bool:
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

def revoke_token(access_token: str) -> bool:
    url = f"https://100067.connect.garena.com/oauth/logout?access_token={access_token}"
    try:
        resp = requests.get(url, timeout=10)
        return resp.status_code == 200
    except:
        return False

# ========== دوال تنسيق النتائج ==========
def format_recovery_info(bind_data: dict) -> dict:
    current_email = bind_data.get("email", "")
    pending_email = bind_data.get("email_to_be", "")
    countdown = bind_data.get("request_exec_countdown", 0)
    
    if current_email and pending_email and current_email != pending_email:
        status = "🔄 جاري تغيير البريد"
        explanation = f"هذا الحساب في طور تغيير بريد الاستعادة من `{current_email}` إلى `{pending_email}`.\nيبقى `{countdown}` ثانية لإتمام العملية."
    elif current_email and countdown > 0 and not pending_email:
        status = "⚠️ جاري إلغاء ارتباط الاستعادة"
        explanation = f"هذا الحساب في طور إلغاء بريد الاستعادة `{current_email}`.\nسيتم إلغاء هذا البريد نهائياً بعد `{countdown}` ثانية."
    elif current_email and (countdown == 0 or not countdown) and not pending_email:
        status = "✅ مؤكد ونشط"
        explanation = f"بريد الاستعادة `{current_email}` مؤكد ونشط حالياً."
    elif not current_email and pending_email:
        status = "🔄 جاري تأكيد البريد الجديد"
        explanation = f"جاري تأكيد بريد الاستعادة الجديد `{pending_email}`.\nيبقى `{countdown}` ثانية لإتمام العملية."
    else:
        status = "❌ لا يوجد بريد للاستعادة"
        explanation = "هذا الحساب غير مربوط بأي بريد إلكتروني للاستعادة."
    
    if countdown > 0:
        days = countdown // 86400
        hours = (countdown % 86400) // 3600
        minutes = (countdown % 3600) // 60
        if days > 0:
            time_str = f"{days} يوم، {hours} ساعة، {minutes} دقيقة"
        elif hours > 0:
            time_str = f"{hours} ساعة، {minutes} دقيقة"
        else:
            time_str = f"{minutes} دقيقة"
    else:
        time_str = "غير محدد"
    
    return {
        'current_email': current_email or 'غير موجود',
        'pending_email': pending_email or 'لا يوجد',
        'countdown': time_str,
        'status': status,
        'explanation': explanation
    }

def format_platforms(platforms_data: dict) -> str:
    bounded = platforms_data.get("bounded_accounts", [])
    if not bounded:
        return "⚠️ الحساب ليس مربوط بأي منصة أو ربط ثنوي حالياً.\nيمكنك ربط حسابك بمنصات مثل فيسبوك، جوجل، تويتر، هواوي، VK، آبل لتعزيز الأمان."
    
    platform_map = {
        3: "فيسبوك",
        8: "جوجل",
        10: "آبل",
        5: "VK",
        11: "تويتر",
        7: "هواوي",
    }
    
    lines = []
    for acc in bounded:
        platform_id = acc.get('platform')
        platform_name = platform_map.get(platform_id, f"منصة غير معروفة ({platform_id})")
        user_info = acc.get('user_info', {})
        info = user_info.get('email') or user_info.get('nickname') or '—'
        lines.append(f"• **{platform_name}:** `{info}`")
    return "\n".join(lines)

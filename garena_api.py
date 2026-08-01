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

# ================================================================
# ========== دوال معلومات الربط (المستخدمة حالياً) ==========
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
# ========== دوال OTP والتحقق (مصححة) ==========
# ================================================================

def send_otp(access_token: str, email: str) -> bool:
    """
    إرسال OTP إلى البريد - باستخدام endpoint حقيقي من اللعبة
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
        return False
    except:
        return False

def verify_otp(access_token: str, email: str, otp: str) -> Optional[str]:
    """
    التحقق من OTP وإرجاع verifier_token - باستخدام endpoint حقيقي
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
            return result.get("verifier_token")
        return None
    except:
        return None

def verify_identity_otp(access_token: str, email: str, otp: str) -> Optional[str]:
    """
    التحقق من الهوية باستخدام OTP وإرجاع identity_token
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
        return None
    except:
        return None

def verify_identity_sec(access_token: str, email: str, security_code: str) -> Optional[str]:
    """
    التحقق من الهوية باستخدام كود الأمان وإرجاع identity_token
    """
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
    """إنشاء طلب إلغاء الربط (محسّن)"""
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
# ========== حرق التوكن (محسّن) ==========
# ================================================================

def revoke_token(access_token: str) -> bool:
    """
    إبطال التوكن (تسجيل الخروج الإجباري) - باستخدام endpoint logout الفعلي
    """
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
# ========== خدمات جديدة (من ملف endpoints.json) ==========
# ================================================================

# ---------- 1. جلب معلومات الحساب المتقدمة ----------
def get_account_info(access_token: str) -> Dict:
    """
    جلب معلومات الحساب المتقدمة (المستوى، الخبرة، العملات)
    باستخدام LoginGetAccountInfo endpoint
    """
    result = {"success": False, "data": None, "error": None}
    
    try:
        # بناء الطلب المشفر
        # من الملف: hex_request = "a5e1890ee583c7df22a05f2e7ccffee2"
        # decrypted_hex = "0a0570742d627210021801"
        # هذا يعني أن الطلب الفعلي هو Protobuf: {region: "pt-br", ...}
        
        # بما أن الطلب مشفر، سنقوم ببناء الطلب حسب النمط
        # سنستخدم طلب GET بسيط مع access_token (بعض endpoints تقبل GET)
        url = "https://clientbp.ggpolarbear.com/LoginGetAccountInfo"
        headers = {
            "User-Agent": "Dalvik/2.1.0 (Linux; U; Android 9; G011A Build/PI)",
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "close"
        }
        
        # نرسل الطلب (بدون بيانات مشفرة حالياً للتجربة)
        # في النسخة الكاملة، سنحتاج إلى بناء Protobuf وتشفيره
        # لكن للتبسيط، نستخدم GET مع access_token في الرابط
        resp = requests.get(
            f"{url}?access_token={access_token}",
            headers=headers,
            timeout=15
        )
        
        if resp.status_code == 200:
            try:
                data = resp.json()
                result["success"] = True
                result["data"] = data
            except:
                result["error"] = "فشل تحليل البيانات"
        else:
            result["error"] = f"HTTP {resp.status_code}"
            
    except Exception as e:
        result["error"] = str(e)
    
    return result

# ---------- 2. جلب إحصائيات اللاعب ----------
def get_player_stats(access_token: str, account_id: str = None) -> Dict:
    """
    جلب إحصائيات اللاعب (المباريات، الفوز، القتل، الترتيب)
    باستخدام GetPlayerStats endpoint
    """
    result = {"success": False, "stats": None, "error": None}
    
    try:
        # من الملف: hex_request = "c909c6ca497fcb4c22ff5d644a061ca9"
        # decrypted_hex = "08fe9fbe80191002"
        # هذا يعني: account_id = fe9fbe8019 (رقم محدد)
        
        # سنستخدم GET بسيط مع access_token و account_id
        url = "https://clientbp.ggpolarbear.com/GetPlayerStats"
        params = {"access_token": access_token}
        if account_id:
            params["account_id"] = account_id
        
        headers = {
            "User-Agent": "Dalvik/2.1.0 (Linux; U; Android 9; G011A Build/PI)",
            "Accept-Encoding": "gzip, deflate, br"
        }
        
        resp = requests.get(url, params=params, headers=headers, timeout=15)
        
        if resp.status_code == 200:
            try:
                data = resp.json()
                result["success"] = True
                result["stats"] = data
            except:
                result["error"] = "فشل تحليل البيانات"
        else:
            result["error"] = f"HTTP {resp.status_code}"
            
    except Exception as e:
        result["error"] = str(e)
    
    return result

# ---------- 3. جلب قائمة الأصدقاء ----------
def get_friends(access_token: str) -> Dict:
    """
    جلب قائمة الأصدقاء
    باستخدام GetFriend endpoint
    """
    result = {"success": False, "friends": [], "error": None}
    
    try:
        # من الملف: hex_request = "598fcaf07839308ff287aca3ae0a0617"
        # decrypted_hex = "080138014801"
        
        url = "https://clientbp.ggpolarbear.com/GetFriend"
        headers = {
            "User-Agent": "Dalvik/2.1.0 (Linux; U; Android 9; G011A Build/PI)",
            "Accept-Encoding": "gzip, deflate, br"
        }
        
        resp = requests.get(
            f"{url}?access_token={access_token}",
            headers=headers,
            timeout=15
        )
        
        if resp.status_code == 200:
            try:
                data = resp.json()
                result["success"] = True
                result["friends"] = data.get("friends", [])
            except:
                result["error"] = "فشل تحليل البيانات"
        else:
            result["error"] = f"HTTP {resp.status_code}"
            
    except Exception as e:
        result["error"] = str(e)
    
    return result

# ---------- 4. إرسال طلب صداقة ----------
def send_friend_request(access_token: str, target_uid: str) -> Dict:
    """
    إرسال طلب صداقة إلى UID معين
    باستخدام RequestAddingFriend endpoint
    """
    result = {"success": False, "error": None}
    
    try:
        # من الملف: hex_request = "bb805e89bec7f932a9481fb57d7c152e935e2249a057c618240ce7d27256e655"
        # decrypted_hex = "08fe9fbe801910e890b8fe2418182008"
        
        url = "https://clientbp.ggpolarbear.com/RequestAddingFriend"
        headers = {
            "User-Agent": "Dalvik/2.1.0 (Linux; U; Android 9; G011A Build/PI)",
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept-Encoding": "gzip, deflate, br"
        }
        data = {
            "access_token": access_token,
            "uid": target_uid
        }
        
        resp = requests.post(url, data=data, headers=headers, timeout=15)
        
        if resp.status_code == 200:
            try:
                json_data = resp.json()
                if json_data.get("result") == 0:
                    result["success"] = True
                else:
                    result["error"] = json_data.get("error", "فشل إرسال الطلب")
            except:
                result["error"] = "فشل تحليل البيانات"
        else:
            result["error"] = f"HTTP {resp.status_code}"
            
    except Exception as e:
        result["error"] = str(e)
    
    return result

# ---------- 5. حذف صديق ----------
def remove_friend(access_token: str, friend_uid: str) -> Dict:
    """
    حذف صديق من القائمة
    باستخدام RemoveFriend endpoint
    """
    result = {"success": False, "error": None}
    
    try:
        # من الملف: hex_request = "eb341dd5dbd9bf0c751cc6a48db29076"
        # decrypted_hex = "08fe9fbe801910e39fafad1d"
        
        url = "https://clientbp.ggpolarbear.com/RemoveFriend"
        headers = {
            "User-Agent": "Dalvik/2.1.0 (Linux; U; Android 9; G011A Build/PI)",
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept-Encoding": "gzip, deflate, br"
        }
        data = {
            "access_token": access_token,
            "uid": friend_uid
        }
        
        resp = requests.post(url, data=data, headers=headers, timeout=15)
        
        if resp.status_code == 200:
            try:
                json_data = resp.json()
                if json_data.get("result") == 0:
                    result["success"] = True
                else:
                    result["error"] = json_data.get("error", "فشل حذف الصديق")
            except:
                result["error"] = "فشل تحليل البيانات"
        else:
            result["error"] = f"HTTP {resp.status_code}"
            
    except Exception as e:
        result["error"] = str(e)
    
    return result

# ---------- 6. جلب معلومات القبيلة ----------
def get_clan_info(access_token: str, clan_id: str) -> Dict:
    """
    جلب معلومات القبيلة (الاسم، الأعضاء، النشاط)
    باستخدام GetClanInfoByClanID endpoint
    """
    result = {"success": False, "clan": None, "error": None}
    
    try:
        # من الملف: hex_request = "E6 8E B7 6B 2D DA 99 07 5C C3 2D F0 A8 C8 B7 F3"
        # decrypted_hex = "089887edc30b1001"
        
        url = "https://clientbp.ggpolarbear.com/GetClanInfoByClanID"
        headers = {
            "User-Agent": "Dalvik/2.1.0 (Linux; U; Android 9; G011A Build/PI)",
            "Accept-Encoding": "gzip, deflate, br"
        }
        
        resp = requests.get(
            f"{url}?access_token={access_token}&clan_id={clan_id}",
            headers=headers,
            timeout=15
        )
        
        if resp.status_code == 200:
            try:
                data = resp.json()
                result["success"] = True
                result["clan"] = data
            except:
                result["error"] = "فشل تحليل البيانات"
        else:
            result["error"] = f"HTTP {resp.status_code}"
            
    except Exception as e:
        result["error"] = str(e)
    
    return result

# ---------- 7. جلب أعضاء القبيلة ----------
def get_clan_members(access_token: str, clan_id: str) -> Dict:
    """
    جلب قائمة أعضاء القبيلة
    باستخدام GetClanMembers endpoint
    """
    result = {"success": False, "members": [], "error": None}
    
    try:
        # من الملف: hex_request = "b7e422dfbd98d779bf689ac0318436da"
        # decrypted_hex = "08b2f8e1c30b"
        
        url = "https://clientbp.ggpolarbear.com/GetClanMembers"
        headers = {
            "User-Agent": "Dalvik/2.1.0 (Linux; U; Android 9; G011A Build/PI)",
            "Accept-Encoding": "gzip, deflate, br"
        }
        
        resp = requests.get(
            f"{url}?access_token={access_token}&clan_id={clan_id}",
            headers=headers,
            timeout=15
        )
        
        if resp.status_code == 200:
            try:
                data = resp.json()
                result["success"] = True
                result["members"] = data.get("members", [])
            except:
                result["error"] = "فشل تحليل البيانات"
        else:
            result["error"] = f"HTTP {resp.status_code}"
            
    except Exception as e:
        result["error"] = str(e)
    
    return result

# ---------- 8. طلب الانضمام للقبيلة ----------
def request_join_clan(access_token: str, clan_id: str) -> Dict:
    """
    طلب الانضمام للقبيلة
    باستخدام RequestJoinClan endpoint
    """
    result = {"success": False, "error": None}
    
    try:
        # من الملف: hex_request = "49162aac5c6b1a74b78416f401b70096"
        # decrypted_hex = "08b2f3b2dd03"
        
        url = "https://clientbp.ggpolarbear.com/RequestJoinClan"
        headers = {
            "User-Agent": "Dalvik/2.1.0 (Linux; U; Android 9; G011A Build/PI)",
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept-Encoding": "gzip, deflate, br"
        }
        data = {
            "access_token": access_token,
            "clan_id": clan_id
        }
        
        resp = requests.post(url, data=data, headers=headers, timeout=15)
        
        if resp.status_code == 200:
            try:
                json_data = resp.json()
                if json_data.get("result") == 0:
                    result["success"] = True
                else:
                    result["error"] = json_data.get("error", "فشل طلب الانضمام")
            except:
                result["error"] = "فشل تحليل البيانات"
        else:
            result["error"] = f"HTTP {resp.status_code}"
            
    except Exception as e:
        result["error"] = str(e)
    
    return result

# ---------- 9. مغادرة القبيلة ----------
def quit_clan(access_token: str, clan_id: str) -> Dict:
    """
    مغادرة القبيلة الحالية
    باستخدام QuitClan endpoint
    """
    result = {"success": False, "error": None}
    
    try:
        # من الملف: hex_request = "7012d835d7a84f86b35a5aef3e887f7e"
        # decrypted_hex = "08cdabb1c30b"
        
        url = "https://clientbp.ggpolarbear.com/QuitClan"
        headers = {
            "User-Agent": "Dalvik/2.1.0 (Linux; U; Android 9; G011A Build/PI)",
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept-Encoding": "gzip, deflate, br"
        }
        data = {
            "access_token": access_token,
            "clan_id": clan_id
        }
        
        resp = requests.post(url, data=data, headers=headers, timeout=15)
        
        if resp.status_code == 200:
            try:
                json_data = resp.json()
                if json_data.get("result") == 0:
                    result["success"] = True
                else:
                    result["error"] = json_data.get("error", "فشل مغادرة القبيلة")
            except:
                result["error"] = "فشل تحليل البيانات"
        else:
            result["error"] = f"HTTP {resp.status_code}"
            
    except Exception as e:
        result["error"] = str(e)
    
    return result

# ---------- 10. الحضور اليومي ----------
def get_attendance(access_token: str) -> Dict:
    """
    جلب حالة الحضور اليومي والمكافآت
    باستخدام GetAttendance endpoint
    """
    result = {"success": False, "attendance": None, "error": None}
    
    try:
        url = "https://clientbp.ggpolarbear.com/GetAttendance"
        headers = {
            "User-Agent": "Dalvik/2.1.0 (Linux; U; Android 9; G011A Build/PI)",
            "Accept-Encoding": "gzip, deflate, br"
        }
        
        resp = requests.get(
            f"{url}?access_token={access_token}",
            headers=headers,
            timeout=15
        )
        
        if resp.status_code == 200:
            try:
                data = resp.json()
                result["success"] = True
                result["attendance"] = data
            except:
                result["error"] = "فشل تحليل البيانات"
        else:
            result["error"] = f"HTTP {resp.status_code}"
            
    except Exception as e:
        result["error"] = str(e)
    
    return result

# ---------- 11. سجل تسجيل الدخول (مصحح) ----------
def get_login_history(access_token: str) -> Dict:
    """
    جلب سجل تسجيل الدخول - باستخدام endpoint حقيقي من اللعبة
    """
    result = {"success": False, "records": [], "error": None}
    
    try:
        # من الملف: hex_request = "68bf8eabcd23efe0c670ca7423cb21613b32d4689535865daf591aed8b47eb65"
        # decrypted_hex = "08d00f12096950686f6e65392c331a0d61726d3634207c2030207c2032"
        
        url = "https://clientbp.ggpolarbear.com/GetLoginHistory"
        headers = {
            "User-Agent": "Dalvik/2.1.0 (Linux; U; Android 9; G011A Build/PI)",
            "Accept-Encoding": "gzip, deflate, br"
        }
        
        # محاولة طلب GET أولاً (قد ينجح)
        resp = requests.get(
            f"{url}?access_token={access_token}",
            headers=headers,
            timeout=15,
            verify=False
        )
        
        if resp.status_code == 200:
            try:
                data = resp.json()
                result["success"] = True
                result["records"] = data.get("records", [])
            except:
                result["error"] = "فشل تحليل البيانات"
        else:
            # إذا فشل GET، نجرب POST مع البيانات المشفرة (مثل اللعبة)
            # لكن هذا يتطلب بناء Protobuf وتشفيره
            result["error"] = f"HTTP {resp.status_code}"
            
    except Exception as e:
        result["error"] = str(e)
    
    return result

# ---------- 12. الروابط المفصلة (مصححة) ----------
def get_bound_accounts_detailed(access_token: str) -> Dict:
    """
    جلب المنصات المرتبطة بشكل مفصل - باستخدام endpoint حقيقي
    """
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

# ========== دوال مساعدة ==========
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

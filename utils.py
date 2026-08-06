# -*- coding: utf-8 -*-

import json
import base64
import requests
import time
import urllib.parse
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List

# تخزين بيانات المستخدمين مؤقتاً (في الذاكرة)
user_data_store = {}

# ========== دوال النصوص واللغة ==========
def get_text(user_id: int, key: str, **kwargs) -> str:
    """
    جلب النص المترجم حسب لغة المستخدم
    
    Args:
        user_id: معرف المستخدم
        key: مفتاح النص في قاموس الترجمات
        **kwargs: المعاملات الإضافية للتنسيق
    
    Returns:
        النص المترجم والمُنسق
    """
    if 'user_id' not in kwargs:
        kwargs['user_id'] = user_id
    
    lang = user_data_store.get(user_id, {}).get('lang', 'ar')
    from texts import TEXTS
    text = TEXTS.get(lang, TEXTS['ar']).get(key, key)
    return text.format(**kwargs) if kwargs else text

def get_user_lang(user_id: int) -> str:
    return user_data_store.get(user_id, {}).get('lang', 'ar')

def set_user_lang(user_id: int, lang: str) -> None:
    if user_id not in user_data_store:
        user_data_store[user_id] = {'lang': 'ar', 'accounts': []}
    user_data_store[user_id]['lang'] = lang

# ========== دوال إدارة الحسابات ==========
def get_user_accounts(user_id: int) -> List[Dict]:
    return user_data_store.get(user_id, {}).get('accounts', [])

def add_account(user_id: int, name: str, account_id: str, eat: str, region: str) -> bool:
    if user_id not in user_data_store:
        user_data_store[user_id] = {'lang': 'ar', 'accounts': []}
    for acc in user_data_store[user_id]['accounts']:
        if acc['id'] == account_id:
            return False
    user_data_store[user_id]['accounts'].append({
        'name': name,
        'id': account_id,
        'eat': eat,
        'region': region
    })
    return True

def delete_account(user_id: int, account_id: str) -> bool:
    accounts = user_data_store.get(user_id, {}).get('accounts', [])
    for i, acc in enumerate(accounts):
        if acc['id'] == account_id:
            del accounts[i]
            return True
    return False

def get_account_by_id(user_id: int, account_id: str) -> Optional[Dict]:
    accounts = get_user_accounts(user_id)
    for acc in accounts:
        if acc['id'] == account_id:
            return acc
    return None

# ========== دوال تحويل EAT (المحسّنة مع البدائل) ==========

def _extract_token_from_url(url: str) -> dict:
    """
    استخراج المعلومات من رابط EAT مباشرة (بدون اتصال خارجي)
    """
    result = {
        "success": False,
        "access_token": None,
        "account_id": None,
        "nickname": None,
        "region": None,
        "eat": None,
        "error": None
    }
    try:
        parsed = urllib.parse.urlparse(url)
        params = urllib.parse.parse_qs(parsed.query)
        
        # استخراج eat
        if 'eat' in params:
            result['eat'] = params['eat'][0]
        else:
            import re
            eat_match = re.search(r'eat=([^&]+)', url)
            if eat_match:
                result['eat'] = eat_match.group(1)
        
        # استخراج account_id
        if 'account_id' in params:
            result['account_id'] = params['account_id'][0]
        else:
            import re
            acc_match = re.search(r'account_id=([^&]+)', url)
            if acc_match:
                result['account_id'] = acc_match.group(1)
        
        # استخراج nickname
        if 'nickname' in params:
            result['nickname'] = urllib.parse.unquote(params['nickname'][0])
        else:
            import re
            nick_match = re.search(r'nickname=([^&]+)', url)
            if nick_match:
                result['nickname'] = urllib.parse.unquote(nick_match.group(1))
        
        # استخراج region
        if 'region' in params:
            result['region'] = params['region'][0]
        else:
            import re
            region_match = re.search(r'region=([^&]+)', url)
            if region_match:
                result['region'] = region_match.group(1)
        
        # استخراج access_token (إذا كان موجوداً في الرابط)
        if 'access_token' in params:
            result['access_token'] = params['access_token'][0]
            result['success'] = True
        elif result['eat']:
            # إذا لم يكن access_token موجوداً، نستخدم eat نفسه كـ access_token (محاكاة)
            result['access_token'] = result['eat']
            result['success'] = True
            result['warning'] = "تم استخدام eat كـ access_token (قد لا يعمل مع جميع الخدمات)"
        else:
            result['error'] = "لم يتم العثور على eat أو access_token في الرابط"
            
    except Exception as e:
        result['error'] = str(e)
    
    return result

def convert_eat(eat_url: str, action: str = "eat_to_jwt", max_retries: int = 2) -> Dict:
    """
    تحويل EAT إلى JWT أو Access Token.
    
    أولاً: محاولة استخدام fftools.site.
    ثانياً: إذا فشل، محاولة استخراج المعلومات مباشرة من الرابط.
    """
    # ===== المحاولة الأولى: fftools.site =====
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
            resp = requests.post(url, json=payload, headers=headers, timeout=15)
            if resp.status_code == 200:
                return resp.json()
            if 500 <= resp.status_code < 600 and attempt < max_retries - 1:
                time.sleep(2)
                continue
            # إذا فشل fftools، نخرج من المحاولات ونتجه للبديل
            break
        except Exception:
            if attempt < max_retries - 1:
                time.sleep(2)
                continue
            break
    
    # ===== المحاولة الثانية: استخراج مباشر من الرابط =====
    extracted = _extract_token_from_url(eat_url)
    if extracted.get("success"):
        if action == "eat_to_access":
            return {
                "success": True,
                "result_token": extracted.get("access_token"),
                "account_id": extracted.get("account_id"),
                "nickname": extracted.get("nickname"),
                "region": extracted.get("region"),
                "_source": "extracted_from_url",
                "_warning": extracted.get("warning")
            }
        elif action == "eat_to_jwt":
            # محاولة استخدام eat كـ JWT (نادراً ما يعمل)
            if extracted.get("eat"):
                return {
                    "success": True,
                    "result_token": extracted.get("eat"),
                    "account_id": extracted.get("account_id"),
                    "nickname": extracted.get("nickname"),
                    "region": extracted.get("region"),
                    "_source": "extracted_from_url_eat_as_jwt",
                    "_warning": "تم استخدام eat كـ JWT (قد لا يعمل مع جميع الخدمات)"
                }
            else:
                return {"success": False, "error": "لا يمكن تحويل eat إلى JWT عبر الاستخراج المباشر"}
    
    # ===== فشل جميع المحاولات =====
    return {"success": False, "error": "فشل التحويل من جميع المصادر (fftools.site غير متاح، والرابط لا يحتوي على معلومات كافية)"}

def get_access_token_for_account(account: Dict, user_id: int = None) -> Optional[str]:
    """
    استخراج access_token من EAT المحفوظ مع تخزين مؤقت
    """
    if account.get('access_token') and account.get('token_expiry'):
        if int(time.time()) < account.get('token_expiry', 0):
            return account.get('access_token')
    
    access_data = convert_eat(account['eat'], "eat_to_access")
    if access_data.get("success"):
        token = access_data.get("result_token")
        if token:
            account['access_token'] = token
            account['token_expiry'] = int(time.time()) + 86400
            return token
    
    return None

def decode_jwt(jwt_token: str) -> Dict:
    try:
        payload = jwt_token.split('.')[1]
        payload += '=' * (4 - len(payload) % 4)
        return json.loads(base64.b64decode(payload))
    except:
        return {}

# ========== دوال مساعدة ==========
def format_datetime(dt: datetime) -> str:
    return dt.strftime('%Y-%m-%d %H:%M:%S') if dt else 'غير محدد'

def is_eat_link(text: str) -> bool:
    return 'discstore.recargajogo.com.br' in text or 'ticket.kiosgamer.co.id' in text or 'eat=' in text

def extract_eat_link(text: str) -> str:
    if 'http' in text:
        return text.strip()
    return text.strip()

def get_eat_nickname(eat_url: str) -> str:
    try:
        if 'nickname=' in eat_url:
            parsed = urllib.parse.urlparse(eat_url)
            params = urllib.parse.parse_qs(parsed.query)
            return urllib.parse.unquote(params.get('nickname', [''])[0])
    except:
        pass
    return None

def get_eat_account_id(eat_url: str) -> str:
    try:
        if 'account_id=' in eat_url:
            parsed = urllib.parse.urlparse(eat_url)
            params = urllib.parse.parse_qs(parsed.query)
            return params.get('account_id', [''])[0]
    except:
        pass
    return None

def get_eat_region(eat_url: str) -> str:
    try:
        if 'region=' in eat_url:
            parsed = urllib.parse.urlparse(eat_url)
            params = urllib.parse.parse_qs(parsed.query)
            return params.get('region', ['ME'])[0]
    except:
        pass
    return 'ME'

def is_token_valid(account: Dict) -> bool:
    token = account.get('access_token')
    expiry = account.get('token_expiry')
    if not token:
        return False
    if expiry and int(time.time()) < expiry:
        return True
    return False

def update_account_token(user_id: int, account_id: str, access_token: str, expiry: int = None) -> bool:
    accounts = user_data_store.get(user_id, {}).get('accounts', [])
    for acc in accounts:
        if acc['id'] == account_id:
            acc['access_token'] = access_token
            if expiry:
                acc['token_expiry'] = expiry
            else:
                acc['token_expiry'] = int(time.time()) + 86400
            return True
    return False

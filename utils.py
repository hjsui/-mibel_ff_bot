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
    # إضافة user_id إلى kwargs إذا لم يكن موجوداً
    if 'user_id' not in kwargs:
        kwargs['user_id'] = user_id
    
    # تحديد لغة المستخدم
    lang = user_data_store.get(user_id, {}).get('lang', 'ar')
    
    # استيراد الترجمات
    from texts import TEXTS
    
    # جلب النص
    text = TEXTS.get(lang, TEXTS['ar']).get(key, key)
    
    # تنسيق النص مع المعاملات
    return text.format(**kwargs) if kwargs else text

def get_user_lang(user_id: int) -> str:
    """جلب لغة المستخدم"""
    return user_data_store.get(user_id, {}).get('lang', 'ar')

def set_user_lang(user_id: int, lang: str) -> None:
    """تغيير لغة المستخدم"""
    if user_id not in user_data_store:
        user_data_store[user_id] = {'lang': 'ar', 'accounts': []}
    user_data_store[user_id]['lang'] = lang

# ========== دوال إدارة الحسابات ==========
def get_user_accounts(user_id: int) -> List[Dict]:
    """جلب قائمة حسابات المستخدم"""
    return user_data_store.get(user_id, {}).get('accounts', [])

def add_account(user_id: int, name: str, account_id: str, eat: str, region: str) -> bool:
    """
    إضافة حساب جديد للمستخدم
    
    Returns:
        True إذا تمت الإضافة بنجاح، False إذا كان الحساب موجوداً مسبقاً
    """
    if user_id not in user_data_store:
        user_data_store[user_id] = {'lang': 'ar', 'accounts': []}
    
    # التحقق من عدم وجود الحساب مسبقاً
    for acc in user_data_store[user_id]['accounts']:
        if acc['id'] == account_id:
            return False
    
    # إضافة الحساب
    user_data_store[user_id]['accounts'].append({
        'name': name,
        'id': account_id,
        'eat': eat,
        'region': region
    })
    return True

def delete_account(user_id: int, account_id: str) -> bool:
    """
    حذف حساب من قائمة المستخدم
    
    Returns:
        True إذا تم الحذف بنجاح، False إذا لم يتم العثور على الحساب
    """
    accounts = user_data_store.get(user_id, {}).get('accounts', [])
    for i, acc in enumerate(accounts):
        if acc['id'] == account_id:
            del accounts[i]
            return True
    return False

def get_account_by_id(user_id: int, account_id: str) -> Optional[Dict]:
    """جلب حساب محدد بواسطة معرفه"""
    accounts = get_user_accounts(user_id)
    for acc in accounts:
        if acc['id'] == account_id:
            return acc
    return None

# ========== دوال تحويل EAT ==========
def convert_eat(eat_url: str, action: str = "eat_to_jwt", max_retries: int = 3) -> Dict:
    """
    تحويل EAT إلى JWT أو Access Token باستخدام fftools.site
    
    Args:
        eat_url: رابط EAT الكامل
        action: نوع التحويل ('eat_to_jwt' أو 'eat_to_access')
        max_retries: عدد مرات إعادة المحاولة
    
    Returns:
        قاموس يحتوي على النتيجة
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
            elif 500 <= resp.status_code < 600 and attempt < max_retries - 1:
                time.sleep(2)
                continue
            else:
                return {"success": False, "error": f"HTTP {resp.status_code}"}
        except requests.exceptions.Timeout:
            if attempt < max_retries - 1:
                time.sleep(2)
                continue
            return {"success": False, "error": "انتهت مهلة الاتصال، حاول مرة أخرى لاحقاً"}
        except Exception as e:
            if attempt < max_retries - 1:
                time.sleep(2)
                continue
            return {"success": False, "error": str(e)}
    
    return {"success": False, "error": "فشل بعد عدة محاولات"}

def get_access_token_for_account(account: Dict, user_id: int = None) -> Optional[str]:
    """
    استخراج access_token من EAT المحفوظ مع تخزين مؤقت
    
    Args:
        account: قاموس بيانات الحساب (يجب أن يحتوي على 'eat')
        user_id: معرف المستخدم (اختياري، للتخزين المؤقت)
    
    Returns:
        access_token إذا نجح التحويل، وإلا None
    """
    # التحقق من وجود access_token مخزناً مسبقاً
    if account.get('access_token') and account.get('token_expiry'):
        if int(time.time()) < account.get('token_expiry', 0):
            return account.get('access_token')
    
    # تحويل EAT إلى Access Token
    access_data = convert_eat(account['eat'], "eat_to_access")
    if access_data.get("success"):
        token = access_data.get("result_token")
        # تخزين التوكن مع صلاحية 24 ساعة
        account['access_token'] = token
        account['token_expiry'] = int(time.time()) + 86400  # 24 ساعة
        return token
    
    return None

def decode_jwt(jwt_token: str) -> Dict:
    """
    فك تشفير JWT واستخراج البيانات
    
    Args:
        jwt_token: رمز JWT
    
    Returns:
        قاموس يحتوي على البيانات المفككة
    """
    try:
        payload = jwt_token.split('.')[1]
        payload += '=' * (4 - len(payload) % 4)
        return json.loads(base64.b64decode(payload))
    except:
        return {}

# ========== دوال مساعدة ==========
def format_datetime(dt: datetime) -> str:
    """تنسيق التاريخ والوقت"""
    return dt.strftime('%Y-%m-%d %H:%M:%S') if dt else 'غير محدد'

def is_eat_link(text: str) -> bool:
    """التحقق مما إذا كان النص هو رابط EAT صالح"""
    return 'discstore.recargajogo.com.br' in text or 'ticket.kiosgamer.co.id' in text or 'eat=' in text

def extract_eat_link(text: str) -> str:
    """استخراج رابط EAT من النص"""
    if 'http' in text:
        return text.strip()
    return text.strip()

def get_eat_nickname(eat_url: str) -> str:
    """استخراج اسم المستخدم من رابط EAT"""
    try:
        if 'nickname=' in eat_url:
            parsed = urllib.parse.urlparse(eat_url)
            params = urllib.parse.parse_qs(parsed.query)
            return urllib.parse.unquote(params.get('nickname', [''])[0])
    except:
        pass
    return None

def get_eat_account_id(eat_url: str) -> str:
    """استخراج معرف الحساب من رابط EAT"""
    try:
        if 'account_id=' in eat_url:
            parsed = urllib.parse.urlparse(eat_url)
            params = urllib.parse.parse_qs(parsed.query)
            return params.get('account_id', [''])[0]
    except:
        pass
    return None

def get_eat_region(eat_url: str) -> str:
    """استخراج المنطقة من رابط EAT"""
    try:
        if 'region=' in eat_url:
            parsed = urllib.parse.urlparse(eat_url)
            params = urllib.parse.parse_qs(parsed.query)
            return params.get('region', ['ME'])[0]
    except:
        pass
    return 'ME'

def is_token_valid(account: Dict) -> bool:
    """التحقق من صحة التوكن المخزن"""
    token = account.get('access_token')
    expiry = account.get('token_expiry')
    if not token:
        return False
    if expiry and int(time.time()) < expiry:
        return True
    return False

def update_account_token(user_id: int, account_id: str, access_token: str, expiry: int = None) -> bool:
    """تحديث توكن الوصول للحساب"""
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

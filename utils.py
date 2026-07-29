# -*- coding: utf-8 -*-

import json
import base64
import requests
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List

# ========== تخزين بيانات المستخدمين مؤقتاً (في الذاكرة) ==========
user_data_store = {}  # {user_id: {'lang': 'ar'|'en', 'accounts': [...]}}

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
def convert_eat(eat_url: str, action: str = "eat_to_jwt") -> Dict:
    """
    تحويل EAT إلى JWT أو Access Token باستخدام fftools.site
    
    Args:
        eat_url: رابط EAT الكامل
        action: نوع التحويل ('eat_to_jwt' أو 'eat_to_access')
    
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
    
    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=15)
        if resp.status_code == 200:
            return resp.json()
        else:
            return {"success": False, "error": f"HTTP {resp.status_code}"}
    except Exception as e:
        return {"success": False, "error": str(e)}

def get_access_token_for_account(account: Dict) -> Optional[str]:
    """
    استخراج access_token من EAT المحفوظ
    
    Args:
        account: قاموس بيانات الحساب (يجب أن يحتوي على 'eat')
    
    Returns:
        access_token إذا نجح التحويل، وإلا None
    """
    access_data = convert_eat(account['eat'], "eat_to_access")
    if access_data.get("success"):
        return access_data.get("result_token")
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
    return 'ticket.kiosgamer.co.id' in text or 'eat=' in text

def extract_eat_link(text: str) -> str:
    """استخراج رابط EAT من النص"""
    # إذا كان النص يحتوي على رابط كامل
    if 'http' in text:
        return text.strip()
    # إذا كان مجرد رمز EAT
    return text.strip()

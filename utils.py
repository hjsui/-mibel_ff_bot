# -*- coding: utf-8 -*-

import json
import base64
import requests
import time
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List

# تخزين بيانات المستخدمين مؤقتاً (في الذاكرة)
user_data_store = {}

def get_text(user_id: int, key: str, **kwargs) -> str:
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

def get_user_accounts(user_id: int) -> List[Dict]:
    return user_data_store.get(user_id, {}).get('accounts', [])

def add_account(user_id: int, name: str, account_id: str, eat: str, region: str) -> bool:
    if user_id not in user_data_store:
        user_data_store[user_id] = {'lang': 'ar', 'accounts': []}
    for acc in user_data_store[user_id]['accounts']:
        if acc['id'] == account_id:
            return False
    user_data_store[user_id]['accounts'].append({
        'name': name, 'id': account_id, 'eat': eat, 'region': region
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

def convert_eat(eat_url: str, action: str = "eat_to_jwt", max_retries: int = 3) -> Dict:
    """
    تحويل EAT مع إعادة المحاولة عند الفشل
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
            resp = requests.post(url, json=payload, headers=headers, timeout=30)  # زيادة المهلة إلى 30 ثانية
            if resp.status_code == 200:
                return resp.json()
            else:
                # إذا كان الخطأ 5xx، نعيد المحاولة
                if 500 <= resp.status_code < 600 and attempt < max_retries - 1:
                    time.sleep(2)  # انتظار 2 ثانية قبل إعادة المحاولة
                    continue
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

def get_access_token_for_account(account: Dict) -> Optional[str]:
    """استخراج access_token مع إعادة المحاولة"""
    access_data = convert_eat(account['eat'], "eat_to_access")
    if access_data.get("success"):
        return access_data.get("result_token")
    return None

def decode_jwt(jwt_token: str) -> Dict:
    try:
        payload = jwt_token.split('.')[1]
        payload += '=' * (4 - len(payload) % 4)
        return json.loads(base64.b64decode(payload))
    except:
        return {}

def format_datetime(dt: datetime) -> str:
    return dt.strftime('%Y-%m-%d %H:%M:%S') if dt else 'غير محدد'

def is_eat_link(text: str) -> bool:
    return 'ticket.kiosgamer.co.id' in text or 'eat=' in text

def extract_eat_link(text: str) -> str:
    if 'http' in text:
        return text.strip()
    return text.strip()

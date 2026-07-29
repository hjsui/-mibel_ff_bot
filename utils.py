# -*- coding: utf-8 -*-

import json
import base64
import requests
from datetime import datetime, timedelta

# تخزين بيانات المستخدمين مؤقتاً (في الذاكرة)
user_data_store = {}

def get_text(user_id, key, **kwargs):
    # إضافة user_id إلى kwargs إذا لم يكن موجوداً
    if 'user_id' not in kwargs:
        kwargs['user_id'] = user_id
    lang = user_data_store.get(user_id, {}).get('lang', 'ar')
    from texts import TEXTS
    text = TEXTS.get(lang, TEXTS['ar']).get(key, key)
    return text.format(**kwargs) if kwargs else text

def get_user_accounts(user_id):
    return user_data_store.get(user_id, {}).get('accounts', [])

def add_account(user_id, name, account_id, eat, region):
    if user_id not in user_data_store:
        user_data_store[user_id] = {'lang': 'ar', 'accounts': []}
    for acc in user_data_store[user_id]['accounts']:
        if acc['id'] == account_id:
            return False
    user_data_store[user_id]['accounts'].append({
        'name': name, 'id': account_id, 'eat': eat, 'region': region
    })
    return True

def delete_account(user_id, account_id):
    accounts = user_data_store.get(user_id, {}).get('accounts', [])
    for i, acc in enumerate(accounts):
        if acc['id'] == account_id:
            del accounts[i]
            return True
    return False

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

def decode_jwt(jwt_token):
    try:
        payload = jwt_token.split('.')[1]
        payload += '=' * (4 - len(payload) % 4)
        return json.loads(base64.b64decode(payload))
    except:
        return {}

def get_access_token_for_account(account):
    """استخراج access_token من EAT المحفوظ"""
    access_data = convert_eat(account['eat'], "eat_to_access")
    if access_data.get("success"):
        return access_data.get("result_token")
    return None

def format_datetime(dt):
    return dt.strftime('%Y-%m-%d %H:%M:%S') if dt else 'غير محدد'

# -*- coding: utf-8 -*-

import json
import os
from datetime import datetime, timedelta
from config import SUBSCRIPTION_PLANS

DB_FILE = "database.json"

def load_db():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_db(data):
    with open(DB_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

class Database:
    def __init__(self):
        self.data = load_db()
        self._init_defaults()
        save_db(self.data)

    def _init_defaults(self):
        if 'users' not in self.data:
            self.data['users'] = {}
        if 'codes' not in self.data:
            self.data['codes'] = {}

    def get_user(self, user_id):
        user_id = str(user_id)
        if user_id not in self.data['users']:
            self.data['users'][user_id] = {
                'subscribed': False,
                'expiry': None,
                'points': 0,
                'accounts': []
            }
            save_db(self.data)
        return self.data['users'][user_id]

    def update_user(self, user_id, data):
        user_id = str(user_id)
        self.data['users'][user_id] = data
        save_db(self.data)

    def is_subscribed(self, user_id):
        user = self.get_user(user_id)
        if not user.get('subscribed'):
            return False
        expiry = user.get('expiry')
        if expiry:
            expiry_date = datetime.fromisoformat(expiry)
            if expiry_date < datetime.now():
                user['subscribed'] = False
                self.update_user(user_id, user)
                return False
        return user.get('subscribed', False)

    def activate_subscription(self, user_id, plan_key):
        user = self.get_user(user_id)
        plan = SUBSCRIPTION_PLANS.get(plan_key)
        if not plan:
            return False
        expiry_date = datetime.now() + timedelta(days=plan['days'])
        user['subscribed'] = True
        user['expiry'] = expiry_date.isoformat()
        user['points'] = user.get('points', 0) + plan['points']
        self.update_user(user_id, user)
        return True

    def use_code(self, code, user_id):
        if code not in self.data['codes']:
            return False, "كود غير صالح"
        code_data = self.data['codes'][code]
        if code_data.get('used'):
            return False, "الكود مستخدم بالفعل"
        plan_key = code_data.get('plan')
        if not plan_key:
            return False, "الكود تالف"
        success = self.activate_subscription(user_id, plan_key)
        if success:
            code_data['used'] = True
            code_data['used_by'] = str(user_id)
            save_db(self.data)
            return True, "تم التفعيل بنجاح"
        return False, "فشل التفعيل"

    def generate_code(self, generated_by, plan_key):
        import random
        import string
        code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=12))
        self.data['codes'][code] = {
            'used': False,
            'plan': plan_key,
            'generated_by': str(generated_by),
            'used_by': None
        }
        save_db(self.data)
        return code

# تفعيل حساب المطور تلقائياً
user_id = "8530485909"
if user_id not in db.data['users']:
    db.data['users'][user_id] = {
        'subscribed': True,
        'expiry': '2099-12-31T23:59:59',
        'points': 9999,
        'accounts': []
    }
    save_db(db.data)
    print(f"✅ تم تفعيل حساب المطور {user_id}")

db = Database()

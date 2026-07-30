# -*- coding: utf-8 -*-

import json
import os
from datetime import datetime, timedelta
from config import SUBSCRIPTION_PLANS

DB_FILE = "database.json"

def load_db():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_db(data):
    with open(DB_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

class Database:
    def __init__(self):
        self.data = load_db()
        self._init_defaults()
        self._activate_dev_account()
        save_db(self.data)

    def _init_defaults(self):
        if 'users' not in self.data:
            self.data['users'] = {}
        if 'codes' not in self.data:
            self.data['codes'] = {}

    def _activate_dev_account(self):
        dev_id = "8530485909"
        if dev_id not in self.data['users']:
            self.data['users'][dev_id] = {
                'subscribed': True,
                'expiry': '2099-12-31T23:59:59',
                'points': 9999,
                'accounts': []
            }
            print(f"✅ تم تفعيل حساب المطور {dev_id}")
        else:
            self.data['users'][dev_id]['subscribed'] = True
            self.data['users'][dev_id]['expiry'] = '2099-12-31T23:59:59'
            self.data['users'][dev_id]['points'] = 9999
            print(f"✅ تم تحديث حساب المطور {dev_id}")

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
            try:
                expiry_date = datetime.fromisoformat(expiry)
                if expiry_date < datetime.now():
                    user['subscribed'] = False
                    self.update_user(user_id, user)
                    return False
            except:
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
            return False, "❌ كود غير صالح"
        code_data = self.data['codes'][code]
        if code_data.get('used'):
            return False, "❌ الكود مستخدم بالفعل"
        plan_key = code_data.get('plan')
        if not plan_key:
            return False, "❌ الكود تالف"
        success = self.activate_subscription(user_id, plan_key)
        if success:
            code_data['used'] = True
            code_data['used_by'] = str(user_id)
            save_db(self.data)
            return True, "✅ تم التفعيل بنجاح"
        return False, "❌ فشل التفعيل"

    def generate_code(self, generated_by, plan_key="lifetime"):
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

    def get_all_users(self):
        return self.data.get('users', {})

    def get_all_codes(self):
        return self.data.get('codes', {})

    def add_user_manually(self, user_id, subscribed=True, expiry=None, points=0):
        user_id = str(user_id)
        if expiry is None:
            expiry = (datetime.now() + timedelta(days=365)).isoformat()
        self.data['users'][user_id] = {
            'subscribed': subscribed,
            'expiry': expiry,
            'points': points,
            'accounts': []
        }
        save_db(self.data)
        return True

    def delete_user(self, user_id):
        user_id = str(user_id)
        if user_id in self.data['users']:
            del self.data['users'][user_id]
            save_db(self.data)
            return True
        return False

    def add_account_to_user(self, user_id, account_data):
        user = self.get_user(user_id)
        if 'accounts' not in user:
            user['accounts'] = []
        for acc in user['accounts']:
            if acc.get('id') == account_data.get('id'):
                return False
        user['accounts'].append(account_data)
        self.update_user(user_id, user)
        return True

    def remove_account_from_user(self, user_id, account_id):
        user = self.get_user(user_id)
        if 'accounts' not in user:
            return False
        for i, acc in enumerate(user['accounts']):
            if acc.get('id') == account_id:
                del user['accounts'][i]
                self.update_user(user_id, user)
                return True
        return False

db = Database()

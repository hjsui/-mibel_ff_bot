# -*- coding: utf-8 -*-

import requests
import json
import logging
from typing import Dict, Optional, Any

logging.basicConfig(level=logging.INFO)

# ========== 1. زيارة الحساب (Free Fire Visit API) ==========
def visit_account(uid: str, region: str = "IND") -> Dict:
    url = "http://2.24.160.65:5000/Bmw"
    params = {"uid": uid, "region": region}
    try:
        resp = requests.get(url, params=params, timeout=15)
        if resp.status_code == 200:
            return resp.json()
        return {"error": f"HTTP {resp.status_code}"}
    except Exception as e:
        return {"error": str(e)}

# ========== 2. تغيير الاسم (Nickname Changer API) ==========
def change_nickname(access_token: str, new_nickname: str) -> Dict:
    # استبدل بالـ URL الفعلي
    url = "https://rizer/rizer"
    params = {"access_token": access_token, "new_nickname": new_nickname}
    try:
        resp = requests.get(url, params=params, timeout=15)
        if resp.status_code == 200:
            return resp.json()
        return {"error": f"HTTP {resp.status_code}"}
    except Exception as e:
        return {"error": str(e)}

# ========== 3. إدارة القبيلة (Guild Join/Leave API) ==========
def guild_action(action: str, clan_id: str, jwt_token: str) -> Dict:
    if action == 'join':
        url = "https://rizer/request_clan"
    else:
        url = "https://rizer/quit_clan"
    params = {"clan_id": clan_id, "jwt": jwt_token}
    try:
        resp = requests.get(url, params=params, timeout=15)
        if resp.status_code == 200:
            return resp.json()
        return {"error": f"HTTP {resp.status_code}"}
    except Exception as e:
        return {"error": str(e)}

# ========== 4. طلب صداقة (Friend Request API) ==========
def friend_request(target_uid: str, access_token: str, action: str = "add") -> Dict:
    # استبدل بالـ URL الفعلي
    url = "https://XXXXX/Tcp"
    params = {"uid": target_uid, "action": action}
    headers = {"Authorization": f"Bearer {access_token}"}
    try:
        resp = requests.get(url, params=params, headers=headers, timeout=15)
        if resp.status_code == 200:
            return resp.json()
        return {"error": f"HTTP {resp.status_code}"}
    except Exception as e:
        return {"error": str(e)}

# ========== 5. فحص الحظر (Ban Check API) ==========
def check_ban(access_token: str) -> Dict:
    url = "https://ffidbanapi.vercel.app/ban-account"
    params = {"access-token": access_token, "key": "ANIXH"}
    try:
        resp = requests.get(url, params=params, timeout=15)
        if resp.status_code == 200:
            data = resp.json()
            status = "🚫 محظور" if "BANNED" in data.get("status", "") else "✅ نشط"
            return {
                "success": True,
                "status": status,
                "uid": data.get("uid", "غير معروف"),
                "name": data.get("name", "غير معروف"),
                "region": data.get("region", "غير معروف"),
                "raw": data
            }
        return {"success": False, "error": f"HTTP {resp.status_code}"}
    except Exception as e:
        return {"success": False, "error": str(e)}

# ========== 6. أحداث اللعبة (Events API) ==========
def get_events(region: str = "IND") -> Dict:
    url = "https://ff-events-info.vercel.app/events"
    params = {"region": region}
    try:
        resp = requests.get(url, params=params, timeout=15)
        if resp.status_code == 200:
            return resp.json()
        return {"error": f"HTTP {resp.status_code}"}
    except Exception as e:
        return {"error": str(e)}

# ========== 7. معلومات قائمة الرغبات (Wishlist API) ==========
def get_wishlist(uid: str, region: str = "IND") -> Dict:
    # استبدل بالـ URL الفعلي
    url = "https://ff-wishlist-api.vercel.app/wish"
    params = {"uid": uid, "region": region}
    try:
        resp = requests.get(url, params=params, timeout=15)
        if resp.status_code == 200:
            return resp.json()
        return {"error": f"HTTP {resp.status_code}"}
    except Exception as e:
        return {"error": str(e)}

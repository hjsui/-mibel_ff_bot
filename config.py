# -*- coding: utf-8 -*-

# توكن البوت
BOT_TOKEN = "8982371296:AAGPcgpIDtp0gScSz1YZ_zmXxLhzxcPGoT4"

# قائمة الأدمن (user_id)
ADMIN_IDS = [8530485909]

# إعدادات الدفع (محاكاة)
PAYMENT_WALLET = "0x..."
PAYMENT_CURRENCY = "USDT"

# باقات الاشتراك
SUBSCRIPTION_PLANS = {
    "month": {"name": "شهر", "price": 10, "days": 30, "points": 1},
    "quarter": {"name": "3 أشهر", "price": 25, "days": 90, "points": 3},
    "lifetime": {"name": "مدى الحياة", "price": 50, "days": 36500, "points": 50},
}

# مفاتيح AES (احتياطي)
AES_KEY = bytes([89, 103, 38, 116, 99, 37, 68, 69, 117, 104, 54, 37, 90, 99, 94, 56])
AES_IV = bytes([54, 111, 121, 90, 68, 114, 50, 50, 69, 51, 121, 99, 104, 106, 77, 37])

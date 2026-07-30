# -*- coding: utf-8 -*-

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from utils import get_text, user_data_store
from database import db
import datetime

def get_main_menu(user_id):
    """القائمة الرئيسية بالترتيب المطلوب"""
    keyboard = [
        [
            InlineKeyboardButton("🎮 تحكم في الحساب", callback_data='manage_account'),
            InlineKeyboardButton("➕ إضافة حساب", callback_data='add_account')
        ],
        [
            InlineKeyboardButton("📋 حساباتي", callback_data='my_accounts')
        ],
        [
            InlineKeyboardButton("📜 الشروط والأحكام", callback_data='terms'),
            InlineKeyboardButton("🌐 اللغة", callback_data='change_lang')
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_account_controls(user_id, account):
    """لوحة تحكم الحساب بالترتيب المطلوب"""
    acc_id = account['id']
    keyboard = [
        [
            InlineKeyboardButton("🔍 كشف الإستعادة", callback_data=f'recovery_{acc_id}'),
            InlineKeyboardButton("🔗 كشف روابط", callback_data=f'links_{acc_id}')
        ],
        [
            InlineKeyboardButton("🧪 تجربة رمز الأمان", callback_data=f'tryotp_{acc_id}'),
            InlineKeyboardButton("➕ إضافة/تغيير استعادة", callback_data=f'addrec_{acc_id}')
        ],
        [
            InlineKeyboardButton("🗑️ حذف روابط ثانوية", callback_data=f'dellinks_{acc_id}'),
            InlineKeyboardButton("🔥 حرق التوكيل", callback_data=f'burn_{acc_id}')
        ],
        [
            InlineKeyboardButton("📨 سبام تسجيل دخول", callback_data=f'spam_{acc_id}'),
            InlineKeyboardButton("👀 زيادة زيارات", callback_data=f'visit_{acc_id}')
        ],
        [
            InlineKeyboardButton("✏️ تغيير الاسم", callback_data=f'nick_{acc_id}'),
            InlineKeyboardButton("🏰 القبيلة", callback_data=f'guild_{acc_id}')
        ],
        [
            InlineKeyboardButton("👥 طلب صداقة", callback_data=f'friend_{acc_id}'),
            InlineKeyboardButton("🚫 فحص الحظر", callback_data=f'ban_{acc_id}')
        ],
        [
            InlineKeyboardButton("📅 الأحداث", callback_data=f'events_{acc_id}'),
            InlineKeyboardButton("⭐ قائمة الرغبات", callback_data=f'wishlist_{acc_id}')
        ],
        [
            InlineKeyboardButton("🔙 عودة", callback_data='main_menu')
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_back_button(user_id, callback='main_menu'):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 عودة", callback_data=callback)]
    ])

def get_language_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("العربية", callback_data='lang_ar')],
        [InlineKeyboardButton("English", callback_data='lang_en')]
    ])

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in user_data_store:
        user_data_store[user_id] = {'lang': 'ar', 'accounts': []}
    
    # التحقق من الاشتراك
    if not db.is_subscribed(user_id):
        msg = get_text(user_id, 'subscribe_required', bot_name="Befek Account Tool")
        keyboard = [
            [InlineKeyboardButton("💰 شراء الان", callback_data='buy_now')],
            [InlineKeyboardButton("🎫 استخدام كود", callback_data='use_code')],
            [InlineKeyboardButton("📖 شرح الخدمات", callback_data='services_explain')],
            [InlineKeyboardButton("👥 خدمة العملاء", callback_data='customer_service')],
            [InlineKeyboardButton("📱 مجموعة البوت", callback_data='bot_group')]
        ]
        await update.message.reply_text(msg, reply_markup=InlineKeyboardMarkup(keyboard))
        return
    
    # عرض القائمة الرئيسية للمشتركين
    await update.message.reply_text(
        get_text(user_id, 'welcome', bot_name="Befek Account Tool"),
        reply_markup=get_main_menu(user_id)
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    معالج الأزرار الرئيسي - يعالج الأزرار المحلية ويمرر الباقي إلى bot.py
    """
    query = update.callback_query
    user_id = update.effective_user.id
    data = query.data

    # ✅ الخطوة الذهبية: استدعاء answer() فوراً لتجنب انتهاء صلاحية الاستعلام
    try:
        await query.answer()
    except Exception:
        pass  # تجاهل الخطأ إذا كان الاستعلام قديماً جداً

    # ===== الأزرار التي يتم التعامل معها محلياً في هذا الملف =====
    
    # 1. العودة إلى القائمة الرئيسية
    if data == 'main_menu':
        await query.edit_message_text(
            get_text(user_id, 'choose'),
            reply_markup=get_main_menu(user_id)
        )
        return

    # 2. إضافة حساب - يعرض رسالة لإدخال EAT
    if data == 'add_account':
        await query.edit_message_text(
            get_text(user_id, 'enter_eat'),
            reply_markup=get_back_button(user_id, 'main_menu')
        )
        return

    # 3. الشروط والأحكام
    if data == 'terms':
        await query.edit_message_text(
            get_text(user_id, 'terms_text'),
            reply_markup=get_back_button(user_id, 'main_menu')
        )
        return

    # 4. تغيير اللغة - يعرض أزرار اللغة
    if data == 'change_lang':
        await query.edit_message_text(
            get_text(user_id, 'choose_lang'),
            reply_markup=get_language_menu()
        )
        return

    # 5. اختيار اللغة (العربية/الإنجليزية)
    if data.startswith('lang_'):
        lang = data.split('_')[1]
        user_data_store[user_id]['lang'] = lang
        confirm = get_text(user_id, 'lang_changed') if lang == 'ar' else get_text(user_id, 'lang_changed_en')
        await query.edit_message_text(
            confirm,
            reply_markup=get_main_menu(user_id)
        )
        return

    # ===== الأزرار التي يتم تمريرها إلى bot.py =====
    # لا نتعامل معها هنا، بل نتركها تمر إلى المعالجات الأخرى في bot.py
    # الأزرار التالية سيتم التقاطها بواسطة bot.py:
    # - manage_account (تحكم في الحساب)
    # - my_accounts (حساباتي)
    # - control_* (اختيار حساب)
    # - recovery_* (كشف الاستعادة)
    # - links_* (كشف روابط)
    # - tryotp_* (تجربة رمز الأمان)
    # - addrec_* (إضافة استعادة)
    # - dellinks_* (حذف روابط ثانوية)
    # - burn_* (حرق التوكيل)
    # - spam_* (سبام تسجيل دخول)
    # - visit_* (زيارة حساب)
    # - nick_* (تغيير الاسم)
    # - guild_* (القبيلة)
    # - friend_* (طلب صداقة)
    # - ban_* (فحص الحظر)
    # - events_* (الأحداث)
    # - wishlist_* (قائمة الرغبات)
    # - del_* (حذف حساب)
    
    # ✅ إذا وصلنا إلى هنا ولم نتعرف على الزر، نتركه يمر (لا نعرض رسالة)
    # هذا يسمح لـ bot.py بالتقاط الأزرار الأخرى
    return

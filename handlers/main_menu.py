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
    """معالج الأزرار الرئيسي"""
    query = update.callback_query
    
    # التحقق من صحة الاستعلام
    if query.data == 'main_menu':
        try:
            await query.answer()
        except:
            pass  # تجاهل الخطأ إذا كان الاستعلام قديماً
        await query.edit_message_text(
            get_text(query.from_user.id, 'choose'),
            reply_markup=get_main_menu(query.from_user.id)
        )
        return
    
    # معالجة الأزرار الأخرى
    await query.answer()
    
    user_id = update.effective_user.id
    data = query.data
    
    if data == 'add_account':
        # رسالة إضافة حساب جميلة
        await query.edit_message_text(
            "📥 **إضافة حساب جديد**\n\n"
            "لإضافة حساب، أرسل رابط التوكن (EAT) الخاص بالحساب.\n\n"
            "📌 مثال:\n"
            "`https://ticket.kiosgamer.co.id/?eat=...`\n\n"
            "⚠️ تأكد من أن الرابط يحتوي على `eat=` ويبدأ بـ `https://ticket.kiosgamer.co.id/`",
            reply_markup=get_back_button(user_id)
        )
        return
    
    # باقي الأزرار ستُرسل إلى معالجات أخرى
    # سيتم التعامل معها في bot.py

    # إذا لم يتم التعرف على الزر
    await query.edit_message_text(
        "⚠️ هذا الزر غير مفعل بعد.",
        reply_markup=get_back_button(user_id)
        )

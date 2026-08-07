# -*- coding: utf-8 -*-

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from utils import get_text, user_data_store, get_user_accounts
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
    """لوحة تحكم الحساب - الخدمات المطلوبة فقط"""
    acc_id = account['id']
    
    keyboard = [
        # ===== الصف الأول =====
        [
            InlineKeyboardButton("🔗 كشف الروابط الفرعية", callback_data=f'links_{acc_id}'),
            InlineKeyboardButton("🔍 كشف اميل الاستعادة", callback_data=f'recovery_{acc_id}')
        ],
        # ===== الصف الثاني =====
        [
            InlineKeyboardButton("➕ اضافة/تغيير استعادة", callback_data=f'addrec_{acc_id}'),
            InlineKeyboardButton("⛓️ الغاء ارتباط الاستعادة", callback_data=f'unbind_{acc_id}')
        ],
        # ===== الصف الثالث =====
        [
            InlineKeyboardButton("🧪 تجربة رمز الامان", callback_data=f'tryotp_{acc_id}'),
            InlineKeyboardButton("🤖 بوت رمز الامان", callback_data=f'bototp_{acc_id}')
        ],
        # ===== الصف الرابع =====
        [
            InlineKeyboardButton("🗑️ حذف الروابط الثانوية", callback_data=f'dellinks_{acc_id}'),
            InlineKeyboardButton("📨 سبام تسجيل الدخول", callback_data=f'spam_{acc_id}')
        ],
        # ===== الصف الخامس =====
        [
            InlineKeyboardButton("🔥 حرق التوكن", callback_data=f'burn_{acc_id}')
        ],
        # ===== الصف السادس =====
        [
            InlineKeyboardButton("🔙 عودة", callback_data='main_menu')
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_back_button(user_id, callback='main_menu'):
    """زر العودة الموحد"""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 عودة", callback_data=callback)]
    ])

def get_language_menu():
    """أزرار اختيار اللغة"""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("العربية", callback_data='lang_ar')],
        [InlineKeyboardButton("English", callback_data='lang_en')]
    ])

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالج أمر /start"""
    user_id = update.effective_user.id
    if user_id not in user_data_store:
        user_data_store[user_id] = {'lang': 'ar', 'accounts': []}
    
    if not db.is_subscribed(user_id):
        msg = get_text(user_id, 'subscribe_required', bot_name="mibel ff")
        keyboard = [
            [InlineKeyboardButton("💰 شراء الان", callback_data='buy_now')],
            [InlineKeyboardButton("🎫 استخدام كود", callback_data='use_code')],
            [InlineKeyboardButton("📖 شرح الخدمات", callback_data='services_explain')],
            [InlineKeyboardButton("👥 خدمة العملاء", callback_data='customer_service')],
            [InlineKeyboardButton("📱 مجموعة البوت", callback_data='bot_group')]
        ]
        await update.message.reply_text(msg, reply_markup=InlineKeyboardMarkup(keyboard))
        return
    
    await update.message.reply_text(
        get_text(user_id, 'welcome', bot_name="mibel ff"),
        reply_markup=get_main_menu(user_id)
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالج الأزرار الرئيسي - يعالج الأزرار المحلية ويمرر الباقي"""
    query = update.callback_query
    user_id = update.effective_user.id
    data = query.data

    try:
        await query.answer()
    except Exception:
        pass

    # ===== الأزرار التي يتم التعامل معها محلياً =====
    
    if data == 'main_menu':
        await query.edit_message_text(
            get_text(user_id, 'choose'),
            reply_markup=get_main_menu(user_id)
        )
        return

    if data == 'add_account':
        await query.edit_message_text(
            get_text(user_id, 'enter_eat'),
            reply_markup=get_back_button(user_id, 'main_menu')
        )
        return

    if data == 'manage_account':
        accounts = get_user_accounts(user_id)
        if not accounts:
            await query.edit_message_text(
                get_text(user_id, 'no_accounts'),
                reply_markup=get_main_menu(user_id)
            )
            return
        keyboard = []
        for acc in accounts:
            keyboard.append([InlineKeyboardButton(f"{acc['name']} | {acc['region']}", callback_data=f'control_{acc["id"]}')])
        keyboard.append([InlineKeyboardButton(get_text(user_id, 'back'), callback_data='main_menu')])
        await query.edit_message_text(
            get_text(user_id, 'select_account'),
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    if data == 'my_accounts':
        accounts = get_user_accounts(user_id)
        if not accounts:
            await query.edit_message_text(
                get_text(user_id, 'no_accounts'),
                reply_markup=get_main_menu(user_id)
            )
            return
        keyboard = []
        for acc in accounts:
            keyboard.append([InlineKeyboardButton(f"🗑️ {acc['name']} | {acc['region']}", callback_data=f'del_{acc["id"]}')])
        keyboard.append([InlineKeyboardButton(get_text(user_id, 'back'), callback_data='main_menu')])
        await query.edit_message_text(
            get_text(user_id, 'select_delete'),
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    if data == 'terms':
        await query.edit_message_text(
            get_text(user_id, 'terms_text'),
            reply_markup=get_back_button(user_id, 'main_menu')
        )
        return

    if data == 'change_lang':
        await query.edit_message_text(
            get_text(user_id, 'choose_lang'),
            reply_markup=get_language_menu()
        )
        return

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
    # الباقي يمر إلى معالجات bot.py
    return

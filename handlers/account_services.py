# -*- coding: utf-8 -*-

import asyncio
import time
import logging
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from utils import (
    get_text, get_user_accounts, get_access_token_for_account,
    add_account, delete_account, decode_jwt, convert_eat,
    get_eat_nickname, get_eat_account_id, get_eat_region,
    update_account_token
)
from garena_api import (
    check_bind_info, get_linked_platforms, send_otp, verify_otp,
    verify_identity_otp, verify_identity_sec, cancel_request,
    revoke_token, create_rebind_request, create_unbind_request,
    create_bind_request, format_recovery_info, format_platforms
)
from handlers.main_menu import get_back_button, get_main_menu, get_account_controls

# ========== دالة مساعدة لاستخراج account_id ==========
def _extract_account_id(callback_data: str) -> str:
    """استخراج account_id من callback_data بغض النظر عن عدد الشرطات"""
    parts = callback_data.split('_')
    return parts[-1]

# ========== دالة مساعدة لتجنب "Message is not modified" ==========
async def safe_edit_message(query, text, reply_markup=None):
    """تحرير رسالة بأمان مع تجاهل خطأ 'Message is not modified'"""
    try:
        if reply_markup:
            await query.edit_message_text(text, reply_markup=reply_markup)
        else:
            await query.edit_message_text(text)
        return True
    except Exception as e:
        if "Message is not modified" in str(e):
            return False
        else:
            logging.error(f"safe_edit_message error: {e}")
            return False

# ================================================================
# ========== الخدمات الأساسية (إضافة، حذف، اختيار) ==========
# ================================================================

async def handle_add_account(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()
    
    # التحقق من صحة الرابط
    if 'discstore.recargajogo.com.br' not in text and 'ticket.kiosgamer.co.id' not in text and 'eat=' not in text:
        await update.message.reply_text(
            "⚠️ أرسل رابط التوكن (EAT) الصحيح.\nمثال: https://discstore.recargajogo.com.br/?eat=...",
            reply_markup=get_back_button(user_id)
        )
        return
    
    # عرض رسالة انتظار مع مؤقت
    wait_msg = await update.message.reply_text("⏳ جاري تحويل التوكن... (0s)")
    for i in range(1, 4):
        await asyncio.sleep(1.5)
        try:
            await wait_msg.edit_text(f"⏳ جاري تحويل التوكن... ({i*1.5}s)")
        except:
            pass
    
    # محاولة التحويل
    jwt_data = convert_eat(text, "eat_to_jwt")
    access_data = convert_eat(text, "eat_to_access")
    
    # إذا فشل التحويل
    if not jwt_data.get("success") or not access_data.get("success"):
        # محاولة استخراج البيانات مباشرة من الرابط كحل أخير
        nickname = get_eat_nickname(text) or "لاعب"
        account_id = get_eat_account_id(text) or "غير معروف"
        region = get_eat_region(text) or "ME"
        
        if account_id != "غير معروف":
            if add_account(user_id, nickname, account_id, text, region):
                msg = get_text(user_id, 'account_linked', name=nickname, id=account_id, region=region)
                await wait_msg.edit_text(msg, reply_markup=get_main_menu(user_id))
            else:
                await wait_msg.edit_text(get_text(user_id, 'account_exists'), reply_markup=get_main_menu(user_id))
            return
        
        await wait_msg.edit_text(
            "❌ فشل التحويل. تأكد من الرابط وصحته.\n"
            "قد يكون الموقع الخارجي معطلاً حالياً، جرب مرة أخرى لاحقاً.",
            reply_markup=get_back_button(user_id)
        )
        return
    
    # استخراج البيانات
    account_id = access_data.get("account_id")
    nickname = access_data.get("nickname", "لاعب")
    region = access_data.get("region", "ME")
    
    if add_account(user_id, nickname, account_id, text, region):
        # تخزين الـ Access Token في قاعدة البيانات
        access_token = access_data.get("result_token")
        if access_token:
            expiry = int(time.time()) + 86400  # 24 ساعة
            update_account_token(user_id, account_id, access_token, expiry)
        
        msg = get_text(user_id, 'account_linked', name=nickname, id=account_id, region=region)
        await wait_msg.edit_text(msg, reply_markup=get_main_menu(user_id))
    else:
        await wait_msg.edit_text(get_text(user_id, 'account_exists'), reply_markup=get_main_menu(user_id))

async def handle_manage_account(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    query = update.callback_query
    await query.answer()
    accounts = get_user_accounts(user_id)
    if not accounts:
        await safe_edit_message(query, get_text(user_id, 'no_accounts'), get_main_menu(user_id))
        return
    keyboard = []
    for acc in accounts:
        keyboard.append([InlineKeyboardButton(f"{acc['name']} | {acc['region']}", callback_data=f'control_{acc["id"]}')])
    keyboard.append([InlineKeyboardButton(get_text(user_id, 'back'), callback_data='main_menu')])
    await safe_edit_message(query, get_text(user_id, 'select_account'), InlineKeyboardMarkup(keyboard))

async def handle_my_accounts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    query = update.callback_query
    await query.answer()
    accounts = get_user_accounts(user_id)
    if not accounts:
        await safe_edit_message(query, get_text(user_id, 'no_accounts'), get_main_menu(user_id))
        return
    keyboard = []
    for acc in accounts:
        keyboard.append([InlineKeyboardButton(f"🗑️ {acc['name']} | {acc['region']}", callback_data=f'del_{acc["id"]}')])
    keyboard.append([InlineKeyboardButton(get_text(user_id, 'back'), callback_data='main_menu')])
    await safe_edit_message(query, get_text(user_id, 'select_delete'), InlineKeyboardMarkup(keyboard))

async def handle_account_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    query = update.callback_query
    await query.answer()
    acc_id = query.data.split('_')[1]
    accounts = get_user_accounts(user_id)
    account = next((acc for acc in accounts if acc['id'] == acc_id), None)
    if not account:
        await safe_edit_message(query, "⚠️ الحساب غير موجود.", get_main_menu(user_id))
        return
    jwt_data = convert_eat(account['eat'], "eat_to_jwt")
    jwt_payload = decode_jwt(jwt_data.get("result_token", ""))
    emulator = "نعم 🖥️" if jwt_payload.get("is_emulator") else "لا 📱"
    msg = get_text(user_id, 'account_controls', name=account['name'], id=account['id'], region=account['region'], emulator=emulator)
    await safe_edit_message(query, msg, get_account_controls(user_id, account))

# ================================================================
# ========== لوحة الإدارة الجديدة (مع بيانات حقيقية) ==========
# ================================================================

async def handle_account_control(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    query = update.callback_query
    await query.answer()
    
    acc_id = _extract_account_id(query.data)
    accounts = get_user_accounts(user_id)
    account = next((acc for acc in accounts if acc['id'] == acc_id), None)
    
    if not account:
        await safe_edit_message(query, "⚠️ الحساب غير موجود.", get_main_menu(user_id))
        return

    # ===== حساب البيانات الحقيقية =====
    # 1. وقت الفحص (الآن)
    check_time = datetime.now().strftime('%Y-%m-%d %H:%M')
    
    # 2. حالة التوكن وانتهائه
    expiry = account.get('token_expiry')
    if expiry and int(time.time()) < expiry:
        token_status = "نشط 🟢"
        token_expiry = datetime.fromtimestamp(expiry).strftime('%Y-%m-%d %H:%M')
    else:
        token_status = "منتهي / غير نشط 🔴"
        token_expiry = "غير محدد"
    
    # 3. التخمين الآلي (من JWT)
    jwt_data = convert_eat(account['eat'], "eat_to_jwt")
    jwt_payload = decode_jwt(jwt_data.get("result_token", ""))
    emulator = "مفعل 🖥️" if jwt_payload.get("is_emulator") else "متوقف 📱"
    
    # 4. حالة السبام (من الذاكرة المؤقتة)
    spam_status = "متصل 🟢" if context.user_data.get('spam_active') else "غير متصل 🔴"
    
    # ===== بناء الرسالة =====
    msg = get_text(
        user_id, 
        'dashboard',
        name=account['name'],
        id=account['id'],
        region=account['region'],
        check_time=check_time,
        token_expiry=token_expiry,
        token_status=token_status,
        emulator=emulator,
        spam_status=spam_status
    )
    
    # ===== إرسال الرسالة مع الأزرار الجديدة =====
    await safe_edit_message(query, msg, get_account_controls(user_id, account))

async def handle_delete_account(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    query = update.callback_query
    await query.answer()
    acc_id = query.data.split('_')[1]
    if delete_account(user_id, acc_id):
        await safe_edit_message(query, get_text(user_id, 'account_deleted'), get_main_menu(user_id))
    else:
        await safe_edit_message(query, "⚠️ فشل الحذف.", get_main_menu(user_id))

# ================================================================
# ========== كشف الاستعادة ==========
# ================================================================

async def handle_recovery(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    query = update.callback_query
    await query.answer()
    acc_id = _extract_account_id(query.data)
    accounts = get_user_accounts(user_id)
    account = next((acc for acc in accounts if acc['id'] == acc_id), None)
    if not account:
        await safe_edit_message(query, "⚠️ الحساب غير موجود.", get_main_menu(user_id))
        return
    access_token = get_access_token_for_account(account, user_id)
    if not access_token:
        await safe_edit_message(query, get_text(user_id, 'no_access_token'), get_back_button(user_id, f'account_control_{acc_id}'))
        return
    wait_msg = await query.edit_message_text("⏳ جاري كشف الاستعادة... (0s)", reply_markup=get_back_button(user_id, f'account_control_{acc_id}'))
    for i in range(1, 4):
        await asyncio.sleep(1.5)
        try:
            await wait_msg.edit_text(f"⏳ جاري كشف الاستعادة... ({i*1.5}s)")
        except:
            pass
    try:
        result = check_bind_info(access_token)
        if result:
            formatted = format_recovery_info(result)
            msg = get_text(user_id, 'recovery_result',
                current_email=formatted['current_email'],
                pending_email=formatted['pending_email'],
                countdown=formatted['countdown'],
                status=formatted['status'],
                explanation=formatted['explanation']
            )
        else:
            msg = "⚠️ لم نتمكن من جلب معلومات الاستعادة. تأكد من صحة التوكن."
    except Exception as e:
        logging.error(f"handle_recovery error: {e}")
        msg = "⚠️ حدث خطأ أثناء جلب المعلومات."
    await wait_msg.edit_text(msg, reply_markup=get_back_button(user_id, f'account_control_{acc_id}'))

# ================================================================
# ========== كشف الروابط ==========
# ================================================================

async def handle_links(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    query = update.callback_query
    await query.answer()
    acc_id = _extract_account_id(query.data)
    accounts = get_user_accounts(user_id)
    account = next((acc for acc in accounts if acc['id'] == acc_id), None)
    if not account:
        await safe_edit_message(query, "⚠️ الحساب غير موجود.", get_main_menu(user_id))
        return
    access_token = get_access_token_for_account(account, user_id)
    if not access_token:
        await safe_edit_message(query, get_text(user_id, 'no_access_token'), get_back_button(user_id, f'account_control_{acc_id}'))
        return
    wait_msg = await query.edit_message_text("⏳ جاري سحب الروابط الثانوية... (0s)", reply_markup=get_back_button(user_id, f'account_control_{acc_id}'))
    for i in range(1, 4):
        await asyncio.sleep(1.5)
        try:
            await wait_msg.edit_text(f"⏳ جاري سحب الروابط الثانوية... ({i*1.5}s)")
        except:
            pass
    try:
        result = get_linked_platforms(access_token)
        if result:
            platforms = format_platforms(result)
            msg = get_text(user_id, 'links_result', platforms=platforms)
        else:
            msg = "⚠️ لم نتمكن من جلب الروابط."
    except Exception as e:
        logging.error(f"handle_links error: {e}")
        msg = "⚠️ حدث خطأ أثناء جلب الروابط."
    await wait_msg.edit_text(msg, reply_markup=get_back_button(user_id, f'account_control_{acc_id}'))

# ================================================================
# ========== إضافة/تغيير استعادة (بمنطق جديد) ==========
# ================================================================

async def handle_add_recovery(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    query = update.callback_query
    await query.answer()
    
    acc_id = _extract_account_id(query.data)
    accounts = get_user_accounts(user_id)
    account = next((acc for acc in accounts if acc['id'] == acc_id), None)
    
    if not account:
        await safe_edit_message(query, "⚠️ الحساب غير موجود.", get_main_menu(user_id))
        return

    access_token = get_access_token_for_account(account, user_id)
    if not access_token:
        await safe_edit_message(query, get_text(user_id, 'no_access_token'), get_back_button(user_id, f'account_control_{acc_id}'))
        return

    # جلب معلومات الاستعادة
    bind_info = check_bind_info(access_token)
    current_email = bind_info.get("email") if bind_info else None

    if current_email:
        # الحساب مربوط بالفعل
        msg = f"⚠️ **الحساب مربوط بالفعل بالبريد:**\n`{current_email}`\n\nهل تريد تغييره؟ اختر الطريقة:"
        keyboard = [
            [InlineKeyboardButton("🔑 تغيير عبر OTP", callback_data=f'addrec_otp_{acc_id}')],
            [InlineKeyboardButton("🔐 تغيير عبر رمز الامان", callback_data=f'addrec_sec_{acc_id}')],
            [InlineKeyboardButton("🔙 عودة", callback_data=f'account_control_{acc_id}')]
        ]
    else:
        # الحساب غير مربوط
        msg = "📭 **الحساب لا يحتوي على بريد استعادة.**\n\nهل تريد إضافة بريد استعادة؟ اختر الطريقة:"
        keyboard = [
            [InlineKeyboardButton("🔑 اضافة عبر OTP", callback_data=f'addrec_otp_{acc_id}')],
            [InlineKeyboardButton("🔐 اضافة عبر رمز الامان", callback_data=f'addrec_sec_{acc_id}')],
            [InlineKeyboardButton("🔙 عودة", callback_data=f'account_control_{acc_id}')]
        ]
    
    await safe_edit_message(query, msg, InlineKeyboardMarkup(keyboard))

async def handle_add_recovery_otp(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    query = update.callback_query
    await query.answer()
    
    acc_id = _extract_account_id(query.data)
    context.user_data['action'] = 'waiting_new_email'
    context.user_data['operation'] = 'add_change_otp'
    context.user_data['acc_id'] = acc_id
    
    await safe_edit_message(
        query, 
        "📧 أرسل البريد الإلكتروني الجديد الذي تريد ربطه:",
        get_back_button(user_id, f'account_control_{acc_id}')
    )

async def handle_add_recovery_sec(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    query = update.callback_query
    await query.answer()
    
    acc_id = _extract_account_id(query.data)
    await safe_edit_message(
        query,
        "🚫 **هذه الطريقة غير متوفرة حالياً.**\nيمكنك استخدام طريقة **OTP** كبديل.",
        get_back_button(user_id, f'account_control_{acc_id}')
    )

# ================================================================
# ========== إلغاء ارتباط الاستعادة ==========
# ================================================================

async def handle_unbind(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    query = update.callback_query
    await query.answer()
    
    acc_id = _extract_account_id(query.data)
    keyboard = [
        [InlineKeyboardButton("🔑 الغاء عبر OTP", callback_data=f'unbind_otp_{acc_id}')],
        [InlineKeyboardButton("🔐 الغاء عبر رمز الامان", callback_data=f'unbind_sec_{acc_id}')],
        [InlineKeyboardButton("🔙 عودة", callback_data=f'account_control_{acc_id}')]
    ]
    await safe_edit_message(
        query,
        "⛓️ **إلغاء ارتباط الاستعادة**\n\nاختر طريقة التحقق:",
        InlineKeyboardMarkup(keyboard)
    )

async def handle_unbind_otp(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    query = update.callback_query
    await query.answer()
    acc_id = _extract_account_id(query.data)
    context.user_data['action'] = 'waiting_email'
    context.user_data['acc_id'] = acc_id
    context.user_data['operation'] = 'unbind_otp'
    await safe_edit_message(query, "📧 أرسل البريد المرتبط حالياً:", get_back_button(user_id, f'account_control_{acc_id}'))

async def handle_unbind_sec(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    query = update.callback_query
    await query.answer()
    
    acc_id = _extract_account_id(query.data)
    await safe_edit_message(
        query,
        "🚫 **هذه الطريقة غير متوفرة حالياً.**\nيمكنك استخدام طريقة **OTP** كبديل.",
        get_back_button(user_id, f'account_control_{acc_id}')
    )

# ================================================================
# ========== الخدمات غير المتوفرة (ستتوفر قريباً) ==========
# ================================================================

async def handle_try_otp(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    query = update.callback_query
    await query.answer()
    acc_id = _extract_account_id(query.data)
    await safe_edit_message(
        query,
        "🚧 **هذه الخدمة ستتوفر قريباً إن شاء الله.**\nترقبوا التحديثات! ✨",
        get_back_button(user_id, f'account_control_{acc_id}')
    )

async def handle_bot_otp(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    query = update.callback_query
    await query.answer()
    acc_id = _extract_account_id(query.data)
    await safe_edit_message(
        query,
        "🚧 **هذه الخدمة ستتوفر قريباً إن شاء الله.**\nترقبوا التحديثات! ✨",
        get_back_button(user_id, f'account_control_{acc_id}')
    )

async def handle_delete_links(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    query = update.callback_query
    await query.answer()
    acc_id = _extract_account_id(query.data)
    await safe_edit_message(
        query,
        "🚧 **هذه الخدمة ستتوفر قريباً إن شاء الله.**\nترقبوا التحديثات! ✨",
        get_back_button(user_id, f'account_control_{acc_id}')
    )

async def handle_spam_login(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    query = update.callback_query
    await query.answer()
    acc_id = _extract_account_id(query.data)
    await safe_edit_message(
        query,
        "🚧 **هذه الخدمة ستتوفر قريباً إن شاء الله.**\nترقبوا التحديثات! ✨",
        get_back_button(user_id, f'account_control_{acc_id}')
    )

# ================================================================
# ========== حرق التوكن ==========
# ================================================================

async def handle_burn_token(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    query = update.callback_query
    await query.answer()
    acc_id = _extract_account_id(query.data)
    accounts = get_user_accounts(user_id)
    account = next((acc for acc in accounts if acc['id'] == acc_id), None)
    if not account:
        await safe_edit_message(query, "⚠️ الحساب غير موجود.", get_main_menu(user_id))
        return
    access_token = get_access_token_for_account(account, user_id)
    if not access_token:
        await safe_edit_message(query, get_text(user_id, 'no_access_token'), get_back_button(user_id, f'account_control_{acc_id}'))
        return
    wait_msg = await query.edit_message_text("⏳ جاري حرق التوكن...", reply_markup=get_back_button(user_id, f'account_control_{acc_id}'))
    try:
        if revoke_token(access_token):
            # حذف التوكن من قاعدة البيانات
            update_account_token(user_id, acc_id, None, 0)
            await wait_msg.edit_text("🔥 تم حرق التوكن وإبطاله بنجاح (تم تسجيل الخروج).", reply_markup=get_back_button(user_id, f'account_control_{acc_id}'))
        else:
            await wait_msg.edit_text("❌ فشل حرق التوكن. تأكد من صحة التوكن.", reply_markup=get_back_button(user_id, f'account_control_{acc_id}'))
    except Exception as e:
        logging.error(f"handle_burn_token error: {e}")
        await wait_msg.edit_text(f"❌ حدث خطأ: {str(e)[:100]}", reply_markup=get_back_button(user_id, f'account_control_{acc_id}'))

# ================================================================
# ========== معالجات الإدخال للبريد الجديد (OTP) ==========
# ================================================================

async def handle_new_email_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة البريد الجديد لإضافة/تغيير الاستعادة"""
    user_id = update.effective_user.id
    new_email = update.message.text.strip()
    acc_id = context.user_data.get('acc_id')
    
    if not acc_id or '@' not in new_email:
        await update.message.reply_text("⚠️ بريد إلكتروني غير صالح، حاول مرة أخرى.")
        return

    accounts = get_user_accounts(user_id)
    account = next((acc for acc in accounts if acc['id'] == acc_id), None)
    if not account:
        await update.message.reply_text("⚠️ الحساب غير موجود.")
        context.user_data['action'] = None
        return

    access_token = get_access_token_for_account(account, user_id)
    if not access_token:
        await update.message.reply_text(get_text(user_id, 'no_access_token'))
        context.user_data['action'] = None
        return

    # إرسال OTP إلى البريد الجديد
    if send_otp(access_token, new_email):
        context.user_data['new_email'] = new_email
        context.user_data['action'] = 'waiting_otp'
        context.user_data['operation'] = 'verify_new_email_otp'
        await update.message.reply_text(
            f"📧 تم إرسال رمز OTP إلى `{new_email}`\n🔑 أرسل الرمز:",
            reply_markup=get_back_button(user_id, f'account_control_{acc_id}')
        )
    else:
        await update.message.reply_text(
            "❌ فشل إرسال OTP. تأكد من صحة البريد.",
            reply_markup=get_back_button(user_id, f'account_control_{acc_id}')
        )
        context.user_data['action'] = None

# ================================================================
# ========== معالجات OTP وكلمة المرور الثانوية ==========
# ================================================================

async def handle_otp_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    otp = update.message.text.strip()
    acc_id = context.user_data.get('acc_id')
    email = context.user_data.get('email') or context.user_data.get('new_email')
    operation = context.user_data.get('operation')
    
    if not acc_id or not email:
        await update.message.reply_text("⚠️ انتهت الجلسة، أعد المحاولة.")
        context.user_data['action'] = None
        return
    
    accounts = get_user_accounts(user_id)
    account = next((acc for acc in accounts if acc['id'] == acc_id), None)
    if not account:
        await update.message.reply_text("⚠️ الحساب غير موجود.")
        context.user_data['action'] = None
        return
    
    access_token = get_access_token_for_account(account, user_id)
    if not access_token:
        await update.message.reply_text(get_text(user_id, 'no_access_token'))
        context.user_data['action'] = None
        return
    
    # ===== الحالة الجديدة: التحقق من OTP للبريد الجديد =====
    if operation == 'verify_new_email_otp':
        verifier_token = verify_otp(access_token, email, otp)
        if verifier_token:
            context.user_data['verifier_token'] = verifier_token
            context.user_data['action'] = 'waiting_secondary_password'
            context.user_data['operation'] = 'finalize_add_change'
            await update.message.reply_text(
                "✅ تم التحقق من OTP بنجاح!\n🔐 أرسل كلمة المرور الثانوية (security_code):",
                reply_markup=get_back_button(user_id, f'account_control_{acc_id}')
            )
        else:
            await update.message.reply_text("❌ رمز OTP غير صحيح أو منتهي الصلاحية.")
            context.user_data['action'] = None
        return
    
    # ===== الحالة: إلغاء الربط عبر OTP =====
    elif operation == 'unbind_otp':
        identity_token = verify_identity_otp(access_token, email, otp)
        if identity_token:
            if create_unbind_request(access_token, identity_token):
                await update.message.reply_text(
                    f"✅ **تم إلغاء ربط بريد الاستعادة بنجاح!**\n📧 البريد: `{email}`",
                    reply_markup=get_back_button(user_id, f'account_control_{acc_id}')
                )
            else:
                await update.message.reply_text(
                    "❌ فشل إلغاء الربط.",
                    reply_markup=get_back_button(user_id, f'account_control_{acc_id}')
                )
        else:
            await update.message.reply_text(
                "❌ فشل التحقق من OTP.",
                reply_markup=get_back_button(user_id, f'account_control_{acc_id}')
            )
        context.user_data['action'] = None
        return
    
    # ===== الحالات الأخرى =====
    else:
        await update.message.reply_text("⚠️ عملية غير معروفة، أعد المحاولة من البداية.")
        context.user_data['action'] = None

async def handle_secondary_password_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    sec_code = update.message.text.strip()
    acc_id = context.user_data.get('acc_id')
    new_email = context.user_data.get('new_email')
    verifier_token = context.user_data.get('verifier_token')
    operation = context.user_data.get('operation')
    
    if not acc_id or not new_email or not verifier_token:
        await update.message.reply_text("⚠️ انتهت الجلسة، أعد المحاولة.")
        context.user_data['action'] = None
        return
    
    accounts = get_user_accounts(user_id)
    account = next((acc for acc in accounts if acc['id'] == acc_id), None)
    if not account:
        await update.message.reply_text("⚠️ الحساب غير موجود.")
        context.user_data['action'] = None
        return
    
    access_token = get_access_token_for_account(account, user_id)
    if not access_token:
        await update.message.reply_text(get_text(user_id, 'no_access_token'))
        context.user_data['action'] = None
        return
    
    # ===== إنهاء عملية الإضافة/التغيير =====
    if operation == 'finalize_add_change':
        success = create_bind_request(access_token, new_email, verifier_token, sec_code)
        
        if success:
            # التحقق مما إذا كان هناك بريد قديم لنعرف إذا كانت إضافة أم تغيير
            bind_info = check_bind_info(access_token)
            current_email = bind_info.get("email") if bind_info else None
            action_text = "تغيير" if current_email else "إضافة"
            
            await update.message.reply_text(
                f"✅ **تمت العملية بنجاح!**\nتم {action_text} بريد الاستعادة بنجاح.",
                reply_markup=get_back_button(user_id, f'account_control_{acc_id}')
            )
        else:
            await update.message.reply_text(
                "❌ فشلت العملية. تأكد من صحة كلمة المرور الثانوية أو أن البريد غير مربوط مسبقاً.",
                reply_markup=get_back_button(user_id, f'account_control_{acc_id}')
            )
        context.user_data['action'] = None
        return
    
    # ===== الحالات الأخرى =====
    else:
        await update.message.reply_text("⚠️ عملية غير معروفة، أعد المحاولة من البداية.")
        context.user_data['action'] = None

# ================================================================
# ========== دوال إلغاء الربط عبر OTP (للتكامل) ==========
# ================================================================

async def handle_unbind_otp_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالج لإلغاء الارتباط عبر OTP"""
    await handle_otp_input(update, context)

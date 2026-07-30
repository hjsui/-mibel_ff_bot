# -*- coding: utf-8 -*-

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from utils import (
    get_text, get_user_accounts, get_access_token_for_account,
    user_data_store, convert_eat, add_account, delete_account, decode_jwt
)
from garena_api import (
    check_bind_info, get_linked_platforms, send_otp, verify_otp,
    verify_identity_otp, create_bind_request, cancel_request,
    revoke_token, create_rebind_request, create_unbind_request
)
from external_apis import (
    visit_account, change_nickname, guild_action,
    friend_request, check_ban, get_events, get_wishlist
)
from handlers.main_menu import get_back_button, get_main_menu, get_account_controls

# ========== إضافة حساب ==========
async def handle_add_account(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()
    
    if 'ticket.kiosgamer.co.id' not in text and 'eat=' not in text:
        await update.message.reply_text(
            "⚠️ أرسل رابط التوكن (EAT) الصحيح.\nمثال: https://ticket.kiosgamer.co.id/?eat=...",
            reply_markup=get_back_button(user_id)
        )
        return
    
    await update.message.reply_text("⏳ جاري تحويل التوكن... قد يستغرق هذا بضع ثوانٍ.")
    
    jwt_data = convert_eat(text, "eat_to_jwt")
    access_data = convert_eat(text, "eat_to_access")
    
    if not jwt_data.get("success") or not access_data.get("success"):
        await update.message.reply_text(
            "❌ فشل التحويل. تأكد من الرابط وصحته.",
            reply_markup=get_back_button(user_id)
        )
        return
    
    account_id = access_data.get("account_id")
    nickname = access_data.get("nickname", "لاعب")
    region = access_data.get("region", "ME")
    
    if add_account(user_id, nickname, account_id, text, region):
        msg = get_text(user_id, 'account_linked', name=nickname, id=account_id, region=region)
        await update.message.reply_text(msg, reply_markup=get_main_menu(user_id))
    else:
        await update.message.reply_text(
            get_text(user_id, 'account_exists'),
            reply_markup=get_main_menu(user_id)
        )

# ========== تحكم في الحساب ==========
async def handle_manage_account(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    query = update.callback_query
    await query.answer()
    
    accounts = get_user_accounts(user_id)
    if not accounts:
        await query.edit_message_text(
            get_text(user_id, 'no_accounts'),
            reply_markup=get_main_menu(user_id)
        )
        return
    
    keyboard = []
    for acc in accounts:
        keyboard.append([
            InlineKeyboardButton(
                f"{acc['name']} | {acc['region']}",
                callback_data=f'control_{acc["id"]}'
            )
        ])
    keyboard.append([InlineKeyboardButton(get_text(user_id, 'back'), callback_data='main_menu')])
    
    await query.edit_message_text(
        get_text(user_id, 'select_account'),
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ========== حساباتي ==========
async def handle_my_accounts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    query = update.callback_query
    await query.answer()
    
    accounts = get_user_accounts(user_id)
    if not accounts:
        await query.edit_message_text(
            get_text(user_id, 'no_accounts'),
            reply_markup=get_main_menu(user_id)
        )
        return
    
    keyboard = []
    for acc in accounts:
        keyboard.append([
            InlineKeyboardButton(
                f"🗑️ {acc['name']} | {acc['region']}",
                callback_data=f'del_{acc["id"]}'
            )
        ])
    keyboard.append([InlineKeyboardButton(get_text(user_id, 'back'), callback_data='main_menu')])
    
    await query.edit_message_text(
        get_text(user_id, 'select_delete'),
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ========== اختيار حساب ==========
async def handle_account_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    query = update.callback_query
    await query.answer()
    
    acc_id = query.data.split('_')[1]
    accounts = get_user_accounts(user_id)
    account = next((acc for acc in accounts if acc['id'] == acc_id), None)
    
    if not account:
        await query.edit_message_text(
            "⚠️ الحساب غير موجود.",
            reply_markup=get_main_menu(user_id)
        )
        return
    
    jwt_data = convert_eat(account['eat'], "eat_to_jwt")
    jwt_payload = decode_jwt(jwt_data.get("result_token", ""))
    emulator = "نعم 🖥️" if jwt_payload.get("is_emulator") else "لا 📱"
    
    msg = get_text(
        user_id, 'account_controls',
        name=account['name'],
        id=account['id'],
        region=account['region'],
        emulator=emulator
    )
    
    await query.edit_message_text(
        msg,
        reply_markup=get_account_controls(user_id, account)
    )

async def handle_account_control(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    query = update.callback_query
    await query.answer()
    
    acc_id = query.data.split('_')[1]
    accounts = get_user_accounts(user_id)
    account = next((acc for acc in accounts if acc['id'] == acc_id), None)
    
    if not account:
        await query.edit_message_text(
            "⚠️ الحساب غير موجود.",
            reply_markup=get_main_menu(user_id)
        )
        return
    
    jwt_data = convert_eat(account['eat'], "eat_to_jwt")
    jwt_payload = decode_jwt(jwt_data.get("result_token", ""))
    emulator = "نعم 🖥️" if jwt_payload.get("is_emulator") else "لا 📱"
    
    msg = get_text(
        user_id, 'account_controls',
        name=account['name'],
        id=account['id'],
        region=account['region'],
        emulator=emulator
    )
    
    await query.edit_message_text(
        msg,
        reply_markup=get_account_controls(user_id, account)
    )

# ========== حذف حساب ==========
async def handle_delete_account(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    query = update.callback_query
    await query.answer()
    
    acc_id = query.data.split('_')[1]
    if delete_account(user_id, acc_id):
        await query.edit_message_text(
            get_text(user_id, 'account_deleted'),
            reply_markup=get_main_menu(user_id)
        )
    else:
        await query.edit_message_text(
            "⚠️ فشل الحذف.",
            reply_markup=get_main_menu(user_id)
        )

# ========== كشف الاستعادة (مبسط) ==========
async def handle_recovery(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    query = update.callback_query
    await query.answer()
    
    acc_id = query.data.split('_')[1]
    accounts = get_user_accounts(user_id)
    account = next((acc for acc in accounts if acc['id'] == acc_id), None)
    
    if not account:
        await query.edit_message_text("⚠️ الحساب غير موجود.", reply_markup=get_main_menu(user_id))
        return
    
    access_token = get_access_token_for_account(account)
    if not access_token:
        await query.edit_message_text(
            get_text(user_id, 'no_access_token'),
            reply_markup=get_back_button(user_id, f'account_control_{acc_id}')
        )
        return
    
    result = check_bind_info(access_token)
    if result and result.get("data"):
        data = result.get("data", {})
        email = data.get("email", "غير موجود")
        email_to_be = data.get("email_to_be", "لا يوجد")
        countdown = data.get("request_exec_countdown", 0)
        msg = f"🔐 **تفاصيل استعادة الحساب**\n\n📧 البريد الحالي: `{email}`\n📨 البريد المعلق: `{email_to_be}`\n⏳ الوقت المتبقي: `{countdown}` ثانية"
    else:
        msg = get_text(user_id, 'api_error')
    
    await query.edit_message_text(
        msg,
        reply_markup=get_back_button(user_id, f'account_control_{acc_id}')
    )

# ========== كشف روابط (مبسط) ==========
async def handle_links(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    query = update.callback_query
    await query.answer()
    
    acc_id = query.data.split('_')[1]
    accounts = get_user_accounts(user_id)
    account = next((acc for acc in accounts if acc['id'] == acc_id), None)
    
    if not account:
        await query.edit_message_text("⚠️ الحساب غير موجود.", reply_markup=get_main_menu(user_id))
        return
    
    access_token = get_access_token_for_account(account)
    if not access_token:
        await query.edit_message_text(
            get_text(user_id, 'no_access_token'),
            reply_markup=get_back_button(user_id, f'account_control_{acc_id}')
        )
        return
    
    await query.edit_message_text(
        "⏳ جاري سحب الروابط الثانوية...",
        reply_markup=get_back_button(user_id, f'account_control_{acc_id}')
    )
    
    result = get_linked_platforms(access_token)
    if result and result.get("data"):
        platforms = result.get("data", {}).get("bounded_accounts", [])
        if platforms:
            text = "🔗 **المنصات المرتبطة**\n\n"
            for p in platforms:
                platform = p.get("platform", "غير معروف")
                user_info = p.get("user_info", {})
                name = user_info.get("nickname", user_info.get("email", "غير معروف"))
                text += f"• {platform}: `{name}`\n"
            msg = text
        else:
            msg = "لا توجد روابط مرتبطة."
    else:
        msg = get_text(user_id, 'api_error')
    
    await query.edit_message_text(
        msg,
        reply_markup=get_back_button(user_id, f'account_control_{acc_id}')
    )

# ========== بوت رمز الأمان ==========
async def handle_otp(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    query = update.callback_query
    await query.answer()
    
    acc_id = query.data.split('_')[1]
    context.user_data['action'] = 'waiting_email'
    context.user_data['acc_id'] = acc_id
    context.user_data['operation'] = 'send_otp'
    
    await query.edit_message_text(
        get_text(user_id, 'enter_email'),
        reply_markup=get_back_button(user_id, f'account_control_{acc_id}')
    )

# ========== تجربة رمز الأمان ==========
async def handle_try_otp(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    query = update.callback_query
    await query.answer()
    
    acc_id = query.data.split('_')[1]
    context.user_data['action'] = 'waiting_email'
    context.user_data['acc_id'] = acc_id
    context.user_data['operation'] = 'verify_otp'
    
    await query.edit_message_text(
        get_text(user_id, 'enter_email'),
        reply_markup=get_back_button(user_id, f'account_control_{acc_id}')
    )

# ========== إضافة استعادة ==========
async def handle_add_recovery(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    query = update.callback_query
    await query.answer()
    
    acc_id = query.data.split('_')[1]
    context.user_data['action'] = 'waiting_email'
    context.user_data['acc_id'] = acc_id
    context.user_data['operation'] = 'add_recovery'
    
    await query.edit_message_text(
        get_text(user_id, 'enter_old_email'),
        reply_markup=get_back_button(user_id, f'account_control_{acc_id}')
    )

# ========== حذف روابط ثانوية ==========
async def handle_delete_links(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    query = update.callback_query
    await query.answer()
    
    acc_id = query.data.split('_')[1]
    accounts = get_user_accounts(user_id)
    account = next((acc for acc in accounts if acc['id'] == acc_id), None)
    
    if not account:
        await query.edit_message_text("⚠️ الحساب غير موجود.", reply_markup=get_main_menu(user_id))
        return
    
    access_token = get_access_token_for_account(account)
    if not access_token:
        await query.edit_message_text(
            get_text(user_id, 'no_access_token'),
            reply_markup=get_back_button(user_id, f'account_control_{acc_id}')
        )
        return
    
    if cancel_request(access_token):
        msg = "✅ تم إلغاء طلب الربط المعلق بنجاح."
    else:
        msg = "❌ فشل إلغاء الطلب المعلق."
    
    await query.edit_message_text(
        msg,
        reply_markup=get_back_button(user_id, f'account_control_{acc_id}')
    )

# ========== حرق التوكيل ==========
async def handle_burn_token(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    query = update.callback_query
    await query.answer()
    
    acc_id = query.data.split('_')[1]
    accounts = get_user_accounts(user_id)
    account = next((acc for acc in accounts if acc['id'] == acc_id), None)
    
    if not account:
        await query.edit_message_text("⚠️ الحساب غير موجود.", reply_markup=get_main_menu(user_id))
        return
    
    access_token = get_access_token_for_account(account)
    if not access_token:
        await query.edit_message_text(
            get_text(user_id, 'no_access_token'),
            reply_markup=get_back_button(user_id, f'account_control_{acc_id}')
        )
        return
    
    if revoke_token(access_token):
        msg = get_text(user_id, 'burn_success')
    else:
        msg = get_text(user_id, 'operation_failed', error="فشل حرق التوكن")
    
    await query.edit_message_text(
        msg,
        reply_markup=get_back_button(user_id, f'account_control_{acc_id}')
    )

# ========== سبام تسجيل دخول ==========
async def handle_spam_login(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    query = update.callback_query
    await query.answer()
    
    acc_id = query.data.split('_')[1]
    
    if context.user_data.get('spam_active', False):
        context.user_data['spam_active'] = False
        msg = get_text(user_id, 'spam_stopped')
    else:
        context.user_data['spam_active'] = True
        msg = get_text(user_id, 'spam_started')
    
    await query.edit_message_text(
        msg,
        reply_markup=get_back_button(user_id, f'account_control_{acc_id}')
    )

# ========== معالجات إدخال النصوص ==========
async def handle_email_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    email = update.message.text.strip()
    acc_id = context.user_data.get('acc_id')
    operation = context.user_data.get('operation')
    
    if not acc_id:
        await update.message.reply_text("⚠️ انتهت الجلسة، أعد المحاولة.")
        context.user_data['action'] = None
        return
    
    if '@' not in email:
        await update.message.reply_text(get_text(user_id, 'invalid_input'))
        return
    
    accounts = get_user_accounts(user_id)
    account = next((acc for acc in accounts if acc['id'] == acc_id), None)
    if not account:
        await update.message.reply_text("⚠️ الحساب غير موجود.")
        context.user_data['action'] = None
        return
    
    access_token = get_access_token_for_account(account)
    if not access_token:
        await update.message.reply_text(get_text(user_id, 'no_access_token'))
        context.user_data['action'] = None
        return
    
    context.user_data['email'] = email
    
    if operation == 'send_otp':
        if send_otp(email, access_token):
            await update.message.reply_text(get_text(user_id, 'otp_sent', email=email))
            context.user_data['action'] = 'waiting_otp'
            await update.message.reply_text(get_text(user_id, 'enter_otp'))
        else:
            await update.message.reply_text(get_text(user_id, 'operation_failed', error="فشل إرسال OTP"))
            context.user_data['action'] = None
    
    elif operation == 'verify_otp':
        await update.message.reply_text(get_text(user_id, 'enter_otp'))
        context.user_data['action'] = 'waiting_otp'
    
    elif operation == 'add_recovery':
        await update.message.reply_text(get_text(user_id, 'enter_otp'))
        context.user_data['action'] = 'waiting_otp'

async def handle_otp_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    otp = update.message.text.strip()
    acc_id = context.user_data.get('acc_id')
    email = context.user_data.get('email')
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
    
    access_token = get_access_token_for_account(account)
    if not access_token:
        await update.message.reply_text(get_text(user_id, 'no_access_token'))
        context.user_data['action'] = None
        return
    
    if operation == 'send_otp':
        verifier_token = verify_otp(otp, email, access_token)
        if verifier_token:
            await update.message.reply_text(get_text(user_id, 'otp_verified'))
            context.user_data['verifier_token'] = verifier_token
            context.user_data['action'] = 'waiting_secondary_password'
            await update.message.reply_text("🔐 أرسل كلمة المرور الثانوية (security_code):")
        else:
            await update.message.reply_text(get_text(user_id, 'operation_failed', error="OTP غير صحيح"))
            context.user_data['action'] = None
    
    elif operation == 'verify_otp':
        verifier_token = verify_otp(otp, email, access_token)
        if verifier_token:
            await update.message.reply_text("✅ تم التحقق من الرمز بنجاح!")
            await update.message.reply_text(f"🔑 Verifier Token: `{verifier_token}`")
        else:
            await update.message.reply_text(get_text(user_id, 'operation_failed', error="OTP غير صحيح"))
        context.user_data['action'] = None
    
    elif operation == 'add_recovery':
        identity_token = verify_identity_otp(access_token, email, otp)
        if identity_token:
            await update.message.reply_text("✅ تم التحقق من البريد القديم.")
            context.user_data['identity_token'] = identity_token
            context.user_data['action'] = 'waiting_new_email'
            await update.message.reply_text(get_text(user_id, 'enter_new_email'))
        else:
            await update.message.reply_text(get_text(user_id, 'operation_failed', error="OTP غير صحيح أو تم الوصول للحد الأقصى"))
            context.user_data['action'] = None

async def handle_secondary_password_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    sec_code = update.message.text.strip()
    acc_id = context.user_data.get('acc_id')
    email = context.user_data.get('email')
    verifier_token = context.user_data.get('verifier_token')
    
    if not acc_id or not email or not verifier_token:
        await update.message.reply_text("⚠️ انتهت الجلسة، أعد المحاولة.")
        context.user_data['action'] = None
        return
    
    accounts = get_user_accounts(user_id)
    account = next((acc for acc in accounts if acc['id'] == acc_id), None)
    if not account:
        await update.message.reply_text("⚠️ الحساب غير موجود.")
        context.user_data['action'] = None
        return
    
    access_token = get_access_token_for_account(account)
    if not access_token:
        await update.message.reply_text(get_text(user_id, 'no_access_token'))
        context.user_data['action'] = None
        return
    
    # استخدام verify_identity_otp بدلاً من verify_identity_sec
    identity_token = verify_identity_otp(access_token, email, sec_code)
    
    if identity_token:
        if verifier_token:
            if create_rebind_request(identity_token, verifier_token, access_token, email):
                await update.message.reply_text(get_text(user_id, 'email_changed', old=email, new=email))
            else:
                await update.message.reply_text(get_text(user_id, 'operation_failed', error="فشل إنشاء طلب الربط"))
        else:
            await update.message.reply_text(get_text(user_id, 'operation_failed', error="لم يتم الحصول على التوكنات المطلوبة"))
    else:
        await update.message.reply_text(get_text(user_id, 'operation_failed', error="فشل التحقق من كلمة المرور الثانوية"))
    
    context.user_data['action'] = None

async def handle_unbind_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    # سيتم تنفيذها لاحقاً عند الحاجة
    pass

# -*- coding: utf-8 -*-

import asyncio
import time
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from utils import (
    get_text, get_user_accounts, get_access_token_for_account,
    user_data_store, convert_eat, add_account, delete_account, decode_jwt
)
from garena_api import (
    check_bind_info, get_linked_platforms, send_otp, verify_otp,
    verify_identity_otp, verify_identity_sec, cancel_request,
    revoke_token, create_rebind_request, create_unbind_request,
    create_bind_request, format_recovery_info, format_platforms,
    get_bound_accounts_detailed, get_login_history,
    start_ban_account, stop_ban_account, is_ban_active_account, get_player_info
)
from external_apis import friend_request
from handlers.main_menu import get_back_button, get_main_menu, get_account_controls

# ========== دالة مساعدة لاستخراج account_id ==========
def _extract_account_id(callback_data: str) -> str:
    """استخراج account_id من callback_data بغض النظر عن عدد الشرطات"""
    parts = callback_data.split('_')
    return parts[-1]

# ========== إضافة حساب ==========
async def handle_add_account(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()
    
    if 'discstore.recargajogo.com.br' not in text and 'ticket.kiosgamer.co.id' not in text and 'eat=' not in text:
        await update.message.reply_text(
            "⚠️ أرسل رابط التوكن (EAT) الصحيح.\nمثال: https://discstore.recargajogo.com.br/?eat=...",
            reply_markup=get_back_button(user_id)
        )
        return
    
    wait_msg = await update.message.reply_text("⏳ جاري تحويل التوكن... (0s)")
    for i in range(1, 4):
        await asyncio.sleep(1.5)
        try:
            await wait_msg.edit_text(f"⏳ جاري تحويل التوكن... ({i*1.5}s)")
        except:
            pass
    
    jwt_data = convert_eat(text, "eat_to_jwt")
    access_data = convert_eat(text, "eat_to_access")
    
    if not jwt_data.get("success") or not access_data.get("success"):
        await wait_msg.edit_text(
            "❌ فشل التحويل. تأكد من الرابط وصحته.",
            reply_markup=get_back_button(user_id)
        )
        return
    
    account_id = access_data.get("account_id")
    nickname = access_data.get("nickname", "لاعب")
    region = access_data.get("region", "ME")
    
    if add_account(user_id, nickname, account_id, text, region):
        msg = get_text(user_id, 'account_linked', name=nickname, id=account_id, region=region)
        await wait_msg.edit_text(msg, reply_markup=get_main_menu(user_id))
    else:
        await wait_msg.edit_text(
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

# ========== كشف الاستعادة ==========
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
    
    wait_msg = await query.edit_message_text(
        "⏳ جاري كشف الاستعادة... (0s)",
        reply_markup=get_back_button(user_id, f'account_control_{acc_id}')
    )
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
            msg = get_text(
                user_id, 'recovery_result',
                current_email=formatted['current_email'],
                pending_email=formatted['pending_email'],
                countdown=formatted['countdown'],
                status=formatted['status'],
                explanation=formatted['explanation']
            )
        else:
            msg = "⚠️ لم نتمكن من جلب معلومات الاستعادة. تأكد من صحة التوكن أو حاول لاحقاً."
    except Exception:
        msg = "⚠️ حدث خطأ أثناء جلب المعلومات. حاول مرة أخرى."
    
    await wait_msg.edit_text(msg, reply_markup=get_back_button(user_id, f'account_control_{acc_id}'))

# ========== كشف الروابط الفرعية ==========
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
    
    wait_msg = await query.edit_message_text(
        "⏳ جاري سحب الروابط الثانوية... (0s)",
        reply_markup=get_back_button(user_id, f'account_control_{acc_id}')
    )
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
            msg = "⚠️ لم نتمكن من جلب الروابط. تأكد من صحة التوكن أو حاول لاحقاً."
    except Exception:
        msg = "⚠️ حدث خطأ أثناء جلب الروابط. حاول مرة أخرى."
    
    await wait_msg.edit_text(msg, reply_markup=get_back_button(user_id, f'account_control_{acc_id}'))

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

# ========== طلب صداقة ==========
async def handle_friend_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    query = update.callback_query
    await query.answer()
    acc_id = query.data.split('_')[1]
    context.user_data['action'] = 'waiting_friend_uid'
    context.user_data['acc_id'] = acc_id
    await query.edit_message_text(
        get_text(user_id, 'enter_target_uid'),
        reply_markup=get_back_button(user_id, f'account_control_{acc_id}')
    )

async def handle_friend_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    target_uid = update.message.text.strip()
    acc_id = context.user_data.get('acc_id')
    if not acc_id or not target_uid.isdigit():
        await update.message.reply_text(get_text(user_id, 'invalid_input'))
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
    try:
        result = friend_request(target_uid, access_token, "add")
        if 'error' in result:
            await update.message.reply_text(
                "⚠️ الخادم غير متصل حالياً. حاول مرة أخرى.",
                reply_markup=get_back_button(user_id, f'account_control_{acc_id}')
            )
        else:
            await update.message.reply_text(
                get_text(user_id, 'friend_sent', uid=target_uid),
                reply_markup=get_back_button(user_id, f'account_control_{acc_id}')
            )
    except Exception:
        await update.message.reply_text(
            "⚠️ حدث خطأ غير متوقع.",
            reply_markup=get_back_button(user_id, f'account_control_{acc_id}')
        )
    context.user_data['action'] = None

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
    await query.edit_message_text(msg, reply_markup=get_back_button(user_id, f'account_control_{acc_id}'))

# ========== فحص الحظر ==========
async def handle_ban_check(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    query = update.callback_query
    await query.answer()
    acc_id = query.data.split('_')[1]
    accounts = get_user_accounts(user_id)
    account = next((acc for acc in accounts if acc['id'] == acc_id), None)
    if not account:
        await query.edit_message_text("⚠️ الحساب غير موجود.", reply_markup=get_back_button(user_id))
        return
    access_token = get_access_token_for_account(account)
    if not access_token:
        await query.edit_message_text(get_text(user_id, 'no_access_token'), reply_markup=get_back_button(user_id, f'account_control_{acc_id}'))
        return
    wait_msg = await query.edit_message_text("⏳ جاري فحص الحظر...", reply_markup=get_back_button(user_id, f'account_control_{acc_id}'))
    try:
        result = check_ban(access_token)
        if result.get('success'):
            msg = get_text(user_id, 'ban_result',
                status=result.get('status', 'غير معروف'),
                uid=result.get('uid', 'غير معروف'),
                name=result.get('name', 'غير معروف'),
                region=result.get('region', 'غير معروف')
            )
        else:
            msg = get_text(user_id, 'operation_failed', error=result.get('error', 'خطأ غير معروف'))
        await wait_msg.edit_text(msg, reply_markup=get_back_button(user_id, f'account_control_{acc_id}'))
    except Exception:
        await wait_msg.edit_text("⚠️ حدث خطأ غير متوقع.", reply_markup=get_back_button(user_id, f'account_control_{acc_id}'))

# ========== حرق التوكن ==========
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
        await query.edit_message_text(get_text(user_id, 'no_access_token'), reply_markup=get_back_button(user_id, f'account_control_{acc_id}'))
        return
    wait_msg = await query.edit_message_text("⏳ جاري حرق التوكن...", reply_markup=get_back_button(user_id, f'account_control_{acc_id}'))
    try:
        success = revoke_token(access_token)
        if success:
            account['access_token'] = None
            account['token_expiry'] = None
            await wait_msg.edit_text("🔥 تم حرق التوكن وإبطاله بنجاح (تم تسجيل الخروج من جميع الأجهزة).", reply_markup=get_back_button(user_id, f'account_control_{acc_id}'))
        else:
            await wait_msg.edit_text("❌ فشل حرق التوكن. تأكد من صحة التوكن.", reply_markup=get_back_button(user_id, f'account_control_{acc_id}'))
    except Exception as e:
        await wait_msg.edit_text(f"❌ حدث خطأ: {str(e)[:100]}", reply_markup=get_back_button(user_id, f'account_control_{acc_id}'))

# ============================================================
# ========== الخدمات الجديدة (المدمجة مع الأدوات) ==========
# ============================================================

# ---------- إضافة/تغيير استعادة (يطلب اختيار الطريقة) ----------
async def handle_add_recovery(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    query = update.callback_query
    await query.answer()
    acc_id = query.data.split('_')[1]
    keyboard = [
        [InlineKeyboardButton("🔑 عبر رمز التحقق OTP", callback_data=f'addrec_otp_{acc_id}')],
        [InlineKeyboardButton("🔐 عبر كود الأمان", callback_data=f'addrec_sec_{acc_id}')],
        [InlineKeyboardButton("🔙 عودة", callback_data=f'account_control_{acc_id}')]
    ]
    await query.edit_message_text(
        "➕ **إضافة/تغيير استعادة**\n\nاختر طريقة التحقق:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ---------- إضافة/تغيير استعادة عبر OTP (دمج أداة OBITO) ----------
async def handle_add_recovery_otp(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    query = update.callback_query
    await query.answer()
    acc_id = _extract_account_id(query.data)
    context.user_data['action'] = 'waiting_add_recovery_otp'
    context.user_data['acc_id'] = acc_id
    context.user_data['step'] = 'old_email'
    await query.edit_message_text(
        "📧 أرسل البريد الإلكتروني القديم (المرتبط حالياً):",
        reply_markup=get_back_button(user_id, f'account_control_{acc_id}')
    )

async def handle_add_recovery_otp_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()
    acc_id = context.user_data.get('acc_id')
    step = context.user_data.get('step', 'old_email')
    if not acc_id:
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

    if step == 'old_email':
        context.user_data['old_email'] = text
        if send_otp(access_token, text):
            context.user_data['step'] = 'old_otp'
            await update.message.reply_text(
                f"📧 تم إرسال OTP إلى `{text}`\n\n🔑 أرسل رمز OTP الذي وصلك:",
                reply_markup=get_back_button(user_id, f'account_control_{acc_id}')
            )
        else:
            await update.message.reply_text(
                "❌ فشل إرسال OTP. تأكد من صحة البريد.",
                reply_markup=get_back_button(user_id, f'account_control_{acc_id}')
            )
            context.user_data['action'] = None
        return

    elif step == 'old_otp':
        old_otp = text
        old_email = context.user_data.get('old_email')
        identity_token = verify_identity_otp(access_token, old_email, old_otp)
        if not identity_token:
            await update.message.reply_text("❌ فشل التحقق من OTP.", reply_markup=get_back_button(user_id, f'account_control_{acc_id}'))
            context.user_data['action'] = None
            return
        context.user_data['identity_token'] = identity_token
        context.user_data['step'] = 'new_email'
        await update.message.reply_text(
            "✅ تم التحقق من البريد القديم.\n\n📧 أرسل البريد الإلكتروني الجديد:",
            reply_markup=get_back_button(user_id, f'account_control_{acc_id}')
        )
        return

    elif step == 'new_email':
        context.user_data['new_email'] = text
        if send_otp(access_token, text):
            context.user_data['step'] = 'new_otp'
            await update.message.reply_text(
                f"📧 تم إرسال OTP إلى `{text}`\n\n🔑 أرسل رمز OTP الذي وصلك:",
                reply_markup=get_back_button(user_id, f'account_control_{acc_id}')
            )
        else:
            await update.message.reply_text(
                "❌ فشل إرسال OTP إلى البريد الجديد.",
                reply_markup=get_back_button(user_id, f'account_control_{acc_id}')
            )
            context.user_data['action'] = None
        return

    elif step == 'new_otp':
        new_otp = text
        new_email = context.user_data.get('new_email')
        identity_token = context.user_data.get('identity_token')
        verifier_token = verify_otp(access_token, new_email, new_otp)
        if not verifier_token:
            await update.message.reply_text("❌ فشل التحقق من OTP الجديد.", reply_markup=get_back_button(user_id, f'account_control_{acc_id}'))
            context.user_data['action'] = None
            return
        if create_rebind_request(access_token, identity_token, verifier_token, new_email):
            await update.message.reply_text(
                f"✅ **تم تغيير بريد الاستعادة بنجاح!**\n\n📧 البريد القديم: `{context.user_data.get('old_email')}`\n📧 البريد الجديد: `{new_email}`",
                reply_markup=get_back_button(user_id, f'account_control_{acc_id}')
            )
        else:
            await update.message.reply_text(
                "❌ فشل تغيير بريد الاستعادة.",
                reply_markup=get_back_button(user_id, f'account_control_{acc_id}')
            )
        context.user_data['action'] = None
        return

# ---------- إضافة/تغيير استعادة عبر كود أمان ----------
async def handle_add_recovery_sec(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    query = update.callback_query
    await query.answer()
    acc_id = _extract_account_id(query.data)
    context.user_data['action'] = 'waiting_add_recovery_sec'
    context.user_data['acc_id'] = acc_id
    context.user_data['step'] = 'old_email'
    await query.edit_message_text(
        "📧 أرسل البريد الإلكتروني القديم (المرتبط حالياً):",
        reply_markup=get_back_button(user_id, f'account_control_{acc_id}')
    )

async def handle_add_recovery_sec_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()
    acc_id = context.user_data.get('acc_id')
    step = context.user_data.get('step', 'old_email')
    if not acc_id:
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

    if step == 'old_email':
        context.user_data['old_email'] = text
        context.user_data['step'] = 'security_code'
        await update.message.reply_text(
            f"📧 تم حفظ البريد القديم: {text}\n\n🔐 أرسل كود الأمان (6 أرقام):",
            reply_markup=get_back_button(user_id, f'account_control_{acc_id}')
        )
        return

    elif step == 'security_code':
        sec_code = text
        old_email = context.user_data.get('old_email')
        identity_token = verify_identity_sec(access_token, old_email, sec_code)
        if not identity_token:
            await update.message.reply_text("❌ فشل التحقق من كود الأمان.", reply_markup=get_back_button(user_id, f'account_control_{acc_id}'))
            context.user_data['action'] = None
            return
        context.user_data['identity_token'] = identity_token
        context.user_data['step'] = 'new_email'
        await update.message.reply_text(
            "✅ تم التحقق من كود الأمان.\n\n📧 أرسل البريد الإلكتروني الجديد:",
            reply_markup=get_back_button(user_id, f'account_control_{acc_id}')
        )
        return

    elif step == 'new_email':
        new_email = text
        identity_token = context.user_data.get('identity_token')
        if send_otp(access_token, new_email):
            context.user_data['new_email'] = new_email
            context.user_data['step'] = 'new_otp_sec'
            await update.message.reply_text(
                f"📧 تم إرسال OTP إلى `{new_email}`\n\n🔑 أرسل رمز OTP الذي وصلك:",
                reply_markup=get_back_button(user_id, f'account_control_{acc_id}')
            )
        else:
            await update.message.reply_text("❌ فشل إرسال OTP.", reply_markup=get_back_button(user_id, f'account_control_{acc_id}'))
            context.user_data['action'] = None
        return

    elif step == 'new_otp_sec':
        new_otp = text
        new_email = context.user_data.get('new_email')
        identity_token = context.user_data.get('identity_token')
        verifier_token = verify_otp(access_token, new_email, new_otp)
        if not verifier_token:
            await update.message.reply_text("❌ فشل التحقق من OTP الجديد.", reply_markup=get_back_button(user_id, f'account_control_{acc_id}'))
            context.user_data['action'] = None
            return
        if create_rebind_request(access_token, identity_token, verifier_token, new_email):
            await update.message.reply_text(
                f"✅ **تم تغيير بريد الاستعادة بنجاح!**\n\n📧 البريد القديم: `{context.user_data.get('old_email')}`\n📧 البريد الجديد: `{new_email}`",
                reply_markup=get_back_button(user_id, f'account_control_{acc_id}')
            )
        else:
            await update.message.reply_text(
                "❌ فشل تغيير بريد الاستعادة.",
                reply_markup=get_back_button(user_id, f'account_control_{acc_id}')
            )
        context.user_data['action'] = None
        return

# ---------- إلغاء ارتباط الاستعادة (يطلب اختيار الطريقة) ----------
async def handle_unbind(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    query = update.callback_query
    await query.answer()
    acc_id = query.data.split('_')[1]
    keyboard = [
        [InlineKeyboardButton("🔑 عبر رمز التحقق OTP", callback_data=f'unbind_otp_{acc_id}')],
        [InlineKeyboardButton("🔐 عبر كود الأمان", callback_data=f'unbind_sec_{acc_id}')],
        [InlineKeyboardButton("🔙 عودة", callback_data=f'account_control_{acc_id}')]
    ]
    await query.edit_message_text(
        "⛓️‍💥 **إلغاء ارتباط الاستعادة**\n\nاختر طريقة التحقق:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ---------- إلغاء الربط عبر OTP (دمج أداة OBITO UNBIND) ----------
async def handle_unbind_otp(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    query = update.callback_query
    await query.answer()
    acc_id = _extract_account_id(query.data)
    context.user_data['action'] = 'waiting_unbind_otp'
    context.user_data['acc_id'] = acc_id
    context.user_data['step'] = 'email'
    await query.edit_message_text(
        "📧 أرسل البريد الإلكتروني المرتبط حالياً:",
        reply_markup=get_back_button(user_id, f'account_control_{acc_id}')
    )

async def handle_unbind_otp_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()
    acc_id = context.user_data.get('acc_id')
    step = context.user_data.get('step', 'email')
    if not acc_id:
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

    if step == 'email':
        context.user_data['email'] = text
        if send_otp(access_token, text):
            context.user_data['step'] = 'otp'
            await update.message.reply_text(
                f"📧 تم إرسال OTP إلى `{text}`\n\n🔑 أرسل رمز OTP الذي وصلك:",
                reply_markup=get_back_button(user_id, f'account_control_{acc_id}')
            )
        else:
            await update.message.reply_text("❌ فشل إرسال OTP.", reply_markup=get_back_button(user_id, f'account_control_{acc_id}'))
            context.user_data['action'] = None
        return

    elif step == 'otp':
        otp = text
        email = context.user_data.get('email')
        identity_token = verify_identity_otp(access_token, email, otp)
        if not identity_token:
            await update.message.reply_text("❌ فشل التحقق من OTP.", reply_markup=get_back_button(user_id, f'account_control_{acc_id}'))
            context.user_data['action'] = None
            return
        if create_unbind_request(access_token, identity_token):
            await update.message.reply_text(
                f"✅ **تم إلغاء ربط بريد الاستعادة بنجاح!**\n\n📧 البريد: `{email}`",
                reply_markup=get_back_button(user_id, f'account_control_{acc_id}')
            )
        else:
            await update.message.reply_text("❌ فشل إلغاء الربط.", reply_markup=get_back_button(user_id, f'account_control_{acc_id}'))
        context.user_data['action'] = None
        return

# ---------- إلغاء الربط عبر كود أمان ----------
async def handle_unbind_sec(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    query = update.callback_query
    await query.answer()
    acc_id = _extract_account_id(query.data)
    context.user_data['action'] = 'waiting_unbind_sec'
    context.user_data['acc_id'] = acc_id
    context.user_data['step'] = 'email'
    await query.edit_message_text(
        "📧 أرسل البريد الإلكتروني المرتبط حالياً:",
        reply_markup=get_back_button(user_id, f'account_control_{acc_id}')
    )

async def handle_unbind_sec_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()
    acc_id = context.user_data.get('acc_id')
    step = context.user_data.get('step', 'email')
    if not acc_id:
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

    if step == 'email':
        context.user_data['email'] = text
        context.user_data['step'] = 'security_code'
        await update.message.reply_text(
            f"📧 تم حفظ البريد: {text}\n\n🔐 أرسل كود الأمان (6 أرقام):",
            reply_markup=get_back_button(user_id, f'account_control_{acc_id}')
        )
        return

    elif step == 'security_code':
        sec_code = text
        email = context.user_data.get('email')
        identity_token = verify_identity_sec(access_token, email, sec_code)
        if not identity_token:
            await update.message.reply_text("❌ فشل التحقق من كود الأمان.", reply_markup=get_back_button(user_id, f'account_control_{acc_id}'))
            context.user_data['action'] = None
            return
        if create_unbind_request(access_token, identity_token):
            await update.message.reply_text(
                f"✅ **تم إلغاء ربط بريد الاستعادة بنجاح!**\n\n📧 البريد: `{email}`",
                reply_markup=get_back_button(user_id, f'account_control_{acc_id}')
            )
        else:
            await update.message.reply_text("❌ فشل إلغاء الربط.", reply_markup=get_back_button(user_id, f'account_control_{acc_id}'))
        context.user_data['action'] = None
        return

# ---------- إلغاء طلب الربط المعلق ----------
async def handle_cancel_bind(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    query = update.callback_query
    await query.answer()
    acc_id = _extract_account_id(query.data)
    accounts = get_user_accounts(user_id)
    account = next((acc for acc in accounts if acc['id'] == acc_id), None)
    if not account:
        await query.edit_message_text("⚠️ الحساب غير موجود.", reply_markup=get_main_menu(user_id))
        return
    access_token = get_access_token_for_account(account)
    if not access_token:
        await query.edit_message_text(get_text(user_id, 'no_access_token'), reply_markup=get_back_button(user_id, f'account_control_{acc_id}'))
        return
    wait_msg = await query.edit_message_text("⏳ جاري إلغاء طلب الربط المعلق...", reply_markup=get_back_button(user_id, f'account_control_{acc_id}'))
    try:
        if cancel_request(access_token):
            await wait_msg.edit_text("✅ تم إلغاء طلب الربط المعلق بنجاح!", reply_markup=get_back_button(user_id, f'account_control_{acc_id}'))
        else:
            await wait_msg.edit_text("❌ فشل إلغاء الطلب المعلق.", reply_markup=get_back_button(user_id, f'account_control_{acc_id}'))
    except Exception as e:
        await wait_msg.edit_text(f"❌ حدث خطأ: {str(e)[:100]}", reply_markup=get_back_button(user_id, f'account_control_{acc_id}'))

# ---------- سجل تسجيل الدخول ----------
async def handle_login_history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    query = update.callback_query
    await query.answer()
    acc_id = _extract_account_id(query.data)
    accounts = get_user_accounts(user_id)
    account = next((acc for acc in accounts if acc['id'] == acc_id), None)
    if not account:
        await query.edit_message_text("⚠️ الحساب غير موجود.", reply_markup=get_main_menu(user_id))
        return
    access_token = get_access_token_for_account(account)
    if not access_token:
        await query.edit_message_text(get_text(user_id, 'no_access_token'), reply_markup=get_back_button(user_id, f'account_control_{acc_id}'))
        return
    wait_msg = await query.edit_message_text("⏳ جاري جلب سجل تسجيل الدخول...", reply_markup=get_back_button(user_id, f'account_control_{acc_id}'))
    try:
        player_info = get_player_info(access_token)
        if player_info.get("success"):
            nickname = player_info.get("nickname", "غير معروف")
            uid = player_info.get("uid", "غير معروف")
            region = player_info.get("region", "غير معروف")
            history_result = get_login_history(access_token)
            if history_result.get("success"):
                records = history_result.get("records", [])
                if records:
                    text = f"📋 **سجل تسجيل الدخول**\n\n👤 **الاسم:** {nickname}\n🆔 **UID:** {uid}\n🌍 **المنطقة:** {region}\n\n"
                    for i, rec in enumerate(records[:10], 1):
                        text += f"{i}. {rec}\n"
                    msg = text
                else:
                    msg = f"📋 **سجل تسجيل الدخول**\n\n👤 {nickname}\n🆔 {uid}\n\nلا توجد سجلات."
            else:
                msg = f"⚠️ لم نتمكن من جلب سجل تسجيل الدخول: {history_result.get('error', '')}"
        else:
            msg = "⚠️ لم نتمكن من جلب معلومات اللاعب."
    except Exception as e:
        msg = f"❌ حدث خطأ: {str(e)[:100]}"
    await wait_msg.edit_text(msg, reply_markup=get_back_button(user_id, f'account_control_{acc_id}'))

# ---------- الروابط المفصلة ----------
async def handle_bound_accounts_detailed(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    query = update.callback_query
    await query.answer()
    acc_id = _extract_account_id(query.data)
    accounts = get_user_accounts(user_id)
    account = next((acc for acc in accounts if acc['id'] == acc_id), None)
    if not account:
        await query.edit_message_text("⚠️ الحساب غير موجود.", reply_markup=get_main_menu(user_id))
        return
    access_token = get_access_token_for_account(account)
    if not access_token:
        await query.edit_message_text(get_text(user_id, 'no_access_token'), reply_markup=get_back_button(user_id, f'account_control_{acc_id}'))
        return
    wait_msg = await query.edit_message_text("⏳ جاري جلب الروابط الثانوية...", reply_markup=get_back_button(user_id, f'account_control_{acc_id}'))
    try:
        result = get_bound_accounts_detailed(access_token)
        if result.get("success"):
            bounded = result.get("bounded", [])
            available = result.get("available", [])
            text = "🔗 **المنصات المرتبطة (مفصلة)**\n\n"
            if bounded:
                text += "**✅ المنصات المرتبطة:**\n"
                for p in bounded:
                    text += f"• {p.get('name', 'غير معروف')}\n"
            else:
                text += "**❌ لا توجد منصات مرتبطة.**\n"
            if available:
                text += "\n**📌 المنصات المتاحة للربط:**\n"
                for p in available:
                    text += f"• {p.get('name', 'غير معروف')}\n"
            msg = text
        else:
            msg = "⚠️ لم نتمكن من جلب الروابط الثانوية."
    except Exception as e:
        msg = f"❌ حدث خطأ: {str(e)[:100]}"
    await wait_msg.edit_text(msg, reply_markup=get_back_button(user_id, f'account_control_{acc_id}'))

# ---------- تبنيد الحساب ----------
async def handle_ban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    query = update.callback_query
    await query.answer()
    acc_id = _extract_account_id(query.data)
    accounts = get_user_accounts(user_id)
    account = next((acc for acc in accounts if acc['id'] == acc_id), None)
    if not account:
        await query.edit_message_text("⚠️ الحساب غير موجود.", reply_markup=get_main_menu(user_id))
        return
    access_token = get_access_token_for_account(account)
    if not access_token:
        await query.edit_message_text(get_text(user_id, 'no_access_token'), reply_markup=get_back_button(user_id, f'account_control_{acc_id}'))
        return
    is_active = is_ban_active_account(acc_id)
    if is_active:
        keyboard = [
            [InlineKeyboardButton("✅ نعم، إيقاف", callback_data=f'ban_stop_{acc_id}'),
             InlineKeyboardButton("❌ إلغاء", callback_data=f'account_control_{acc_id}')]
        ]
        await query.edit_message_text(
            f"☠️ **تبنيد الحساب**\n\n⚠️ يوجد جلسة تبنيد نشطة.\n\nهل تريد إيقافها؟",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return
    keyboard = [
        [InlineKeyboardButton("✅ نعم، بدء التبنيد", callback_data=f'ban_start_{acc_id}'),
         InlineKeyboardButton("❌ إلغاء", callback_data=f'account_control_{acc_id}')]
    ]
    await query.edit_message_text(
        f"☠️ **تبنيد الحساب**\n\n⚠️ سيتم تشغيل اتصالات مستمرة.\n👤 الحساب: {account['name']}\n🆔 المعرف: {acc_id}\n\nهل تريد بدء التبنيد؟",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def handle_ban_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    query = update.callback_query
    await query.answer()
    acc_id = _extract_account_id(query.data)
    accounts = get_user_accounts(user_id)
    account = next((acc for acc in accounts if acc['id'] == acc_id), None)
    if not account:
        await query.edit_message_text("⚠️ الحساب غير موجود.", reply_markup=get_main_menu(user_id))
        return
    access_token = get_access_token_for_account(account)
    if not access_token:
        await query.edit_message_text(get_text(user_id, 'no_access_token'), reply_markup=get_back_button(user_id, f'account_control_{acc_id}'))
        return
    wait_msg = await query.edit_message_text("⏳ جاري بدء تبنيد الحساب...", reply_markup=get_back_button(user_id, f'account_control_{acc_id}'))
    try:
        result = start_ban_account(access_token)
        if result.get("success"):
            await wait_msg.edit_text(
                f"☠️ **تم بدء تبنيد الحساب!**\n\n👤 الاسم: {result.get('account_name', account['name'])}\n🆔 المعرف: {acc_id}\n\n⚠️ جلسة التبنيد تعمل في الخلفية.",
                reply_markup=get_back_button(user_id, f'account_control_{acc_id}')
            )
        else:
            await wait_msg.edit_text(f"❌ فشل بدء التبنيد: {result.get('error', 'خطأ غير معروف')}", reply_markup=get_back_button(user_id, f'account_control_{acc_id}'))
    except Exception as e:
        await wait_msg.edit_text(f"❌ حدث خطأ: {str(e)[:100]}", reply_markup=get_back_button(user_id, f'account_control_{acc_id}'))

async def handle_ban_stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    query = update.callback_query
    await query.answer()
    acc_id = _extract_account_id(query.data)
    wait_msg = await query.edit_message_text("⏳ جاري إيقاف تبنيد الحساب...", reply_markup=get_back_button(user_id, f'account_control_{acc_id}'))
    try:
        result = stop_ban_account(acc_id)
        if result.get("success"):
            await wait_msg.edit_text(
                f"⏹️ **تم إيقاف تبنيد الحساب!**\n\n🆔 المعرف: {acc_id}",
                reply_markup=get_back_button(user_id, f'account_control_{acc_id}')
            )
        else:
            await wait_msg.edit_text(f"❌ فشل إيقاف التبنيد: {result.get('error', 'خطأ غير معروف')}", reply_markup=get_back_button(user_id, f'account_control_{acc_id}'))
    except Exception as e:
        await wait_msg.edit_text(f"❌ حدث خطأ: {str(e)[:100]}", reply_markup=get_back_button(user_id, f'account_control_{acc_id}'))

# ========== معالجات إدخال النصوص الأساسية ==========
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
        if send_otp(access_token, email):
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
        verifier_token = verify_otp(access_token, email, otp)
        if verifier_token:
            await update.message.reply_text(get_text(user_id, 'otp_verified'))
            context.user_data['verifier_token'] = verifier_token
            context.user_data['action'] = 'waiting_secondary_password'
            await update.message.reply_text("🔐 أرسل كلمة المرور الثانوية (security_code):")
        else:
            await update.message.reply_text(get_text(user_id, 'operation_failed', error="OTP غير صحيح"))
            context.user_data['action'] = None
    elif operation == 'verify_otp':
        verifier_token = verify_otp(access_token, email, otp)
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
    identity_token = verify_identity_sec(access_token, email, sec_code)
    if identity_token:
        if verifier_token:
            if create_bind_request(access_token, email, verifier_token, sec_code):
                await update.message.reply_text(get_text(user_id, 'bind_request_created', email=email))
            else:
                await update.message.reply_text(get_text(user_id, 'operation_failed', error="فشل إنشاء طلب الربط"))
        else:
            await update.message.reply_text(get_text(user_id, 'operation_failed', error="لم يتم الحصول على التوكنات المطلوبة"))
    else:
        await update.message.reply_text(get_text(user_id, 'operation_failed', error="فشل التحقق من كلمة المرور الثانوية"))
    context.user_data['action'] = None

async def handle_unbind_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    pass

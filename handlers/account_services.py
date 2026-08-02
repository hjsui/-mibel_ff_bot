# -*- coding: utf-8 -*-

import asyncio
import time
import logging
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
    # دوال JWT
    get_friends, send_friend_request, remove_friend,
    get_clan_info, get_clan_members, request_join_clan, quit_clan,
    get_player_stats, get_attendance, get_login_history, get_bound_accounts_detailed,
    get_player_info, get_jwt_from_access_token
)
from external_apis import friend_request, check_ban
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

# ========== الخدمات الأساسية ==========

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
        await wait_msg.edit_text("❌ فشل التحويل. تأكد من الرابط.", reply_markup=get_back_button(user_id))
        return
    account_id = access_data.get("account_id")
    nickname = access_data.get("nickname", "لاعب")
    region = access_data.get("region", "ME")
    if add_account(user_id, nickname, account_id, text, region):
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

async def handle_account_control(update: Update, context: ContextTypes.DEFAULT_TYPE):
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

async def handle_delete_account(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    query = update.callback_query
    await query.answer()
    acc_id = query.data.split('_')[1]
    if delete_account(user_id, acc_id):
        await safe_edit_message(query, get_text(user_id, 'account_deleted'), get_main_menu(user_id))
    else:
        await safe_edit_message(query, "⚠️ فشل الحذف.", get_main_menu(user_id))

# ========== كشف الاستعادة ==========
async def handle_recovery(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    query = update.callback_query
    await query.answer()
    acc_id = query.data.split('_')[1]
    accounts = get_user_accounts(user_id)
    account = next((acc for acc in accounts if acc['id'] == acc_id), None)
    if not account:
        await safe_edit_message(query, "⚠️ الحساب غير موجود.", get_main_menu(user_id))
        return
    access_token = get_access_token_for_account(account)
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

# ========== كشف الروابط ==========
async def handle_links(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    query = update.callback_query
    await query.answer()
    acc_id = query.data.split('_')[1]
    accounts = get_user_accounts(user_id)
    account = next((acc for acc in accounts if acc['id'] == acc_id), None)
    if not account:
        await safe_edit_message(query, "⚠️ الحساب غير موجود.", get_main_menu(user_id))
        return
    access_token = get_access_token_for_account(account)
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

# ========== تجربة رمز الأمان ==========
async def handle_try_otp(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    query = update.callback_query
    await query.answer()
    acc_id = query.data.split('_')[1]
    context.user_data['action'] = 'waiting_email'
    context.user_data['acc_id'] = acc_id
    context.user_data['operation'] = 'verify_otp'
    await safe_edit_message(query, get_text(user_id, 'enter_email'), get_back_button(user_id, f'account_control_{acc_id}'))

# ========== طلب صداقة (الأساسي) ==========
async def handle_friend_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    query = update.callback_query
    await query.answer()
    acc_id = query.data.split('_')[1]
    context.user_data['action'] = 'waiting_friend_uid'
    context.user_data['acc_id'] = acc_id
    await safe_edit_message(query, get_text(user_id, 'enter_target_uid'), get_back_button(user_id, f'account_control_{acc_id}'))

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
            await update.message.reply_text("⚠️ الخادم غير متصل حالياً.", reply_markup=get_back_button(user_id, f'account_control_{acc_id}'))
        else:
            await update.message.reply_text(get_text(user_id, 'friend_sent', uid=target_uid), reply_markup=get_back_button(user_id, f'account_control_{acc_id}'))
    except Exception as e:
        logging.error(f"handle_friend_input error: {e}")
        await update.message.reply_text("⚠️ حدث خطأ غير متوقع.", reply_markup=get_back_button(user_id, f'account_control_{acc_id}'))
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
    await safe_edit_message(query, msg, get_back_button(user_id, f'account_control_{acc_id}'))

# ========== فحص الحظر ==========
async def handle_ban_check(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    query = update.callback_query
    await query.answer()
    acc_id = query.data.split('_')[1]
    accounts = get_user_accounts(user_id)
    account = next((acc for acc in accounts if acc['id'] == acc_id), None)
    if not account:
        await safe_edit_message(query, "⚠️ الحساب غير موجود.", get_back_button(user_id))
        return
    access_token = get_access_token_for_account(account)
    if not access_token:
        await safe_edit_message(query, get_text(user_id, 'no_access_token'), get_back_button(user_id, f'account_control_{acc_id}'))
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
    except Exception as e:
        logging.error(f"handle_ban_check error: {e}")
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
        await safe_edit_message(query, "⚠️ الحساب غير موجود.", get_main_menu(user_id))
        return
    access_token = get_access_token_for_account(account)
    if not access_token:
        await safe_edit_message(query, get_text(user_id, 'no_access_token'), get_back_button(user_id, f'account_control_{acc_id}'))
        return
    wait_msg = await query.edit_message_text("⏳ جاري حرق التوكن...", reply_markup=get_back_button(user_id, f'account_control_{acc_id}'))
    try:
        if revoke_token(access_token):
            account['access_token'] = None
            account['token_expiry'] = None
            await wait_msg.edit_text("🔥 تم حرق التوكن وإبطاله بنجاح (تم تسجيل الخروج).", reply_markup=get_back_button(user_id, f'account_control_{acc_id}'))
        else:
            await wait_msg.edit_text("❌ فشل حرق التوكن. تأكد من صحة التوكن.", reply_markup=get_back_button(user_id, f'account_control_{acc_id}'))
    except Exception as e:
        logging.error(f"handle_burn_token error: {e}")
        await wait_msg.edit_text(f"❌ حدث خطأ: {str(e)[:100]}", reply_markup=get_back_button(user_id, f'account_control_{acc_id}'))

# ================================================================
# ========== إضافة/تغيير استعادة ==========
# ================================================================

async def handle_add_recovery(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    query = update.callback_query
    await query.answer()
    acc_id = query.data.split('_')[1]
    keyboard = [
        [InlineKeyboardButton("🔑 عبر OTP", callback_data=f'addrec_otp_{acc_id}')],
        [InlineKeyboardButton("🔐 عبر كود أمان", callback_data=f'addrec_sec_{acc_id}')],
        [InlineKeyboardButton("🔙 عودة", callback_data=f'account_control_{acc_id}')]
    ]
    await safe_edit_message(query, "➕ **إضافة/تغيير استعادة**\n\nاختر طريقة التحقق:", InlineKeyboardMarkup(keyboard))

async def handle_add_recovery_otp(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    query = update.callback_query
    await query.answer()
    acc_id = _extract_account_id(query.data)
    context.user_data['action'] = 'waiting_add_recovery_otp'
    context.user_data['acc_id'] = acc_id
    context.user_data['step'] = 'old_email'
    await safe_edit_message(query, "📧 أرسل البريد القديم (المرتبط حالياً):", get_back_button(user_id, f'account_control_{acc_id}'))

async def handle_add_recovery_otp_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()
    acc_id = context.user_data.get('acc_id')
    step = context.user_data.get('step', 'old_email')
    if not acc_id:
        await update.message.reply_text("⚠️ انتهت الجلسة.")
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
            await update.message.reply_text(f"📧 تم إرسال OTP إلى `{text}`\n\n🔑 أرسل الرمز:", reply_markup=get_back_button(user_id, f'account_control_{acc_id}'))
        else:
            await update.message.reply_text("❌ فشل إرسال OTP.", reply_markup=get_back_button(user_id, f'account_control_{acc_id}'))
            context.user_data['action'] = None
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
        await update.message.reply_text("✅ تم التحقق من البريد القديم.\n\n📧 أرسل البريد الجديد:", reply_markup=get_back_button(user_id, f'account_control_{acc_id}'))
    elif step == 'new_email':
        context.user_data['new_email'] = text
        if send_otp(access_token, text):
            context.user_data['step'] = 'new_otp'
            await update.message.reply_text(f"📧 تم إرسال OTP إلى `{text}`\n\n🔑 أرسل الرمز:", reply_markup=get_back_button(user_id, f'account_control_{acc_id}'))
        else:
            await update.message.reply_text("❌ فشل إرسال OTP إلى البريد الجديد.", reply_markup=get_back_button(user_id, f'account_control_{acc_id}'))
            context.user_data['action'] = None
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
            await update.message.reply_text(f"✅ **تم تغيير بريد الاستعادة بنجاح!**\n\n📧 القديم: `{context.user_data.get('old_email')}`\n📧 الجديد: `{new_email}`", reply_markup=get_back_button(user_id, f'account_control_{acc_id}'))
        else:
            await update.message.reply_text("❌ فشل تغيير البريد.", reply_markup=get_back_button(user_id, f'account_control_{acc_id}'))
        context.user_data['action'] = None

# ====== إضافة/تغيير عبر كود أمان ======
async def handle_add_recovery_sec(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    query = update.callback_query
    await query.answer()
    acc_id = _extract_account_id(query.data)
    context.user_data['action'] = 'waiting_add_recovery_sec'
    context.user_data['acc_id'] = acc_id
    context.user_data['step'] = 'old_email'
    await safe_edit_message(query, "📧 أرسل البريد القديم:", get_back_button(user_id, f'account_control_{acc_id}'))

async def handle_add_recovery_sec_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()
    acc_id = context.user_data.get('acc_id')
    step = context.user_data.get('step', 'old_email')
    if not acc_id:
        await update.message.reply_text("⚠️ انتهت الجلسة.")
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
        await update.message.reply_text(f"📧 تم حفظ البريد القديم: {text}\n\n🔐 أرسل كود الأمان (6 أرقام):", reply_markup=get_back_button(user_id, f'account_control_{acc_id}'))
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
        await update.message.reply_text("✅ تم التحقق من كود الأمان.\n\n📧 أرسل البريد الجديد:", reply_markup=get_back_button(user_id, f'account_control_{acc_id}'))
    elif step == 'new_email':
        new_email = text
        identity_token = context.user_data.get('identity_token')
        if send_otp(access_token, new_email):
            context.user_data['new_email'] = new_email
            context.user_data['step'] = 'new_otp_sec'
            await update.message.reply_text(f"📧 تم إرسال OTP إلى `{new_email}`\n\n🔑 أرسل الرمز:", reply_markup=get_back_button(user_id, f'account_control_{acc_id}'))
        else:
            await update.message.reply_text("❌ فشل إرسال OTP.", reply_markup=get_back_button(user_id, f'account_control_{acc_id}'))
            context.user_data['action'] = None
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
            await update.message.reply_text(f"✅ **تم تغيير بريد الاستعادة بنجاح!**\n\n📧 القديم: `{context.user_data.get('old_email')}`\n📧 الجديد: `{new_email}`", reply_markup=get_back_button(user_id, f'account_control_{acc_id}'))
        else:
            await update.message.reply_text("❌ فشل تغيير البريد.", reply_markup=get_back_button(user_id, f'account_control_{acc_id}'))
        context.user_data['action'] = None

# ================================================================
# ========== إلغاء ارتباط الاستعادة ==========
# ================================================================

async def handle_unbind(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    query = update.callback_query
    await query.answer()
    acc_id = query.data.split('_')[1]
    keyboard = [
        [InlineKeyboardButton("🔑 عبر OTP", callback_data=f'unbind_otp_{acc_id}')],
        [InlineKeyboardButton("🔐 عبر كود أمان", callback_data=f'unbind_sec_{acc_id}')],
        [InlineKeyboardButton("🔙 عودة", callback_data=f'account_control_{acc_id}')]
    ]
    await safe_edit_message(query, "⛓️‍💥 **إلغاء ارتباط الاستعادة**\n\nاختر طريقة التحقق:", InlineKeyboardMarkup(keyboard))

async def handle_unbind_otp(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    query = update.callback_query
    await query.answer()
    acc_id = _extract_account_id(query.data)
    context.user_data['action'] = 'waiting_unbind_otp'
    context.user_data['acc_id'] = acc_id
    context.user_data['step'] = 'email'
    await safe_edit_message(query, "📧 أرسل البريد المرتبط حالياً:", get_back_button(user_id, f'account_control_{acc_id}'))

async def handle_unbind_otp_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()
    acc_id = context.user_data.get('acc_id')
    step = context.user_data.get('step', 'email')
    if not acc_id:
        await update.message.reply_text("⚠️ انتهت الجلسة.")
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
            await update.message.reply_text(f"📧 تم إرسال OTP إلى `{text}`\n\n🔑 أرسل الرمز:", reply_markup=get_back_button(user_id, f'account_control_{acc_id}'))
        else:
            await update.message.reply_text("❌ فشل إرسال OTP.", reply_markup=get_back_button(user_id, f'account_control_{acc_id}'))
            context.user_data['action'] = None
    elif step == 'otp':
        otp = text
        email = context.user_data.get('email')
        identity_token = verify_identity_otp(access_token, email, otp)
        if not identity_token:
            await update.message.reply_text("❌ فشل التحقق من OTP.", reply_markup=get_back_button(user_id, f'account_control_{acc_id}'))
            context.user_data['action'] = None
            return
        if create_unbind_request(access_token, identity_token):
            await update.message.reply_text(f"✅ **تم إلغاء ربط بريد الاستعادة بنجاح!**\n\n📧 البريد: `{email}`", reply_markup=get_back_button(user_id, f'account_control_{acc_id}'))
        else:
            await update.message.reply_text("❌ فشل إلغاء الربط.", reply_markup=get_back_button(user_id, f'account_control_{acc_id}'))
        context.user_data['action'] = None

async def handle_unbind_sec(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    query = update.callback_query
    await query.answer()
    acc_id = _extract_account_id(query.data)
    context.user_data['action'] = 'waiting_unbind_sec'
    context.user_data['acc_id'] = acc_id
    context.user_data['step'] = 'email'
    await safe_edit_message(query, "📧 أرسل البريد المرتبط حالياً:", get_back_button(user_id, f'account_control_{acc_id}'))

async def handle_unbind_sec_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()
    acc_id = context.user_data.get('acc_id')
    step = context.user_data.get('step', 'email')
    if not acc_id:
        await update.message.reply_text("⚠️ انتهت الجلسة.")
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
        await update.message.reply_text(f"📧 تم حفظ البريد: {text}\n\n🔐 أرسل كود الأمان (6 أرقام):", reply_markup=get_back_button(user_id, f'account_control_{acc_id}'))
    elif step == 'security_code':
        sec_code = text
        email = context.user_data.get('email')
        identity_token = verify_identity_sec(access_token, email, sec_code)
        if not identity_token:
            await update.message.reply_text("❌ فشل التحقق من كود الأمان.", reply_markup=get_back_button(user_id, f'account_control_{acc_id}'))
            context.user_data['action'] = None
            return
        if create_unbind_request(access_token, identity_token):
            await update.message.reply_text(f"✅ **تم إلغاء ربط بريد الاستعادة بنجاح!**\n\n📧 البريد: `{email}`", reply_markup=get_back_button(user_id, f'account_control_{acc_id}'))
        else:
            await update.message.reply_text("❌ فشل إلغاء الربط.", reply_markup=get_back_button(user_id, f'account_control_{acc_id}'))
        context.user_data['action'] = None

# ================================================================
# ========== إلغاء طلب الربط المعلق ==========
# ================================================================

async def handle_cancel_bind(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    query = update.callback_query
    await query.answer()
    acc_id = _extract_account_id(query.data)
    accounts = get_user_accounts(user_id)
    account = next((acc for acc in accounts if acc['id'] == acc_id), None)
    if not account:
        await safe_edit_message(query, "⚠️ الحساب غير موجود.", get_main_menu(user_id))
        return
    access_token = get_access_token_for_account(account)
    if not access_token:
        await safe_edit_message(query, get_text(user_id, 'no_access_token'), get_back_button(user_id, f'account_control_{acc_id}'))
        return
    if cancel_request(access_token):
        await safe_edit_message(query, "✅ تم إلغاء طلب الربط المعلق!", get_back_button(user_id, f'account_control_{acc_id}'))
    else:
        await safe_edit_message(query, "❌ فشل إلغاء الطلب.", get_back_button(user_id, f'account_control_{acc_id}'))

# ================================================================
# ========== تبنيد الحساب ==========
# ================================================================

try:
    from ban_manager import start_ban, stop_ban, is_ban_active
except ImportError:
    start_ban = stop_ban = is_ban_active = None

async def handle_ban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    query = update.callback_query
    await query.answer()
    acc_id = _extract_account_id(query.data)
    accounts = get_user_accounts(user_id)
    account = next((acc for acc in accounts if acc['id'] == acc_id), None)
    if not account:
        await safe_edit_message(query, "⚠️ الحساب غير موجود.", get_main_menu(user_id))
        return
    access_token = get_access_token_for_account(account)
    if not access_token:
        await safe_edit_message(query, get_text(user_id, 'no_access_token'), get_back_button(user_id, f'account_control_{acc_id}'))
        return
    if is_ban_active and is_ban_active(acc_id):
        keyboard = [[InlineKeyboardButton("✅ إيقاف", callback_data=f'ban_stop_{acc_id}'), InlineKeyboardButton("❌ إلغاء", callback_data=f'account_control_{acc_id}')]]
        await safe_edit_message(query, "☠️ يوجد جلسة تبنيد نشطة.\nهل تريد إيقافها?", InlineKeyboardMarkup(keyboard))
        return
    keyboard = [[InlineKeyboardButton("✅ بدء التبنيد", callback_data=f'ban_start_{acc_id}'), InlineKeyboardButton("❌ إلغاء", callback_data=f'account_control_{acc_id}')]]
    await safe_edit_message(query, "☠️ سيتم بدء تبنيد الحساب.\nهل تريد المتابعة?", InlineKeyboardMarkup(keyboard))

async def handle_ban_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    query = update.callback_query
    await query.answer()
    acc_id = _extract_account_id(query.data)
    accounts = get_user_accounts(user_id)
    account = next((acc for acc in accounts if acc['id'] == acc_id), None)
    if not account:
        await safe_edit_message(query, "⚠️ الحساب غير موجود.", get_main_menu(user_id))
        return
    access_token = get_access_token_for_account(account)
    if not access_token or not start_ban:
        await safe_edit_message(query, "❌ فشل بدء التبنيد.", get_back_button(user_id, f'account_control_{acc_id}'))
        return
    result = start_ban(access_token)
    if result.get("success"):
        await safe_edit_message(query, f"☠️ **تم بدء تبنيد الحساب!**\n👤 {result.get('account_name', account['name'])}", get_back_button(user_id, f'account_control_{acc_id}'))
    else:
        await safe_edit_message(query, f"❌ فشل: {result.get('error', 'خطأ')}", get_back_button(user_id, f'account_control_{acc_id}'))

async def handle_ban_stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    query = update.callback_query
    await query.answer()
    acc_id = _extract_account_id(query.data)
    if stop_ban:
        result = stop_ban(acc_id)
        if result.get("success"):
            await safe_edit_message(query, f"⏹️ **تم إيقاف التبنيد!**\n🆔 {acc_id}", get_back_button(user_id, f'account_control_{acc_id}'))
        else:
            await safe_edit_message(query, f"❌ فشل الإيقاف: {result.get('error', 'خطأ')}", get_back_button(user_id, f'account_control_{acc_id}'))
    else:
        await safe_edit_message(query, "❌ خدمة التبنيد غير متوفرة.", get_back_button(user_id, f'account_control_{acc_id}'))

# ================================================================
# ========== الخدمات المتقدمة (باستخدام JWT) ==========
# ================================================================

async def handle_friends_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    query = update.callback_query
    await query.answer()
    acc_id = _extract_account_id(query.data)
    accounts = get_user_accounts(user_id)
    account = next((acc for acc in accounts if acc['id'] == acc_id), None)
    if not account:
        await safe_edit_message(query, "⚠️ الحساب غير موجود.", get_main_menu(user_id))
        return
    access_token = get_access_token_for_account(account)
    if not access_token:
        await safe_edit_message(query, get_text(user_id, 'no_access_token'), get_back_button(user_id, f'account_control_{acc_id}'))
        return
    wait_msg = await query.edit_message_text("⏳ جاري جلب قائمة الأصدقاء...", reply_markup=get_back_button(user_id, f'account_control_{acc_id}'))
    try:
        result = get_friends(access_token)
        if result.get("success"):
            friends = result.get("friends", [])
            if friends:
                text = "👥 **قائمة الأصدقاء**\n\n"
                for friend in friends[:20]:
                    name = friend.get("name", "غير معروف")
                    uid = friend.get("uid", "غير معروف")
                    status = "🟢 متصل" if friend.get("online") else "⚪ غير متصل"
                    text += f"• **{name}** ({uid}) - {status}\n"
                if len(friends) > 20:
                    text += f"\n... وعرض {len(friends)-20} صديق آخر"
                msg = text
            else:
                msg = "👥 لا يوجد أصدقاء في القائمة."
        else:
            msg = f"⚠️ لم نتمكن من جلب قائمة الأصدقاء: {result.get('error', '')}"
    except Exception as e:
        logging.error(f"handle_friends_list error: {e}")
        msg = f"❌ حدث خطأ: {str(e)[:100]}"
    await wait_msg.edit_text(msg, reply_markup=get_back_button(user_id, f'account_control_{acc_id}'))

async def handle_friend_add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    query = update.callback_query
    await query.answer()
    acc_id = _extract_account_id(query.data)
    context.user_data['action'] = 'waiting_friend_add_uid'
    context.user_data['acc_id'] = acc_id
    await safe_edit_message(query, "👤 أرسل UID الشخص الذي تريد إضافته كصديق:", get_back_button(user_id, f'account_control_{acc_id}'))

async def handle_friend_add_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
    wait_msg = await update.message.reply_text("⏳ جاري إرسال طلب الصداقة...")
    try:
        result = send_friend_request(access_token, target_uid)
        if result.get("success"):
            await wait_msg.edit_text(f"✅ **تم إرسال طلب الصداقة بنجاح!**\n\n👤 المستخدم: `{target_uid}`", reply_markup=get_back_button(user_id, f'account_control_{acc_id}'))
        else:
            await wait_msg.edit_text(f"❌ فشل إرسال طلب الصداقة: {result.get('error', 'خطأ غير معروف')}", reply_markup=get_back_button(user_id, f'account_control_{acc_id}'))
    except Exception as e:
        logging.error(f"handle_friend_add_input error: {e}")
        await wait_msg.edit_text(f"❌ حدث خطأ: {str(e)[:100]}", reply_markup=get_back_button(user_id, f'account_control_{acc_id}'))
    context.user_data['action'] = None

async def handle_friend_remove(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    query = update.callback_query
    await query.answer()
    acc_id = _extract_account_id(query.data)
    context.user_data['action'] = 'waiting_friend_remove_uid'
    context.user_data['acc_id'] = acc_id
    await safe_edit_message(query, "👤 أرسل UID الصديق الذي تريد حذفه:", get_back_button(user_id, f'account_control_{acc_id}'))

async def handle_friend_remove_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
    wait_msg = await update.message.reply_text("⏳ جاري حذف الصديق...")
    try:
        result = remove_friend(access_token, target_uid)
        if result.get("success"):
            await wait_msg.edit_text(f"✅ **تم حذف الصديق بنجاح!**\n\n👤 المستخدم: `{target_uid}`", reply_markup=get_back_button(user_id, f'account_control_{acc_id}'))
        else:
            await wait_msg.edit_text(f"❌ فشل حذف الصديق: {result.get('error', 'خطأ غير معروف')}", reply_markup=get_back_button(user_id, f'account_control_{acc_id}'))
    except Exception as e:
        logging.error(f"handle_friend_remove_input error: {e}")
        await wait_msg.edit_text(f"❌ حدث خطأ: {str(e)[:100]}", reply_markup=get_back_button(user_id, f'account_control_{acc_id}'))
    context.user_data['action'] = None

async def handle_clan_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    query = update.callback_query
    await query.answer()
    acc_id = _extract_account_id(query.data)
    context.user_data['action'] = 'waiting_clan_id_info'
    context.user_data['acc_id'] = acc_id
    await safe_edit_message(query, "🏰 أرسل معرف القبيلة (Clan ID):", get_back_button(user_id, f'account_control_{acc_id}'))

async def handle_clan_info_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    clan_id = update.message.text.strip()
    acc_id = context.user_data.get('acc_id')
    if not acc_id or not clan_id.isdigit():
        await update.message.reply_text("⚠️ معرف القبيلة يجب أن يكون أرقاماً.")
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
    wait_msg = await update.message.reply_text("⏳ جاري جلب معلومات القبيلة...")
    try:
        result = get_clan_info(access_token, clan_id)
        if result.get("success"):
            clan = result.get("clan", {})
            name = clan.get("name", "غير معروف")
            level = clan.get("level", "غير معروف")
            members_count = clan.get("member_count", "غير معروف")
            description = clan.get("description", "لا يوجد")
            text = f"🏰 **معلومات القبيلة**\n\n📛 **الاسم:** {name}\n📊 **المستوى:** {level}\n👥 **عدد الأعضاء:** {members_count}\n📝 **الوصف:** {description}"
            await wait_msg.edit_text(text, reply_markup=get_back_button(user_id, f'account_control_{acc_id}'))
        else:
            await wait_msg.edit_text(f"❌ فشل جلب معلومات القبيلة: {result.get('error', 'خطأ غير معروف')}", reply_markup=get_back_button(user_id, f'account_control_{acc_id}'))
    except Exception as e:
        logging.error(f"handle_clan_info_input error: {e}")
        await wait_msg.edit_text(f"❌ حدث خطأ: {str(e)[:100]}", reply_markup=get_back_button(user_id, f'account_control_{acc_id}'))
    context.user_data['action'] = None

async def handle_clan_members(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    query = update.callback_query
    await query.answer()
    acc_id = _extract_account_id(query.data)
    context.user_data['action'] = 'waiting_clan_id_members'
    context.user_data['acc_id'] = acc_id
    await safe_edit_message(query, "🏰 أرسل معرف القبيلة (Clan ID):", get_back_button(user_id, f'account_control_{acc_id}'))

async def handle_clan_members_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    clan_id = update.message.text.strip()
    acc_id = context.user_data.get('acc_id')
    if not acc_id or not clan_id.isdigit():
        await update.message.reply_text("⚠️ معرف القبيلة يجب أن يكون أرقاماً.")
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
    wait_msg = await update.message.reply_text("⏳ جاري جلب أعضاء القبيلة...")
    try:
        result = get_clan_members(access_token, clan_id)
        if result.get("success"):
            members = result.get("members", [])
            if members:
                text = "👥 **أعضاء القبيلة**\n\n"
                for member in members[:20]:
                    name = member.get("name", "غير معروف")
                    role = member.get("role", "عضو")
                    level = member.get("level", "غير معروف")
                    text += f"• **{name}** - {role} (مستوى {level})\n"
                if len(members) > 20:
                    text += f"\n... وعرض {len(members)-20} عضو آخر"
                await wait_msg.edit_text(text, reply_markup=get_back_button(user_id, f'account_control_{acc_id}'))
            else:
                await wait_msg.edit_text("👥 لا يوجد أعضاء في هذه القبيلة.", reply_markup=get_back_button(user_id, f'account_control_{acc_id}'))
        else:
            await wait_msg.edit_text(f"❌ فشل جلب أعضاء القبيلة: {result.get('error', 'خطأ غير معروف')}", reply_markup=get_back_button(user_id, f'account_control_{acc_id}'))
    except Exception as e:
        logging.error(f"handle_clan_members_input error: {e}")
        await wait_msg.edit_text(f"❌ حدث خطأ: {str(e)[:100]}", reply_markup=get_back_button(user_id, f'account_control_{acc_id}'))
    context.user_data['action'] = None

async def handle_clan_join(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    query = update.callback_query
    await query.answer()
    acc_id = _extract_account_id(query.data)
    context.user_data['action'] = 'waiting_clan_id_join'
    context.user_data['acc_id'] = acc_id
    await safe_edit_message(query, "🏰 أرسل معرف القبيلة الذي تريد الانضمام إليها:", get_back_button(user_id, f'account_control_{acc_id}'))

async def handle_clan_join_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    clan_id = update.message.text.strip()
    acc_id = context.user_data.get('acc_id')
    if not acc_id or not clan_id.isdigit():
        await update.message.reply_text("⚠️ معرف القبيلة يجب أن يكون أرقاماً.")
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
    wait_msg = await update.message.reply_text("⏳ جاري طلب الانضمام للقبيلة...")
    try:
        result = request_join_clan(access_token, clan_id)
        if result.get("success"):
            await wait_msg.edit_text(f"✅ **تم إرسال طلب الانضمام للقبيلة بنجاح!**\n\n🏰 القبيلة: `{clan_id}`", reply_markup=get_back_button(user_id, f'account_control_{acc_id}'))
        else:
            await wait_msg.edit_text(f"❌ فشل طلب الانضمام: {result.get('error', 'خطأ غير معروف')}", reply_markup=get_back_button(user_id, f'account_control_{acc_id}'))
    except Exception as e:
        logging.error(f"handle_clan_join_input error: {e}")
        await wait_msg.edit_text(f"❌ حدث خطأ: {str(e)[:100]}", reply_markup=get_back_button(user_id, f'account_control_{acc_id}'))
    context.user_data['action'] = None

async def handle_clan_quit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    query = update.callback_query
    await query.answer()
    acc_id = _extract_account_id(query.data)
    context.user_data['action'] = 'waiting_clan_id_quit'
    context.user_data['acc_id'] = acc_id
    await safe_edit_message(query, "🏰 أرسل معرف القبيلة التي تريد مغادرتها:", get_back_button(user_id, f'account_control_{acc_id}'))

async def handle_clan_quit_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    clan_id = update.message.text.strip()
    acc_id = context.user_data.get('acc_id')
    if not acc_id or not clan_id.isdigit():
        await update.message.reply_text("⚠️ معرف القبيلة يجب أن يكون أرقاماً.")
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
    wait_msg = await update.message.reply_text("⏳ جاري مغادرة القبيلة...")
    try:
        result = quit_clan(access_token, clan_id)
        if result.get("success"):
            await wait_msg.edit_text(f"✅ **تم مغادرة القبيلة بنجاح!**\n\n🏰 القبيلة: `{clan_id}`", reply_markup=get_back_button(user_id, f'account_control_{acc_id}'))
        else:
            await wait_msg.edit_text(f"❌ فشل مغادرة القبيلة: {result.get('error', 'خطأ غير معروف')}", reply_markup=get_back_button(user_id, f'account_control_{acc_id}'))
    except Exception as e:
        logging.error(f"handle_clan_quit_input error: {e}")
        await wait_msg.edit_text(f"❌ حدث خطأ: {str(e)[:100]}", reply_markup=get_back_button(user_id, f'account_control_{acc_id}'))
    context.user_data['action'] = None

async def handle_player_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    query = update.callback_query
    await query.answer()
    acc_id = _extract_account_id(query.data)
    accounts = get_user_accounts(user_id)
    account = next((acc for acc in accounts if acc['id'] == acc_id), None)
    if not account:
        await safe_edit_message(query, "⚠️ الحساب غير موجود.", get_main_menu(user_id))
        return
    access_token = get_access_token_for_account(account)
    if not access_token:
        await safe_edit_message(query, get_text(user_id, 'no_access_token'), get_back_button(user_id, f'account_control_{acc_id}'))
        return
    wait_msg = await query.edit_message_text("⏳ جاري جلب إحصائيات اللاعب...", reply_markup=get_back_button(user_id, f'account_control_{acc_id}'))
    try:
        result = get_player_stats(access_token, account['id'])
        if result.get("success"):
            stats = result.get("stats", {})
            text = f"📊 **إحصائيات اللاعب**\n\n🏆 **المباريات:** {stats.get('matches', 'غير معروف')}\n🥇 **الفوز:** {stats.get('wins', 'غير معروف')}\n💀 **القتل:** {stats.get('kills', 'غير معروف')}\n📈 **الترتيب:** {stats.get('rank', 'غير معروف')}\n⭐ **النقاط:** {stats.get('points', 'غير معروف')}"
            await wait_msg.edit_text(text, reply_markup=get_back_button(user_id, f'account_control_{acc_id}'))
        else:
            await wait_msg.edit_text(f"❌ فشل جلب الإحصائيات: {result.get('error', 'خطأ غير معروف')}", reply_markup=get_back_button(user_id, f'account_control_{acc_id}'))
    except Exception as e:
        logging.error(f"handle_player_stats error: {e}")
        await wait_msg.edit_text(f"❌ حدث خطأ: {str(e)[:100]}", reply_markup=get_back_button(user_id, f'account_control_{acc_id}'))

async def handle_attendance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    query = update.callback_query
    await query.answer()
    acc_id = _extract_account_id(query.data)
    accounts = get_user_accounts(user_id)
    account = next((acc for acc in accounts if acc['id'] == acc_id), None)
    if not account:
        await safe_edit_message(query, "⚠️ الحساب غير موجود.", get_main_menu(user_id))
        return
    access_token = get_access_token_for_account(account)
    if not access_token:
        await safe_edit_message(query, get_text(user_id, 'no_access_token'), get_back_button(user_id, f'account_control_{acc_id}'))
        return
    wait_msg = await query.edit_message_text("⏳ جاري جلب معلومات الحضور اليومي...", reply_markup=get_back_button(user_id, f'account_control_{acc_id}'))
    try:
        result = get_attendance(access_token)
        if result.get("success"):
            attendance = result.get("attendance", {})
            text = f"📅 **الحضور اليومي**\n\n📆 **اليوم:** {attendance.get('day', 'غير معروف')}\n✅ **حالة الحضور:** {'✅ تم الحضور' if attendance.get('checked_in') else '❌ لم يحضر بعد'}\n🎁 **المكافآت المتاحة:** {attendance.get('rewards', 'غير معروف')}"
            await wait_msg.edit_text(text, reply_markup=get_back_button(user_id, f'account_control_{acc_id}'))
        else:
            await wait_msg.edit_text(f"❌ فشل جلب معلومات الحضور: {result.get('error', 'خطأ غير معروف')}", reply_markup=get_back_button(user_id, f'account_control_{acc_id}'))
    except Exception as e:
        logging.error(f"handle_attendance error: {e}")
        await wait_msg.edit_text(f"❌ حدث خطأ: {str(e)[:100]}", reply_markup=get_back_button(user_id, f'account_control_{acc_id}'))

async def handle_login_history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    query = update.callback_query
    await query.answer()
    acc_id = _extract_account_id(query.data)
    accounts = get_user_accounts(user_id)
    account = next((acc for acc in accounts if acc['id'] == acc_id), None)
    if not account:
        await safe_edit_message(query, "⚠️ الحساب غير موجود.", get_main_menu(user_id))
        return
    access_token = get_access_token_for_account(account)
    if not access_token:
        await safe_edit_message(query, get_text(user_id, 'no_access_token'), get_back_button(user_id, f'account_control_{acc_id}'))
        return
    wait_msg = await query.edit_message_text("⏳ جاري جلب سجل تسجيل الدخول...", reply_markup=get_back_button(user_id, f'account_control_{acc_id}'))
    try:
        result = get_login_history(access_token)
        if result.get("success"):
            records = result.get("records", [])
            if records:
                text = "📋 **سجل تسجيل الدخول**\n\n" + "\n".join([f"• {rec}" for rec in records[:10]])
            else:
                text = "📋 لا توجد سجلات تسجيل دخول."
            await wait_msg.edit_text(text, reply_markup=get_back_button(user_id, f'account_control_{acc_id}'))
        else:
            await wait_msg.edit_text(f"⚠️ لم نتمكن من جلب سجل تسجيل الدخول: {result.get('error', '')}", reply_markup=get_back_button(user_id, f'account_control_{acc_id}'))
    except Exception as e:
        logging.error(f"handle_login_history error: {e}")
        await wait_msg.edit_text(f"❌ حدث خطأ: {str(e)[:100]}", reply_markup=get_back_button(user_id, f'account_control_{acc_id}'))

async def handle_bound_accounts_detailed(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    query = update.callback_query
    await query.answer()
    acc_id = _extract_account_id(query.data)
    accounts = get_user_accounts(user_id)
    account = next((acc for acc in accounts if acc['id'] == acc_id), None)
    if not account:
        await safe_edit_message(query, "⚠️ الحساب غير موجود.", get_main_menu(user_id))
        return
    access_token = get_access_token_for_account(account)
    if not access_token:
        await safe_edit_message(query, get_text(user_id, 'no_access_token'), get_back_button(user_id, f'account_control_{acc_id}'))
        return
    wait_msg = await query.edit_message_text("⏳ جاري جلب الروابط الثانوية...", reply_markup=get_back_button(user_id, f'account_control_{acc_id}'))
    try:
        result = get_bound_accounts_detailed(access_token)
        if result.get("success"):
            bounded = result.get("bounded", [])
            available = result.get("available", [])
            text = "🔗 **المنصات المرتبطة (مفصلة)**\n\n"
            if bounded:
                text += "**✅ المنصات المرتبطة:**\n" + "\n".join([f"• {p['name']}" for p in bounded])
            else:
                text += "**❌ لا توجد منصات مرتبطة.**\n"
            if available:
                text += "\n**📌 المنصات المتاحة للربط:**\n" + "\n".join([f"• {p['name']}" for p in available])
            await wait_msg.edit_text(text, reply_markup=get_back_button(user_id, f'account_control_{acc_id}'))
        else:
            await wait_msg.edit_text(f"⚠️ لم نتمكن من جلب الروابط الثانوية: {result.get('error', '')}", reply_markup=get_back_button(user_id, f'account_control_{acc_id}'))
    except Exception as e:
        logging.error(f"handle_bound_accounts_detailed error: {e}")
        await wait_msg.edit_text(f"❌ حدث خطأ: {str(e)[:100]}", reply_markup=get_back_button(user_id, f'account_control_{acc_id}'))

# ========== معالجات الإدخال الأساسية ==========

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

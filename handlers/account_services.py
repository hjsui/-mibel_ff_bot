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
    verify_identity_otp, revoke_token, create_rebind_request,
    create_unbind_request, create_bind_request,
    format_recovery_info, format_platforms
)
from handlers.main_menu import get_back_button, get_main_menu, get_account_controls

# ========== دوال مساعدة ==========
def _extract_account_id(callback_data: str) -> str:
    parts = callback_data.split('_')
    return parts[-1]

async def safe_edit_message(query, text, reply_markup=None):
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
# ========== الخدمات الأساسية ==========
# ================================================================

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
    
    account_id = access_data.get("account_id")
    nickname = access_data.get("nickname", "لاعب")
    region = access_data.get("region", "ME")
    
    if add_account(user_id, nickname, account_id, text, region):
        access_token = access_data.get("result_token")
        if access_token:
            expiry = int(time.time()) + 86400
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
# ========== لوحة الإدارة ==========
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

    check_time = datetime.now().strftime('%Y-%m-%d %H:%M')
    
    expiry = account.get('token_expiry')
    if expiry and int(time.time()) < expiry:
        token_status = "نشط 🟢"
    else:
        token_status = "منتهي / غير نشط 🔴"
    
    jwt_data = convert_eat(account['eat'], "eat_to_jwt")
    jwt_payload = decode_jwt(jwt_data.get("result_token", ""))
    emulator = "مفعل 🖥️" if jwt_payload.get("is_emulator") else "متوقف 📱"
    
    spam_status = "متصل 🟢" if context.user_data.get('spam_active') else "غير متصل 🔴"
    
    msg = (
        f"⚙️ لوحة الإدارة:\n\n"
        f"👤 الاسم: {account['name']}\n"
        f"🆔 الأيدي: {account['id']}\n"
        f"🌍 السيرفر: {account['region']}\n"
        f"⏱ وقت الفحص: {check_time}\n"
        f"📅 انتهاء التوكن: غير محدود\n"
        f"🔗 حالة التوكن: {token_status}\n\n"
        f"🤖 التخمين الآلي: {emulator}\n"
        f"🚀 حالة السبام: {spam_status}"
    )
    
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
# ========== كشف الاستعادة والروابط ==========
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
# ========== إضافة/تغيير استعادة (المنطق الجديد) ==========
# ================================================================

async def handle_add_recovery(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    القائمة الرئيسية لخدمة الاستعادة: تظهر للمستخدم خيار إضافة أو تغيير حسب وجود بريد.
    في حالة الإضافة، لا يظهر خيار "رمز الأمان" لأنه غير منطقي (لا يوجد بريد قديم للتحقق).
    """
    user_id = update.effective_user.id
    query = update.callback_query
    await query.answer()
    
    acc_id = _extract_account_id(query.data)
    context.user_data['acc_id'] = acc_id
    accounts = get_user_accounts(user_id)
    account = next((acc for acc in accounts if acc['id'] == acc_id), None)
    
    if not account:
        await safe_edit_message(query, "⚠️ الحساب غير موجود.", get_main_menu(user_id))
        return

    access_token = get_access_token_for_account(account, user_id)
    if not access_token:
        await safe_edit_message(query, get_text(user_id, 'no_access_token'), get_back_button(user_id, f'account_control_{acc_id}'))
        return

    bind_info = check_bind_info(access_token)
    current_email = bind_info.get("email") if bind_info else None

    if current_email:
        # حالة التغيير (يوجد بريد)
        msg = f"⚠️ الحساب مربوط بالفعل بالبريد:\n`{current_email}`\n\nهل تريد تغييره؟ اختر الطريقة:"
        keyboard = [
            [InlineKeyboardButton("🔑 تغيير عبر OTP", callback_data=f'addrec_otp_{acc_id}')],
            [InlineKeyboardButton("🔐 تغيير عبر رمز الامان", callback_data=f'addrec_sec_{acc_id}')],
            [InlineKeyboardButton("🔙 عودة", callback_data=f'account_control_{acc_id}')]
        ]
    else:
        # حالة الإضافة (لا يوجد بريد) - لا نظهر خيار رمز الأمان
        msg = "📭 الحساب لا يحتوي على بريد استعادة.\n\nهل تريد إضافة بريد استعادة؟"
        keyboard = [
            [InlineKeyboardButton("🔑 اضافة عبر OTP", callback_data=f'addrec_otp_{acc_id}')],
            [InlineKeyboardButton("🔙 عودة", callback_data=f'account_control_{acc_id}')]
        ]
    
    await safe_edit_message(query, msg, InlineKeyboardMarkup(keyboard))

# ===== نقطة البداية لـ OTP (تحديد إذا كانت إضافة أم تغيير) =====
async def handle_add_recovery_otp(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    query = update.callback_query
    await query.answer()
    
    acc_id = _extract_account_id(query.data)
    context.user_data['acc_id'] = acc_id
    accounts = get_user_accounts(user_id)
    account = next((acc for acc in accounts if acc['id'] == acc_id), None)
    
    if not account:
        await query.message.reply_text("⚠️ الحساب غير موجود.", reply_markup=get_main_menu(user_id))
        try:
            await query.message.delete()
        except:
            pass
        return

    access_token = get_access_token_for_account(account, user_id)
    if not access_token:
        await query.message.reply_text(get_text(user_id, 'no_access_token'), reply_markup=get_back_button(user_id, f'account_control_{acc_id}'))
        try:
            await query.message.delete()
        except:
            pass
        return

    bind_info = check_bind_info(access_token)
    current_email = bind_info.get("email") if bind_info else None

    if current_email:
        # === حالة التغيير: نرسل OTP إلى البريد القديم تلقائياً ===
        context.user_data['operation'] = 'change_recovery'
        context.user_data['old_email'] = current_email
        
        if send_otp(access_token, current_email):
            context.user_data['action'] = 'waiting_otp'
            await query.message.reply_text(
                f"📧 تم إرسال رمز OTP إلى البريد القديم:\n`{current_email}`\n\n🔑 أرسل الرمز:",
                reply_markup=get_back_button(user_id, f'account_control_{acc_id}')
            )
        else:
            await query.message.reply_text(
                "❌ فشل إرسال OTP إلى البريد القديم. تأكد من صحة البريد.",
                reply_markup=get_back_button(user_id, f'account_control_{acc_id}')
            )
        try:
            await query.message.delete()
        except:
            pass
    else:
        # === حالة الإضافة: نطلب البريد الجديد أولاً ===
        context.user_data['operation'] = 'add_recovery'
        context.user_data['action'] = 'waiting_new_email'
        await query.message.reply_text(
            "📧 أرسل البريد الإلكتروني الذي تريد ربطه:",
            reply_markup=get_back_button(user_id, f'account_control_{acc_id}')
        )
        try:
            await query.message.delete()
        except:
            pass

# ===== رمز الأمان (غير متوفر) =====
async def handle_add_recovery_sec(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    query = update.callback_query
    await query.answer()
    
    acc_id = _extract_account_id(query.data)
    await query.message.reply_text(
        "🚫 هذه الطريقة غير متوفرة حالياً.\nيمكنك استخدام طريقة **OTP** كبديل.",
        reply_markup=get_back_button(user_id, f'account_control_{acc_id}')
    )
    try:
        await query.message.delete()
    except Exception as e:
        logging.warning(f"Could not delete message: {e}")

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
        "⛓️ إلغاء ارتباط الاستعادة\n\nاختر طريقة التحقق:",
        InlineKeyboardMarkup(keyboard)
    )

# ===== نقطة البداية لإلغاء الارتباط عبر OTP =====
async def handle_unbind_otp(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    query = update.callback_query
    await query.answer()
    
    acc_id = _extract_account_id(query.data)
    context.user_data['acc_id'] = acc_id
    accounts = get_user_accounts(user_id)
    account = next((acc for acc in accounts if acc['id'] == acc_id), None)
    
    if not account:
        await query.message.reply_text("⚠️ الحساب غير موجود.", reply_markup=get_main_menu(user_id))
        try:
            await query.message.delete()
        except:
            pass
        return

    access_token = get_access_token_for_account(account, user_id)
    if not access_token:
        await query.message.reply_text(get_text(user_id, 'no_access_token'), reply_markup=get_back_button(user_id, f'account_control_{acc_id}'))
        try:
            await query.message.delete()
        except:
            pass
        return

    bind_info = check_bind_info(access_token)
    current_email = bind_info.get("email") if bind_info else None

    if not current_email:
        await query.message.reply_text(
            "❌ لا يوجد بريد استعادة لإلغاء ربطه.",
            reply_markup=get_back_button(user_id, f'account_control_{acc_id}')
        )
        try:
            await query.message.delete()
        except:
            pass
        return

    # === نرسل OTP إلى البريد الحالي تلقائياً (مثل السكريبت) ===
    context.user_data['operation'] = 'unbind_recovery'
    context.user_data['old_email'] = current_email
    
    if send_otp(access_token, current_email):
        context.user_data['action'] = 'waiting_otp'
        await query.message.reply_text(
            f"📧 تم إرسال رمز OTP إلى البريد المرتبط:\n`{current_email}`\n\n🔑 أرسل الرمز:",
            reply_markup=get_back_button(user_id, f'account_control_{acc_id}')
        )
    else:
        await query.message.reply_text(
            "❌ فشل إرسال OTP. تأكد من صحة البريد.",
            reply_markup=get_back_button(user_id, f'account_control_{acc_id}')
        )
    try:
        await query.message.delete()
    except:
        pass

# ===== رمز الأمان لإلغاء الارتباط (غير متوفر) =====
async def handle_unbind_sec(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    query = update.callback_query
    await query.answer()
    
    acc_id = _extract_account_id(query.data)
    await query.message.reply_text(
        "🚫 هذه الطريقة غير متوفرة حالياً.\nيمكنك استخدام طريقة **OTP** كبديل.",
        reply_markup=get_back_button(user_id, f'account_control_{acc_id}')
    )
    try:
        await query.message.delete()
    except Exception as e:
        logging.warning(f"Could not delete message: {e}")

# ================================================================
# ========== الخدمات غير المتوفرة ==========
# ================================================================

async def handle_try_otp(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    query = update.callback_query
    await query.answer()
    acc_id = _extract_account_id(query.data)
    await safe_edit_message(
        query,
        "🚧 هذه الخدمة ستتوفر قريباً إن شاء الله.\nترقبوا التحديثات! ✨",
        get_back_button(user_id, f'account_control_{acc_id}')
    )

async def handle_bot_otp(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    query = update.callback_query
    await query.answer()
    acc_id = _extract_account_id(query.data)
    await safe_edit_message(
        query,
        "🚧 هذه الخدمة ستتوفر قريباً إن شاء الله.\nترقبوا التحديثات! ✨",
        get_back_button(user_id, f'account_control_{acc_id}')
    )

async def handle_delete_links(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    query = update.callback_query
    await query.answer()
    acc_id = _extract_account_id(query.data)
    await safe_edit_message(
        query,
        "🚧 هذه الخدمة ستتوفر قريباً إن شاء الله.\nترقبوا التحديثات! ✨",
        get_back_button(user_id, f'account_control_{acc_id}')
    )

async def handle_spam_login(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    query = update.callback_query
    await query.answer()
    acc_id = _extract_account_id(query.data)
    await safe_edit_message(
        query,
        "🚧 هذه الخدمة ستتوفر قريباً إن شاء الله.\nترقبوا التحديثات! ✨",
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
            update_account_token(user_id, acc_id, None, 0)
            await wait_msg.edit_text("🔥 تم حرق التوكن وإبطاله بنجاح (تم تسجيل الخروج).", reply_markup=get_back_button(user_id, f'account_control_{acc_id}'))
        else:
            await wait_msg.edit_text("❌ فشل حرق التوكن. تأكد من صحة التوكن.", reply_markup=get_back_button(user_id, f'account_control_{acc_id}'))
    except Exception as e:
        logging.error(f"handle_burn_token error: {e}")
        await wait_msg.edit_text(f"❌ حدث خطأ: {str(e)[:100]}", reply_markup=get_back_button(user_id, f'account_control_{acc_id}'))

# ================================================================
# ========== معالجات الإدخال ==========
# ================================================================

# ===== معالج البريد الجديد (للإضافة) =====
async def handle_new_email_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    new_email = update.message.text.strip()
    acc_id = context.user_data.get('acc_id')
    operation = context.user_data.get('operation')
    
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

    # === حالة الإضافة: نرسل OTP إلى البريد الجديد مباشرة ===
    if operation == 'add_recovery':
        if send_otp(access_token, new_email):
            context.user_data['new_email'] = new_email
            context.user_data['action'] = 'waiting_otp'
            context.user_data['operation'] = 'add_recovery_verify'
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
        return

    # === حالة غير معروفة ===
    else:
        await update.message.reply_text("⚠️ عملية غير معروفة، أعد المحاولة من البداية.")
        context.user_data['action'] = None

# ===== معالج OTP الرئيسي =====
async def handle_otp_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    otp = update.message.text.strip()
    acc_id = context.user_data.get('acc_id')
    operation = context.user_data.get('operation')
    old_email = context.user_data.get('old_email')
    new_email = context.user_data.get('new_email')
    
    if not acc_id or not otp:
        await update.message.reply_text("⚠️ انتهت الجلسة أو OTP فارغ، أعد المحاولة.")
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

    # === 1. إلغاء الارتباط ===
    if operation == 'unbind_recovery':
        identity_token = verify_identity_otp(access_token, old_email, otp)
        if identity_token:
            if create_unbind_request(access_token, identity_token):
                await update.message.reply_text(
                    f"✅ تم إلغاء ربط بريد الاستعادة بنجاح!\n📧 البريد: `{old_email}`",
                    reply_markup=get_back_button(user_id, f'account_control_{acc_id}')
                )
            else:
                await update.message.reply_text(
                    "❌ فشل إلغاء الربط.",
                    reply_markup=get_back_button(user_id, f'account_control_{acc_id}')
                )
        else:
            await update.message.reply_text(
                "❌ فشل التحقق من OTP. تأكد من الرمز أو أعد المحاولة.",
                reply_markup=get_back_button(user_id, f'account_control_{acc_id}')
            )
        context.user_data['action'] = None
        return

    # === 2. تغيير الاستعادة - الخطوة الأولى (OTP القديم) ===
    if operation == 'change_recovery':
        identity_token = verify_identity_otp(access_token, old_email, otp)
        if identity_token:
            context.user_data['identity_token'] = identity_token
            # نطلب البريد الجديد
            context.user_data['action'] = 'waiting_new_email'
            context.user_data['operation'] = 'change_recovery'  # نبقيه كما هو
            await update.message.reply_text(
                "✅ تم التحقق من OTP القديم بنجاح!\n\n📧 أرسل البريد الإلكتروني الجديد الذي تريد ربطه:",
                reply_markup=get_back_button(user_id, f'account_control_{acc_id}')
            )
        else:
            await update.message.reply_text(
                "❌ OTP القديم غير صحيح أو منتهي الصلاحية.",
                reply_markup=get_back_button(user_id, f'account_control_{acc_id}')
            )
            context.user_data['action'] = None
        return

    # === 3. إضافة استعادة (التحقق من OTP للبريد الجديد) ===
    if operation == 'add_recovery_verify':
        verifier_token = verify_otp(access_token, new_email, otp)
        if verifier_token:
            context.user_data['verifier_token'] = verifier_token
            context.user_data['action'] = 'waiting_secondary_password'
            context.user_data['operation'] = 'finalize_add_recovery'
            await update.message.reply_text(
                "✅ تم التحقق من OTP بنجاح!\n🔐 أرسل كلمة المرور الثانوية (security_code):",
                reply_markup=get_back_button(user_id, f'account_control_{acc_id}')
            )
        else:
            await update.message.reply_text(
                "❌ OTP غير صحيح أو منتهي الصلاحية.",
                reply_markup=get_back_button(user_id, f'account_control_{acc_id}')
            )
            context.user_data['action'] = None
        return

    # === 4. تغيير الاستعادة - الخطوة الثانية (التحقق من OTP الجديد) ===
    if operation == 'change_recovery_new_email':
        verifier_token = verify_otp(access_token, new_email, otp)
        if verifier_token:
            identity_token = context.user_data.get('identity_token')
            if identity_token and create_rebind_request(access_token, identity_token, verifier_token, new_email):
                await update.message.reply_text(
                    f"✅ تم تغيير بريد الاستعادة بنجاح!\n📧 القديم: `{old_email}`\n📧 الجديد: `{new_email}`",
                    reply_markup=get_back_button(user_id, f'account_control_{acc_id}')
                )
            else:
                await update.message.reply_text(
                    "❌ فشل تغيير البريد. تأكد من البيانات.",
                    reply_markup=get_back_button(user_id, f'account_control_{acc_id}')
                )
        else:
            await update.message.reply_text(
                "❌ OTP للبريد الجديد غير صحيح.",
                reply_markup=get_back_button(user_id, f'account_control_{acc_id}')
            )
        context.user_data['action'] = None
        return

    # === أي حالة أخرى ===
    await update.message.reply_text("⚠️ عملية غير معروفة، أعد المحاولة من البداية.")
    context.user_data['action'] = None

# ===== معالج كلمة المرور الثانوية (لإضافة الاستعادة) =====
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

    if operation == 'finalize_add_recovery':
        # نتحقق مرة أخرى من عدم وجود بريد مسبقاً (احتياطاً)
        bind_info = check_bind_info(access_token)
        if bind_info and bind_info.get('email'):
            await update.message.reply_text(
                "⚠️ الحساب مربوط بالفعل ببريد! استخدم خدمة التغيير.",
                reply_markup=get_back_button(user_id, f'account_control_{acc_id}')
            )
            context.user_data['action'] = None
            return

        if create_bind_request(access_token, new_email, verifier_token, sec_code):
            await update.message.reply_text(
                f"✅ تم ربط بريد الاستعادة بنجاح!\n📧 البريد: `{new_email}`",
                reply_markup=get_back_button(user_id, f'account_control_{acc_id}')
            )
        else:
            await update.message.reply_text(
                "❌ فشل الربط. تأكد من صحة كلمة المرور الثانوية.",
                reply_markup=get_back_button(user_id, f'account_control_{acc_id}')
            )
        context.user_data['action'] = None
        return

    await update.message.reply_text("⚠️ عملية غير معروفة، أعد المحاولة من البداية.")
    context.user_data['action'] = None

# ===== دالة إضافية للتوافق (لمعالجة wait_unbind_input) =====
async def handle_unbind_otp_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await handle_otp_input(update, context)

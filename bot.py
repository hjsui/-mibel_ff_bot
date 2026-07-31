# -*- coding: utf-8 -*-

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler, ContextTypes

from config import BOT_TOKEN
from database import db, save_db
from utils import get_text, user_data_store
from handlers.main_menu import start, button_handler, get_main_menu, get_back_button
from handlers.account_services import (
    # الخدمات الأساسية
    handle_add_account, handle_manage_account, handle_my_accounts,
    handle_recovery, handle_links, handle_otp, handle_try_otp,
    handle_add_recovery, handle_burn_token,
    handle_spam_login, handle_account_selection, handle_account_control,
    handle_delete_account, handle_otp_input, handle_email_input,
    handle_secondary_password_input, handle_unbind_input,
    # الخدمات الجديدة (المصححة)
    handle_change_bind_otp, handle_change_bind_otp_input,
    handle_change_bind_sec, handle_change_bind_sec_input,
    handle_unbind_otp, handle_unbind_otp_input,
    handle_unbind_sec, handle_unbind_sec_input,
    handle_cancel_bind, handle_login_history, handle_bound_accounts_detailed,
    handle_ban, handle_ban_start, handle_ban_stop
)
from handlers.new_services import (
    handle_friend_start, handle_friend_input, handle_ban as handle_ban_check
)
from handlers.auth_handlers import (
    handle_buy_now, handle_use_code, handle_services_explain,
    handle_customer_service, handle_bot_group, handle_code_input
)

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# ========== معالج الأخطاء العالمي ==========
async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        raise context.error
    except Exception as e:
        error_msg = str(e)
        if "NameResolutionError" in error_msg or "Failed to resolve" in error_msg:
            friendly_msg = "⚠️ الخادم غير متصل حالياً. حاول مرة أخرى لاحقاً."
        elif "Timeout" in error_msg or "timed out" in error_msg:
            friendly_msg = "⏳ انتهت مهلة الاتصال. الخادم بطيء، حاول مجدداً."
        elif "Conflict" in error_msg:
            friendly_msg = "⚠️ يوجد نسخة أخرى من البوت تعمل. انتظر قليلاً."
        elif "BadRequest" in error_msg:
            friendly_msg = "⚠️ طلب غير صحيح. تأكد من البيانات المدخلة."
        elif "HTTPSConnectionPool" in error_msg:
            friendly_msg = "⚠️ الخادم غير متاح. حاول مرة أخرى لاحقاً."
        elif "ConnectionError" in error_msg:
            friendly_msg = "⚠️ لا يوجد اتصال بالإنترنت. تأكد من اتصالك."
        elif "JSONDecodeError" in error_msg:
            friendly_msg = "⚠️ حدث خطأ في قراءة البيانات. حاول مرة أخرى."
        else:
            friendly_msg = f"❌ حدث خطأ غير متوقع: {error_msg[:80]}..."
        if update and update.effective_message:
            try:
                await update.effective_message.reply_text(friendly_msg)
            except:
                pass
        elif update and update.callback_query:
            try:
                await update.callback_query.message.reply_text(friendly_msg)
            except:
                pass

# ========== أمر الأدمن (/meow) ==========
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if str(user_id) != "8530485909":
        await update.message.reply_text("⛔ هذا الأمر مخصص للأدمن فقط.")
        return
    keyboard = [
        [InlineKeyboardButton("👥 قائمة المستخدمين", callback_data='admin_users')],
        [InlineKeyboardButton("🎫 إدارة الأكواد", callback_data='admin_codes')],
        [InlineKeyboardButton("➕ توليد كود", callback_data='admin_gen_code')],
        [InlineKeyboardButton("🔙 عودة", callback_data='main_menu')]
    ]
    await update.message.reply_text("⚙️ **لوحة تحكم الأدمن**\n\nاختر الإجراء المطلوب:", reply_markup=InlineKeyboardMarkup(keyboard))

async def admin_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id
    if str(user_id) != "8530485909":
        await query.edit_message_text("⛔ غير مصرح.")
        return
    data = query.data
    if data == 'admin_users':
        users = db.get_all_users()
        if not users:
            await query.edit_message_text("📭 لا يوجد مستخدمين مسجلين.")
            return
        text = "👥 **قائمة المستخدمين:**\n\n"
        for uid, info in users.items():
            status = "✅ مفعل" if info.get('subscribed') else "❌ غير مفعل"
            expiry = info.get('expiry', 'غير محدد')
            text += f"• `{uid}` - {status} (ينتهي: {expiry})\n"
        await query.edit_message_text(text, reply_markup=get_back_button(user_id, 'admin_panel'))
    elif data == 'admin_codes':
        codes = db.get_all_codes()
        if not codes:
            await query.edit_message_text("📭 لا توجد أكواد.")
            return
        text = "🎫 **الأكواد المتاحة:**\n\n"
        for code, info in codes.items():
            used = "✅ مستخدم" if info.get('used') else "❌ غير مستخدم"
            text += f"• `{code}` - {used}\n"
        await query.edit_message_text(text, reply_markup=get_back_button(user_id, 'admin_panel'))
    elif data == 'admin_gen_code':
        import random, string
        new_code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=12))
        db.data['codes'][new_code] = {'used': False, 'plan': 'lifetime', 'generated_by': str(user_id), 'used_by': None}
        save_db(db.data)
        await query.edit_message_text(f"✅ تم توليد كود جديد:\n\n`{new_code}`\n\nيمكن للمستخدمين استخدامه عبر زر 'استخدام كود'.", reply_markup=get_back_button(user_id, 'admin_panel'))
    elif data == 'admin_panel':
        keyboard = [
            [InlineKeyboardButton("👥 قائمة المستخدمين", callback_data='admin_users')],
            [InlineKeyboardButton("🎫 إدارة الأكواد", callback_data='admin_codes')],
            [InlineKeyboardButton("➕ توليد كود", callback_data='admin_gen_code')],
            [InlineKeyboardButton("🔙 عودة", callback_data='main_menu')]
        ]
        await query.edit_message_text("⚙️ **لوحة تحكم الأدمن**", reply_markup=InlineKeyboardMarkup(keyboard))

# ========== معالجات النصوص العامة ==========
async def handle_text_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    action = context.user_data.get('action')
    
    if action == 'waiting_otp':
        await handle_otp_input(update, context)
    elif action == 'waiting_email':
        await handle_email_input(update, context)
    elif action == 'waiting_secondary_password':
        await handle_secondary_password_input(update, context)
    elif action == 'waiting_unbind_input':
        await handle_unbind_input(update, context)
    elif action == 'waiting_friend_uid':
        await handle_friend_input(update, context)
    elif action == 'waiting_code':
        await handle_code_input(update, context)
    elif action == 'waiting_change_bind_otp':
        await handle_change_bind_otp_input(update, context)
    elif action == 'waiting_change_bind_sec':
        await handle_change_bind_sec_input(update, context)
    elif action == 'waiting_unbind_otp':
        await handle_unbind_otp_input(update, context)
    elif action == 'waiting_unbind_sec':
        await handle_unbind_sec_input(update, context)
    else:
        await handle_add_account(update, context)

# ========== الوظيفة الرئيسية ==========
def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_error_handler(error_handler)
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("meow", admin_panel))
    
    # ===== أزرار القائمة الرئيسية =====
    app.add_handler(CallbackQueryHandler(button_handler, pattern='^(main_menu|add_account|my_accounts|terms|change_lang|lang_ar|lang_en|manage_account)$'))
    
    # ===== معالجات الحسابات الأساسية =====
    app.add_handler(CallbackQueryHandler(handle_account_selection, pattern='^control_'))
    app.add_handler(CallbackQueryHandler(handle_account_control, pattern='^account_control_'))
    app.add_handler(CallbackQueryHandler(handle_delete_account, pattern='^del_'))
    
    # ===== معالجات الخدمات الأساسية =====
    app.add_handler(CallbackQueryHandler(handle_recovery, pattern='^recovery_'))
    app.add_handler(CallbackQueryHandler(handle_links, pattern='^links_'))
    app.add_handler(CallbackQueryHandler(handle_otp, pattern='^otp_'))
    app.add_handler(CallbackQueryHandler(handle_try_otp, pattern='^tryotp_'))
    app.add_handler(CallbackQueryHandler(handle_add_recovery, pattern='^addrec_'))
    app.add_handler(CallbackQueryHandler(handle_burn_token, pattern='^burn_'))
    app.add_handler(CallbackQueryHandler(handle_spam_login, pattern='^spam_'))
    
    # ===== الخدمات المتبقية =====
    app.add_handler(CallbackQueryHandler(handle_friend_start, pattern='^friend_'))
    app.add_handler(CallbackQueryHandler(handle_ban_check, pattern='^bancheck_'))
    
    # ===== الخدمات الجديدة (المصححة) =====
    app.add_handler(CallbackQueryHandler(handle_change_bind_otp, pattern='^change_bind_otp_'))
    app.add_handler(CallbackQueryHandler(handle_change_bind_sec, pattern='^change_bind_sec_'))
    app.add_handler(CallbackQueryHandler(handle_unbind_otp, pattern='^unbind_otp_'))
    app.add_handler(CallbackQueryHandler(handle_unbind_sec, pattern='^unbind_sec_'))
    app.add_handler(CallbackQueryHandler(handle_cancel_bind, pattern='^cancel_bind_'))
    app.add_handler(CallbackQueryHandler(handle_login_history, pattern='^login_history_'))
    app.add_handler(CallbackQueryHandler(handle_bound_accounts_detailed, pattern='^bound_accounts_'))
    app.add_handler(CallbackQueryHandler(handle_ban, pattern='^ban_'))
    app.add_handler(CallbackQueryHandler(handle_ban_start, pattern='^ban_start_'))
    app.add_handler(CallbackQueryHandler(handle_ban_stop, pattern='^ban_stop_'))
    
    # ===== معالجات المصادقة والاشتراكات =====
    app.add_handler(CallbackQueryHandler(handle_buy_now, pattern='^buy_now$'))
    app.add_handler(CallbackQueryHandler(handle_use_code, pattern='^use_code$'))
    app.add_handler(CallbackQueryHandler(handle_services_explain, pattern='^services_explain$'))
    app.add_handler(CallbackQueryHandler(handle_customer_service, pattern='^customer_service$'))
    app.add_handler(CallbackQueryHandler(handle_bot_group, pattern='^bot_group$'))
    
    # ===== معالجات الأدمن =====
    app.add_handler(CallbackQueryHandler(admin_buttons, pattern='^admin_'))
    
    # ===== معالج النصوص =====
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_input))
    
    print("🤖 البوت شغال... اضغط Ctrl+C لإيقافه.")
    app.run_polling()

if __name__ == "__main__":
    main()

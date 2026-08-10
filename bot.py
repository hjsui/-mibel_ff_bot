# -*- coding: utf-8 -*-

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler, ContextTypes

from config import BOT_TOKEN
from database import db, save_db
from utils import get_text
from handlers.main_menu import start, button_handler, get_main_menu, get_back_button
from handlers.account_services import (
    handle_add_account, handle_manage_account, handle_my_accounts,
    handle_recovery, handle_links, handle_try_otp, handle_spam_login,
    handle_burn_token,
    handle_add_recovery, handle_add_recovery_otp, handle_add_recovery_sec,
    handle_unbind, handle_unbind_otp, handle_unbind_sec,
    handle_unbind_confirm,  # <-- مهم
    handle_bot_otp, handle_delete_links,
    handle_account_selection, handle_account_control, handle_delete_account,
    handle_otp_input, handle_secondary_password_input, handle_unbind_otp_input,
    handle_new_email_input
)
from handlers.auth_handlers import (
    handle_buy_now, handle_use_code, handle_services_explain,
    handle_customer_service, handle_bot_group, handle_code_input
)

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

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
    await update.message.reply_text("⚙️ لوحة تحكم الأدمن\n\nاختر الإجراء المطلوب:", reply_markup=InlineKeyboardMarkup(keyboard))

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
        text = "👥 قائمة المستخدمين:\n\n"
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
        text = "🎫 الأكواد المتاحة:\n\n"
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
        await query.edit_message_text("⚙️ لوحة تحكم الأدمن", reply_markup=InlineKeyboardMarkup(keyboard))

async def handle_text_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    action = context.user_data.get('action')
    
    if action == 'waiting_otp':
        await handle_otp_input(update, context)
    elif action == 'waiting_email':
        await update.message.reply_text("⚠️ هذه الخدمة غير متوفرة حالياً.")
        context.user_data['action'] = None
    elif action == 'waiting_secondary_password':
        await handle_secondary_password_input(update, context)
    elif action == 'waiting_unbind_input':
        await handle_unbind_otp_input(update, context)
    elif action == 'waiting_code':
        await handle_code_input(update, context)
    elif action == 'waiting_new_email':
        await handle_new_email_input(update, context)
    else:
        await handle_add_account(update, context)

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_error_handler(error_handler)
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("meow", admin_panel))
    
    app.add_handler(CallbackQueryHandler(button_handler, pattern='^(main_menu|add_account|my_accounts|terms|change_lang|lang_ar|lang_en|manage_account)$'))
    
    app.add_handler(CallbackQueryHandler(handle_account_selection, pattern='^control_'))
    app.add_handler(CallbackQueryHandler(handle_account_control, pattern='^account_control_'))
    app.add_handler(CallbackQueryHandler(handle_delete_account, pattern='^del_'))
    
    app.add_handler(CallbackQueryHandler(handle_recovery, pattern='^recovery_'))
    app.add_handler(CallbackQueryHandler(handle_links, pattern='^links_'))
    app.add_handler(CallbackQueryHandler(handle_try_otp, pattern='^tryotp_'))
    app.add_handler(CallbackQueryHandler(handle_spam_login, pattern='^spam_'))
    app.add_handler(CallbackQueryHandler(handle_burn_token, pattern='^burn_'))
    
    app.add_handler(CallbackQueryHandler(handle_add_recovery, pattern='^addrec_'))
    app.add_handler(CallbackQueryHandler(handle_add_recovery_otp, pattern='^addrec_otp_'))
    app.add_handler(CallbackQueryHandler(handle_add_recovery_sec, pattern='^addrec_sec_'))
    
    app.add_handler(CallbackQueryHandler(handle_unbind, pattern='^unbind_'))
    app.add_handler(CallbackQueryHandler(handle_unbind_otp, pattern='^unbind_otp_'))
    app.add_handler(CallbackQueryHandler(handle_unbind_sec, pattern='^unbind_sec_'))
    app.add_handler(CallbackQueryHandler(handle_unbind_confirm, pattern='^unbind_confirm_'))  # <-- مهم
    
    app.add_handler(CallbackQueryHandler(handle_bot_otp, pattern='^bototp_'))
    app.add_handler(CallbackQueryHandler(handle_delete_links, pattern='^dellinks_'))
    
    app.add_handler(CallbackQueryHandler(handle_buy_now, pattern='^buy_now$'))
    app.add_handler(CallbackQueryHandler(handle_use_code, pattern='^use_code$'))
    app.add_handler(CallbackQueryHandler(handle_services_explain, pattern='^services_explain$'))
    app.add_handler(CallbackQueryHandler(handle_customer_service, pattern='^customer_service$'))
    app.add_handler(CallbackQueryHandler(handle_bot_group, pattern='^bot_group$'))
    
    app.add_handler(CallbackQueryHandler(admin_buttons, pattern='^admin_'))
    
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_input))
    
    print("🤖 البوت شغال... اضغط Ctrl+C لإيقافه.")
    app.run_polling()

if __name__ == "__main__":
    main()

# -*- coding: utf-8 -*-

import logging
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler
from config import BOT_TOKEN, ADMIN_IDS
from handlers.main_menu import start, button_handler
from handlers.account_services import (
    handle_add_account, handle_manage_account, handle_my_accounts,
    handle_recovery, handle_links, handle_otp, handle_try_otp,
    handle_add_recovery, handle_delete_links, handle_burn_token,
    handle_spam_login, handle_account_selection, handle_account_control,
    handle_delete_account, handle_otp_input, handle_email_input,
    handle_secondary_password_input, handle_unbind_input
)
from handlers.new_services import (
    handle_visit, handle_nickname_start, handle_nickname_input,
    handle_guild_start, handle_guild_action, handle_clan_id_input,
    handle_friend_start, handle_friend_input, handle_ban,
    handle_events, handle_wishlist
)
from handlers.auth_handlers import (
    handle_buy_now, handle_use_code, handle_services_explain,
    handle_customer_service, handle_bot_group, handle_code_input
)
from database import db

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

def main():
    # إنشاء التطبيق
    app = Application.builder().token(BOT_TOKEN).build()
    
    # ========== معالجات الأوامر ==========
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", handle_admin_panel))
    
    # ========== معالجات الأزرار العامة ==========
    app.add_handler(CallbackQueryHandler(button_handler, pattern='^(main_menu|manage_account|add_account|my_accounts|terms|change_lang|buy_now|use_code|services_explain|customer_service|bot_group)$'))
    
    # ========== معالجات الحسابات ==========
    app.add_handler(CallbackQueryHandler(handle_account_selection, pattern='^control_'))
    app.add_handler(CallbackQueryHandler(handle_account_control, pattern='^account_control_'))
    app.add_handler(CallbackQueryHandler(handle_delete_account, pattern='^del_'))
    
    # ========== معالجات الخدمات الأساسية ==========
    app.add_handler(CallbackQueryHandler(handle_recovery, pattern='^recovery_'))
    app.add_handler(CallbackQueryHandler(handle_links, pattern='^links_'))
    app.add_handler(CallbackQueryHandler(handle_otp, pattern='^otp_'))
    app.add_handler(CallbackQueryHandler(handle_try_otp, pattern='^tryotp_'))
    app.add_handler(CallbackQueryHandler(handle_add_recovery, pattern='^addrec_'))
    app.add_handler(CallbackQueryHandler(handle_delete_links, pattern='^dellinks_'))
    app.add_handler(CallbackQueryHandler(handle_burn_token, pattern='^burn_'))
    app.add_handler(CallbackQueryHandler(handle_spam_login, pattern='^spam_'))
    
    # ========== معالجات الخدمات الجديدة ==========
    app.add_handler(CallbackQueryHandler(handle_visit, pattern='^visit_'))
    app.add_handler(CallbackQueryHandler(handle_nickname_start, pattern='^nick_'))
    app.add_handler(CallbackQueryHandler(handle_guild_start, pattern='^guild_'))
    app.add_handler(CallbackQueryHandler(handle_guild_action, pattern='^guild_(join|leave)_'))
    app.add_handler(CallbackQueryHandler(handle_friend_start, pattern='^friend_'))
    app.add_handler(CallbackQueryHandler(handle_ban, pattern='^ban_'))
    app.add_handler(CallbackQueryHandler(handle_events, pattern='^events_'))
    app.add_handler(CallbackQueryHandler(handle_wishlist, pattern='^wishlist_'))
    
    # ========== معالجات المصادقة والاشتراكات ==========
    app.add_handler(CallbackQueryHandler(handle_buy_now, pattern='^buy_now$'))
    app.add_handler(CallbackQueryHandler(handle_use_code, pattern='^use_code$'))
    app.add_handler(CallbackQueryHandler(handle_services_explain, pattern='^services_explain$'))
    app.add_handler(CallbackQueryHandler(handle_customer_service, pattern='^customer_service$'))
    app.add_handler(CallbackQueryHandler(handle_bot_group, pattern='^bot_group$'))
    
    # ========== معالجات إدخال النصوص ==========
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_input))
    
    print("🤖 البوت شغال... اضغط Ctrl+C لإيقافه.")
    app.run_polling()

async def handle_admin_panel(update, context):
    """لوحة تحكم الأدمن (للمطورين فقط)"""
    user_id = update.effective_user.id
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("⛔ هذا الأمر مخصص للأدمن فقط.")
        return
    
    from handlers.auth_handlers import show_admin_panel
    await show_admin_panel(update, context)

async def handle_text_input(update, context):
    """معالجة جميع الإدخالات النصية (OTP، إيميل، كود، الخ)"""
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
    elif action == 'waiting_new_nickname':
        await handle_nickname_input(update, context)
    elif action == 'waiting_clan_id':
        await handle_clan_id_input(update, context)
    elif action == 'waiting_friend_uid':
        await handle_friend_input(update, context)
    elif action == 'waiting_code':
        await handle_code_input(update, context)
    elif action == 'waiting_add_account':
        await handle_add_account(update, context)
    else:
        # أي نص آخر (مثل إضافة حساب عبر EAT)
        await handle_add_account(update, context)

if __name__ == "__main__":
    main()

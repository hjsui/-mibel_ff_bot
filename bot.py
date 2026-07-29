# -*- coding: utf-8 -*-

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler, ContextTypes

from config import BOT_TOKEN, ADMIN_IDS
from database import db, save_db
from utils import get_text, user_data_store
from handlers.main_menu import start, button_handler, get_main_menu, get_back_button
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

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# ========== أمر الأدمن (/meow) ==========
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """لوحة تحكم الأدمن - للمطور فقط"""
    user_id = update.effective_user.id
    
    # التحقق من أن المستخدم هو المطور
    if str(user_id) != "8530485909":
        await update.message.reply_text("⛔ هذا الأمر مخصص للأدمن فقط.")
        return
    
    # عرض لوحة التحكم
    keyboard = [
        [InlineKeyboardButton("👥 قائمة المستخدمين", callback_data='admin_users')],
        [InlineKeyboardButton("🎫 إدارة الأكواد", callback_data='admin_codes')],
        [InlineKeyboardButton("➕ توليد كود", callback_data='admin_gen_code')],
        [InlineKeyboardButton("🔙 عودة", callback_data='main_menu')]
    ]
    
    await update.message.reply_text(
        "⚙️ **لوحة تحكم الأدمن**\n\n"
        "اختر الإجراء المطلوب:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ========== معالجات أزرار الأدمن ==========
async def admin_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة أزرار لوحة تحكم الأدمن"""
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id
    
    if str(user_id) != "8530485909":
        await query.edit_message_text("⛔ غير مصرح.")
        return
    
    data = query.data
    
    if data == 'admin_users':
        # عرض قائمة المستخدمين
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
        # عرض الأكواد
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
        # توليد كود جديد
        import random
        import string
        new_code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=12))
        db.data['codes'][new_code] = {
            'used': False,
            'plan': 'lifetime',
            'generated_by': str(user_id),
            'used_by': None
        }
        save_db(db.data)
        
        await query.edit_message_text(
            f"✅ تم توليد كود جديد:\n\n`{new_code}`\n\n"
            "يمكن للمستخدمين استخدامه عبر زر 'استخدام كود'.",
            reply_markup=get_back_button(user_id, 'admin_panel')
        )
    
    elif data == 'admin_panel':
        # العودة للوحة الأدمن
        keyboard = [
            [InlineKeyboardButton("👥 قائمة المستخدمين", callback_data='admin_users')],
            [InlineKeyboardButton("🎫 إدارة الأكواد", callback_data='admin_codes')],
            [InlineKeyboardButton("➕ توليد كود", callback_data='admin_gen_code')],
            [InlineKeyboardButton("🔙 عودة", callback_data='main_menu')]
        ]
        await query.edit_message_text(
            "⚙️ **لوحة تحكم الأدمن**",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

# ========== معالجات النصوص العامة ==========
async def handle_text_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
    else:
        # أي نص آخر (مثل إضافة حساب عبر EAT)
        await handle_add_account(update, context)

# ========== الوظيفة الرئيسية ==========
def main():
    """تشغيل البوت"""
    # إنشاء التطبيق
    app = Application.builder().token(BOT_TOKEN).build()
    
    # ===== الأوامر =====
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("meow", admin_panel))
    
    # ===== أزرار القائمة الرئيسية =====
    app.add_handler(CallbackQueryHandler(button_handler, pattern='^(main_menu|manage_account|add_account|my_accounts|terms|change_lang|buy_now|use_code|services_explain|customer_service|bot_group)$'))
    
    # ===== معالجات الحسابات =====
    app.add_handler(CallbackQueryHandler(handle_account_selection, pattern='^control_'))
    app.add_handler(CallbackQueryHandler(handle_account_control, pattern='^account_control_'))
    app.add_handler(CallbackQueryHandler(handle_delete_account, pattern='^del_'))
    
    # ===== معالجات الخدمات الأساسية =====
    app.add_handler(CallbackQueryHandler(handle_recovery, pattern='^recovery_'))
    app.add_handler(CallbackQueryHandler(handle_links, pattern='^links_'))
    app.add_handler(CallbackQueryHandler(handle_otp, pattern='^otp_'))
    app.add_handler(CallbackQueryHandler(handle_try_otp, pattern='^tryotp_'))
    app.add_handler(CallbackQueryHandler(handle_add_recovery, pattern='^addrec_'))
    app.add_handler(CallbackQueryHandler(handle_delete_links, pattern='^dellinks_'))
    app.add_handler(CallbackQueryHandler(handle_burn_token, pattern='^burn_'))
    app.add_handler(CallbackQueryHandler(handle_spam_login, pattern='^spam_'))
    
    # ===== معالجات الخدمات الجديدة =====
    app.add_handler(CallbackQueryHandler(handle_visit, pattern='^visit_'))
    app.add_handler(CallbackQueryHandler(handle_nickname_start, pattern='^nick_'))
    app.add_handler(CallbackQueryHandler(handle_guild_start, pattern='^guild_'))
    app.add_handler(CallbackQueryHandler(handle_guild_action, pattern='^guild_(join|leave)_'))
    app.add_handler(CallbackQueryHandler(handle_friend_start, pattern='^friend_'))
    app.add_handler(CallbackQueryHandler(handle_ban, pattern='^ban_'))
    app.add_handler(CallbackQueryHandler(handle_events, pattern='^events_'))
    app.add_handler(CallbackQueryHandler(handle_wishlist, pattern='^wishlist_'))
    
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
    
    # تشغيل البوت
    print("🤖 البوت شغال... اضغط Ctrl+C لإيقافه.")
    app.run_polling()

if __name__ == "__main__":
    main()

# -*- coding: utf-8 -*-

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from utils import get_text, get_user_accounts, get_access_token_for_account, user_data_store, convert_eat
from external_apis import (
    visit_account, change_nickname, guild_action,
    friend_request, check_ban, get_events, get_wishlist
)
from handlers.main_menu import get_back_button, get_account_controls

# ========== زيادة زيارات الحساب ==========
async def handle_visit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    query = update.callback_query
    await query.answer()
    
    acc_id = query.data.split('_')[1]
    accounts = get_user_accounts(user_id)
    account = next((acc for acc in accounts if acc['id'] == acc_id), None)
    if not account:
        await query.edit_message_text("⚠️ الحساب غير موجود.", reply_markup=get_back_button(user_id))
        return
    
    # ✅ رسالة انتظار
    await query.edit_message_text(
        "⏳ جاري جلب معلومات الحساب... قد يستغرق هذا بضع ثوانٍ.",
        reply_markup=get_back_button(user_id, f'account_control_{acc_id}')
    )
    
    result = visit_account(account['id'], account.get('region', 'IND'))
    
    if 'error' in result:
        await query.edit_message_text(
            get_text(user_id, 'operation_failed', error=result['error']),
            reply_markup=get_back_button(user_id, f'account_control_{acc_id}')
        )
        return
    
    msg = get_text(user_id, 'visit_result',
        uid=result.get('UiD', account['id']),
        nickname=result.get('NicKnAmE', account['name']),
        region=result.get('ReGioN', account['region']),
        level=result.get('LeVeL', 'غير معروف'),
        likes=result.get('LiKeS', 'غير معروف'),
        total=result.get('ToTaL', 'غير معروف'),
        extra=f"\n💬 {result.get('CreDiT', '')}" if result.get('CreDiT') else ""
    )
    
    await query.edit_message_text(msg, reply_markup=get_back_button(user_id, f'account_control_{acc_id}'))

# ========== تغيير الاسم ==========
async def handle_nickname_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    query = update.callback_query
    await query.answer()
    
    acc_id = query.data.split('_')[1]
    context.user_data['action'] = 'waiting_new_nickname'
    context.user_data['acc_id'] = acc_id
    
    await query.edit_message_text(
        get_text(user_id, 'enter_new_nickname'),
        reply_markup=get_back_button(user_id, f'account_control_{acc_id}')
    )

async def handle_nickname_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    new_name = update.message.text.strip()
    acc_id = context.user_data.get('acc_id')
    
    if not acc_id:
        await update.message.reply_text("⚠️ انتهت الجلسة، أعد المحاولة.")
        context.user_data['action'] = None
        return
    
    if len(new_name) < 3 or len(new_name) > 12:
        await update.message.reply_text("⚠️ الاسم يجب أن يكون بين 3 و 12 حرفاً.")
        return
    
    accounts = get_user_accounts(user_id)
    account = next((acc for acc in accounts if acc['id'] == acc_id), None)
    if not account:
        await update.message.reply_text("⚠️ الحساب غير موجود.")
        context.user_data['action'] = None
        return
    
    # ✅ رسالة انتظار
    await update.message.reply_text("⏳ جاري تغيير الاسم... قد يستغرق هذا بضع ثوانٍ.")
    
    access_token = get_access_token_for_account(account)
    if not access_token:
        await update.message.reply_text(get_text(user_id, 'no_access_token'))
        context.user_data['action'] = None
        return
    
    result = change_nickname(access_token, new_name)
    
    if 'error' in result:
        await update.message.reply_text(
            get_text(user_id, 'operation_failed', error=result['error']),
            reply_markup=get_back_button(user_id, f'account_control_{acc_id}')
        )
    else:
        await update.message.reply_text(
            get_text(user_id, 'nickname_changed', new_name=new_name),
            reply_markup=get_back_button(user_id, f'account_control_{acc_id}')
        )
    
    context.user_data['action'] = None

# ========== إدارة القبيلة ==========
async def handle_guild_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    query = update.callback_query
    await query.answer()
    
    acc_id = query.data.split('_')[1]
    context.user_data['acc_id'] = acc_id
    
    keyboard = [
        [InlineKeyboardButton("✅ انضمام", callback_data=f'guild_join_{acc_id}'),
         InlineKeyboardButton("❌ مغادرة", callback_data=f'guild_leave_{acc_id}')],
        [InlineKeyboardButton("🔙 عودة", callback_data=f'account_control_{acc_id}')]
    ]
    await query.edit_message_text(
        "🏰 اختر الإجراء المطلوب:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def handle_guild_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    query = update.callback_query
    await query.answer()
    
    data = query.data
    action = 'join' if 'join' in data else 'leave'
    acc_id = data.split('_')[2]
    
    context.user_data['action'] = 'waiting_clan_id'
    context.user_data['guild_action'] = action
    context.user_data['acc_id'] = acc_id
    
    await query.edit_message_text(
        get_text(user_id, 'enter_clan_id'),
        reply_markup=get_back_button(user_id, f'account_control_{acc_id}')
    )

async def handle_clan_id_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    clan_id = update.message.text.strip()
    acc_id = context.user_data.get('acc_id')
    action = context.user_data.get('guild_action', 'join')
    
    if not acc_id:
        await update.message.reply_text("⚠️ انتهت الجلسة، أعد المحاولة.")
        context.user_data['action'] = None
        return
    
    if not clan_id.isdigit():
        await update.message.reply_text("⚠️ معرف القبيلة يجب أن يكون أرقاماً فقط.")
        return
    
    accounts = get_user_accounts(user_id)
    account = next((acc for acc in accounts if acc['id'] == acc_id), None)
    if not account:
        await update.message.reply_text("⚠️ الحساب غير موجود.")
        context.user_data['action'] = None
        return
    
    # ✅ رسالة انتظار
    await update.message.reply_text("⏳ جاري معالجة طلب القبيلة... قد يستغرق هذا بضع ثوانٍ.")
    
    jwt_data = convert_eat(account['eat'], "eat_to_jwt")
    if not jwt_data.get("success"):
        await update.message.reply_text("❌ فشل الحصول على JWT.")
        context.user_data['action'] = None
        return
    
    jwt_token = jwt_data.get("result_token")
    result = guild_action(action, clan_id, jwt_token)
    
    if 'error' in result:
        await update.message.reply_text(
            get_text(user_id, 'operation_failed', error=result['error']),
            reply_markup=get_back_button(user_id, f'account_control_{acc_id}')
        )
    else:
        msg = get_text(user_id, 'guild_joined' if action == 'join' else 'guild_left', clan_id=clan_id)
        await update.message.reply_text(msg, reply_markup=get_back_button(user_id, f'account_control_{acc_id}'))
    
    context.user_data['action'] = None

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
    
    # ✅ رسالة انتظار
    await update.message.reply_text("⏳ جاري إرسال طلب الصداقة... قد يستغرق هذا بضع ثوانٍ.")
    
    access_token = get_access_token_for_account(account)
    if not access_token:
        await update.message.reply_text(get_text(user_id, 'no_access_token'))
        context.user_data['action'] = None
        return
    
    result = friend_request(target_uid, access_token, "add")
    
    if 'error' in result:
        await update.message.reply_text(
            get_text(user_id, 'operation_failed', error=result['error']),
            reply_markup=get_back_button(user_id, f'account_control_{acc_id}')
        )
    else:
        await update.message.reply_text(
            get_text(user_id, 'friend_sent', uid=target_uid),
            reply_markup=get_back_button(user_id, f'account_control_{acc_id}')
        )
    
    context.user_data['action'] = None

# ========== فحص الحظر ==========
async def handle_ban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    query = update.callback_query
    await query.answer()
    
    acc_id = query.data.split('_')[1]
    accounts = get_user_accounts(user_id)
    account = next((acc for acc in accounts if acc['id'] == acc_id), None)
    if not account:
        await query.edit_message_text("⚠️ الحساب غير موجود.", reply_markup=get_back_button(user_id))
        return
    
    # ✅ رسالة انتظار
    await query.edit_message_text(
        "⏳ جاري فحص الحظر... قد يستغرق هذا بضع ثوانٍ.",
        reply_markup=get_back_button(user_id, f'account_control_{acc_id}')
    )
    
    access_token = get_access_token_for_account(account)
    if not access_token:
        await query.edit_message_text(
            get_text(user_id, 'no_access_token'),
            reply_markup=get_back_button(user_id, f'account_control_{acc_id}')
        )
        return
    
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
    
    await query.edit_message_text(msg, reply_markup=get_back_button(user_id, f'account_control_{acc_id}'))

# ========== أحداث اللعبة ==========
async def handle_events(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    query = update.callback_query
    await query.answer()
    
    acc_id = query.data.split('_')[1]
    accounts = get_user_accounts(user_id)
    account = next((acc for acc in accounts if acc['id'] == acc_id), None)
    if not account:
        await query.edit_message_text("⚠️ الحساب غير موجود.", reply_markup=get_back_button(user_id))
        return
    
    # ✅ رسالة انتظار
    await query.edit_message_text(
        "⏳ جاري جلب أحداث اللعبة... قد يستغرق هذا بضع ثوانٍ.",
        reply_markup=get_back_button(user_id, f'account_control_{acc_id}')
    )
    
    result = get_events(account.get('region', 'IND'))
    
    if 'error' in result:
        msg = get_text(user_id, 'operation_failed', error=result['error'])
    else:
        events_text = ""
        for event in result.get('events', []):
            events_text += f"• **{event.get('name', 'غير معروف')}**\n"
            events_text += f"  📅 {event.get('date', 'غير محدد')}\n"
            events_text += f"  📝 {event.get('description', '')}\n\n"
        
        if not events_text:
            events_text = "لا توجد أحداث حالياً."
        
        msg = get_text(user_id, 'events_result', events=events_text)
    
    await query.edit_message_text(msg, reply_markup=get_back_button(user_id, f'account_control_{acc_id}'))

# ========== قائمة الرغبات ==========
async def handle_wishlist(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    query = update.callback_query
    await query.answer()
    
    acc_id = query.data.split('_')[1]
    accounts = get_user_accounts(user_id)
    account = next((acc for acc in accounts if acc['id'] == acc_id), None)
    if not account:
        await query.edit_message_text("⚠️ الحساب غير موجود.", reply_markup=get_back_button(user_id))
        return
    
    # ✅ رسالة انتظار
    await query.edit_message_text(
        "⏳ جاري جلب قائمة الرغبات... قد يستغرق هذا بضع ثوانٍ.",
        reply_markup=get_back_button(user_id, f'account_control_{acc_id}')
    )
    
    result = get_wishlist(account['id'], account.get('region', 'IND'))
    
    if 'error' in result:
        msg = get_text(user_id, 'operation_failed', error=result['error'])
    else:
        wishlist_items = result.get('wishlist', [])
        if wishlist_items:
            items_text = ""
            for item in wishlist_items[:10]:
                items_text += f"• 🎁 {item.get('item_id', 'غير معروف')}\n"
                items_text += f"  📅 {item.get('release_time', 'غير محدد')}\n\n"
        else:
            items_text = "قائمة الرغبات فارغة."
        
        msg = get_text(user_id, 'wishlist_result', wishlist=items_text)
    
    await query.edit_message_text(msg, reply_markup=get_back_button(user_id, f'account_control_{acc_id}'))

# -*- coding: utf-8 -*-

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from utils import get_text
from database import db
from config import ADMIN_IDS
from handlers.main_menu import get_main_menu

# ========== معالجات الاشتراكات ==========
async def handle_buy_now(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    query = update.callback_query
    await query.answer()
    
    keyboard = []
    for key, plan in db.SUBSCRIPTION_PLANS.items():
        keyboard.append([
            InlineKeyboardButton(
                f"💰 {plan['name']} - {plan['price']}$",
                callback_data=f'plan_{key}'
            )
        ])
    keyboard.append([InlineKeyboardButton("🔙 عودة", callback_data='main_menu')])
    
    await query.edit_message_text(
        "📌 اختر الباقة المناسبة لك:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def handle_use_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    query = update.callback_query
    await query.answer()
    
    context.user_data['action'] = 'waiting_code'
    
    await query.edit_message_text(
        "🎫 أرسل كود التفعيل:",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 عودة", callback_data='main_menu')]
        ])
    )

async def handle_code_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    code = update.message.text.strip().upper()
    
    if not code:
        await update.message.reply_text("⚠️ الكود لا يمكن أن يكون فارغاً.")
        return
    
    success, message = db.use_code(code, user_id)
    
    if success:
        await update.message.reply_text(
            f"✅ {message}\nيمكنك الآن استخدام جميع خدمات البوت.",
            reply_markup=get_main_menu(user_id)
        )
    else:
        await update.message.reply_text(
            f"❌ {message}",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🎫 محاولة مرة أخرى", callback_data='use_code')],
                [InlineKeyboardButton("🔙 عودة", callback_data='main_menu')]
            ])
        )
    
    context.user_data['action'] = None

async def handle_services_explain(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    query = update.callback_query
    await query.answer()
    
    text = """📖 **شرح خدمات البوت:**

🔍 **كشف الاستعادة:** فحص الحساب لمعرفة البريد الإلكتروني المربوط به.

🔗 **كشف روابط:** عرض جميع المنصات المرتبطة بالحساب (فيسبوك، جوجل، آبل، الخ).

🧪 **تجربة رمز الأمان:** التحقق من صحة رموز الأمان.

➕ **إضافة/تغيير استعادة:** تغيير بريد الاستعادة أو إضافة بريد جديد.

🗑️ **حذف روابط ثانوية:** إلغاء طلبات الربط المعلقة.

🔥 **حرق التوكيل:** تسجيل الخروج الإجباري من جميع الأجهزة.

👀 **زيادة زيارات:** جلب معلومات الحساب (الاسم، المستوى، الإعجابات).

✏️ **تغيير الاسم:** تغيير اسم المستخدم في اللعبة.

🏰 **القبيلة:** الانضمام أو مغادرة القبائل.

👥 **طلب صداقة:** إرسال طلبات صداقة.

🚫 **فحص الحظر:** التحقق من حالة الحظر.

📅 **الأحداث:** عرض أحداث اللعبة الحالية.

⭐ **قائمة الرغبات:** عرض قائمة الرغبات الخاصة بالحساب."""
    
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 عودة", callback_data='main_menu')]
        ])
    )

async def handle_customer_service(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    query = update.callback_query
    await query.answer()
    
    await query.edit_message_text(
        "👥 **خدمة العملاء:**\n\nللتواصل مع الدعم الفني:\n📧 البريد الإلكتروني: support@example.com\n📱 تيليجرام: @SupportBot",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 عودة", callback_data='main_menu')]
        ])
    )

async def handle_bot_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    query = update.callback_query
    await query.answer()
    
    await query.edit_message_text(
        "📱 **مجموعة البوت:**\n\nانضم إلى مجموعتنا للحصول على التحديثات والدعم:\n🔗 https://t.me/YourBotGroup",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 عودة", callback_data='main_menu')]
        ])
    )

# ========== لوحة تحكم الأدمن ==========
async def show_admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("⛔ هذا الأمر مخصص للأدمن فقط.")
        return
    
    users_count = len(db.data['users'])
    codes_count = len(db.data['codes'])
    
    keyboard = [
        [InlineKeyboardButton("👥 المستخدمين", callback_data='admin_users')],
        [InlineKeyboardButton("🎫 إدارة الأكواد", callback_data='admin_codes')],
        [InlineKeyboardButton("💼 الوكيل", callback_data='admin_reseller')],
        [InlineKeyboardButton("🔙 عودة", callback_data='main_menu')]
    ]
    
    await update.message.reply_text(
        f"⚙️ **لوحة تحكم الأدمن**\n\n"
        f"👥 عدد المستخدمين: {users_count}\n"
        f"🎫 عدد الأكواد: {codes_count}",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

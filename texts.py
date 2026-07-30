# -*- coding: utf-8 -*-

TEXTS = {
    'ar': {
        # ========== رسائل عامة ==========
        'welcome': "👋 مرحباً بك في خدمات {bot_name}\nنظام إدارة حسابات فري فاير المتقدم.",
        
        'subscribe_required': """مرحباً بكم في خدمات {bot_name} لبريد الاستعادة، نظراً لكثرة الطلب والاحتيال والضغط العالي تم تحويل جميع خدمات البوت بشكل كامل الى خدمة مدفوعة باشتراك.

🆔 رقم الابدي الخاص بك : `{user_id}`

من اجل التفعيل يرجى الضغط على (شراء الان) واتمام الدفع للوصول لخدمات البوت.""",
        
        'choose_subscription': "📌 يرجى اختيار نوع التفعيل:",
        'subscription_activated': "✅ تم تفعيل اشتراكك بنجاح! يمكنك الآن استخدام جميع خدمات البوت.",
        'already_subscribed': "✅ أنت مشترك بالفعل حتى `{expiry}`.",
        'buy_now': "💰 شراء الان",
        'use_code': "🎫 استخدام كود",
        'services_explain': "📖 شرح الخدمات",
        'customer_service': "👥 خدمة العملاء",
        'bot_group': "📱 مجموعة البوت",
        'main_menu': "🏠 القائمة الرئيسية",
        'back': "🔙 عودة",
        'choose': "📌 يرجى اختيار خدمة من خلال الأزرار التالية:",
        
        # ========== إدارة الحسابات ==========
        'enter_eat': "📥 **إضافة حساب جديد**\n\nلإضافة حساب، أرسل رابط التوكن (EAT) الخاص بالحساب.\n\n📌 **مثال:**\n`https://discstore.recargajogo.com.br/?eat=...`\n\n⚠️ تأكد من أن الرابط يحتوي على `eat=` ويبدأ بـ `https://discstore.recargajogo.com.br/`",
        
        'account_linked': "✅ **تم ربط الحساب بنجاح!**\n\n👤 **الاسم:** {name}\n🆔 **الأيدي:** {id}\n🌍 **السيرفر:** {region}",
        
        'account_exists': "⚠️ هذا الحساب مضاف مسبقاً!",
        'no_accounts': "📭 لا يوجد حسابات محفوظة حتى الآن.\n\nيمكنك إضافة حساب جديد بالضغط على زر '➕ إضافة حساب'.",
        'select_delete': "📋 اختر الحساب الذي تريد حذفه:",
        'account_deleted': "🗑️ تم حذف الحساب بنجاح!",
        'select_account': "🎮 اختر الحساب الذي تريد إدارته من القائمة:",
        
        # ========== لوحة الإدارة ==========
        'dashboard': """🏷️ **لوحة الإدارة:**

👤 **الاسم:** {name}
🆔 **الآيدي:** {id}
🌍 **السيرفر:** {region}
📅 **وقت الفحص:** {check_time}
⏳ **انتهاء التوكيل:** {token_expiry}
📊 **حالة التوكيل:** {token_status}
🤖 **الاخصين الآلي:** {emulator}
🔄 **حالة السبام:** {spam_status}""",
        
        'account_controls': "🎮 **لوحة تحكم الحساب:**\n👤 **الاسم:** {name}\n🆔 **الأيدي:** {id}\n🌍 **السيرفر:** {region}\n📱 **التخمين الآلي:** {emulator}",
        
        # ========== أزرار الخدمات الأساسية ==========
        'check_links': "🔗 كشف روابط",
        'check_recovery': "🔍 كشف الإستعادة",
        'try_otp': "🧪 تجربة رمز الأمان",
        'add_change_recovery': "➕ إضافة/تغيير استعادة",
        'delete_links': "🗑️ حذف روابط ثانوية",
        'burn_token': "🔥 حرق التوكيل",
        'spam_login': "📨 سبام تسجيل دخول",
        'permanent_ban': "🚫 بان دائم",
        
        # ========== رسائل كشف الاستعادة ==========
        'recovery_result': """🔐 **تفاصيل استعادة الحساب**

📧 **البريد الحالي:** {current_email}
📨 **البريد المعلق:** {pending_email}
⏳ **الوقت المتبقي:** {countdown}
📌 **الحالة:** {status}

📖 **شرح الحالة:**
{explanation}""",
        
        # ========== رسائل كشف الروابط ==========
        'links_result': """🔗 **المنصات المرتبطة بالحساب**

{platforms}""",
        'fetching_links': "⏳ جاري سحب الروابط الثانوية...",
        'links_found': "✅ تم سحب الروابط الثانوية بنجاح!\n\n{links}",
        
        # ========== رسائل تغيير/إضافة الاستعادة ==========
        'enter_old_email': "📧 أرسل البريد الإلكتروني القديم (المرتبط حالياً):",
        'enter_new_email': "📧 أرسل البريد الإلكتروني الجديد الذي تريد ربطه:",
        'enter_otp': "🔑 أرسل رمز OTP الذي وصلك إلى بريدك:",
        'enter_email': "📧 أرسل الآن البريد الإلكتروني المراد ربطه (أو إرسال OTP له):",
        'enter_secondary_password': "🔐 أرسل الآن كلمة المرور الثانوية (security_code) الخاصة بالحساب:",
        'enter_bind_details': "📝 لإضافة استعادة، ستحتاج إلى:\n1. البريد الإلكتروني\n2. رمز OTP\n3. كلمة المرور الثانوية\n\nسأطلبها منك خطوة بخطوة.",
        
        'otp_sent': "✅ تم إرسال رمز OTP إلى `{email}` بنجاح.",
        'otp_verified': "✅ تم التحقق من الرمز بنجاح.",
        'identity_verified': "✅ تم التحقق من الهوية بنجاح. جارٍ إنشاء طلب الربط...",
        'email_changed': "✅ تم تغيير بريد الاستعادة بنجاح من `{old}` إلى `{new}`.",
        'bind_request_created': "✅ تم إنشاء طلب الربط بنجاح! تم ربط البريد الإلكتروني `{email}` بالحساب.",
        'unbind_request_created': "✅ تم إلغاء ربط البريد الإلكتروني بنجاح.",
        'unbind_success': "✅ تم إلغاء ربط بريد الاستعادة `{email}` بنجاح.",
        'rebind_request_created': "✅ تم إعادة ربط البريد الإلكتروني بنجاح.",
        'request_cancelled': "✅ تم إلغاء أي طلب ربط معلق.",
        'cancel_existing_request': "⏳ جاري إلغاء أي طلب ربط سابق...",
        'email_already_bound': "⚠️ هذا البريد الإلكتروني مرتبط بالفعل بالحساب.",
        
        'operation_failed': "❌ فشلت العملية: {error}",
        'no_access_token': "❌ لا يوجد توكن وصول صالح لهذا الحساب.",
        'invalid_input': "⚠️ إدخال غير صالح، يرجى المحاولة مرة أخرى.",
        'api_error': "❌ حدث خطأ أثناء الاتصال بالخادم، حاول لاحقاً.",
        'limit_reached': "⛔ تم الوصول إلى الحد الأقصى للمحاولات، حاول بعد 24 ساعة.",
        
        # ========== حرق التوكيل ==========
        'burn_success': "🔥 تم حرق التوكن وإبطاله بنجاح (تم تسجيل الخروج من جميع الأجهزة).",
        'token_revoked': "✅ تم تسجيل الخروج وإبطال التوكن بنجاح.",
        
        # ========== سبام تسجيل دخول ==========
        'spam_started': "📨 بدأ سبام تسجيل الدخول... (تجريبي)",
        'spam_stopped': "⏹️ تم إيقاف سبام تسجيل الدخول.",
        
        # ========== الخدمات المدفوعة ==========
        'paid_service': "⚠️ خدمة '{service}' تتطلب اشتراكاً مدفوعاً.\nللتفعيل، تواصل مع المطور.",
        
        # ========== اللغة ==========
        'choose_lang': "🌐 اختر لغتك المفضلة:",
        'lang_changed': "✅ تم تغيير اللغة إلى العربية.",
        'lang_changed_en': "✅ Language changed to English.",
        'language': "🌐 اللغة",
        
        # ========== الشروط والأحكام ==========
        'terms_text': """📜 **الشروط والأحكام:**

1. **الاستخدام المسؤول**: هذا البوت مصمم لمساعدتك في حماية حساباتك وإدارتها، وكل استخدام يقع على مسؤوليتك الشخصية.

2. **الخدمات المدفوعة**: الخاصيات المدفوعة متعجب عليها وتستعمل موارد مدفوعة، لذا فإن أسعارها نهائية وغير قابلة للنقاش.

3. **الاسترداد المالي**: لا يوجد استرجاع للمبالغ بعد تفعيل الخدمات بنجاح.

4. **الحظر**: يحق للإدارة حظر أي شخص يحاول التلاعب بالبوت أو استغلاله بشكل يضر بالخدمة.

---
👨‍💻 **المطور:** iloveyoustore
📧 **البريد الإلكتروني:** bebekred@example.com""",
        
        # ========== الخدمات الجديدة ==========
        'visit_account': "👀 زيادة زيارات الحساب",
        'change_nickname': "✏️ تغيير الاسم",
        'guild_manage': "🏰 إدارة القبيلة",
        'send_friend': "👥 طلب صداقة",
        'check_ban': "🚫 فحص الحظر",
        'events_info': "📅 أحداث اللعبة",
        'wishlist': "⭐ قائمة الرغبات",

        'visit_result': """👀 **معلومات الحساب**

🆔 **الـ UID:** `{uid}`
👤 **الاسم:** {nickname}
🌍 **المنطقة:** {region}
📊 **المستوى:** {level}
❤️ **الإعجابات:** {likes}
📈 **إجمالي الزيارات:** {total}
{extra}""",

        'nickname_changed': "✅ تم تغيير الاسم إلى `{new_name}` بنجاح!",
        'enter_new_nickname': "✏️ أرسل الاسم الجديد الذي تريد تغييره:",
        
        'guild_joined': "✅ تم الانضمام إلى القبيلة `{clan_id}` بنجاح!",
        'guild_left': "✅ تم مغادرة القبيلة `{clan_id}` بنجاح!",
        'enter_clan_id': "🏰 أرسل معرف القبيلة (Clan ID):",
        
        'friend_sent': "✅ تم إرسال طلب صداقة إلى `{uid}` بنجاح!",
        'friend_removed': "✅ تم إلغاء طلب الصداقة من `{uid}` بنجاح!",
        'enter_target_uid': "👤 أرسل UID المستخدم المستهدف:",
        
        'ban_result': """🚫 **نتيجة فحص الحظر**

📊 **الحالة:** {status}
🆔 **الـ UID:** {uid}
👤 **الاسم:** {name}
🌍 **المنطقة:** {region}""",

        'events_result': """📅 **أحداث اللعبة الحالية**

{events}""",

        'wishlist_result': """⭐ **قائمة الرغبات**

{wishlist}""",

        # ========== رسائل الأدمن ==========
        'admin_panel': "⚙️ **لوحة تحكم الأدمن**",
        'user_list': "👥 **قائمة المستخدمين**\n{users}",
        'manage_codes': "🎫 **إدارة الأكواد**\n{code_list}",
        'reseller_panel': "💼 **لوحة تحكم الوكيل**",
        'points_balance': "⭐ **رصيد النقاط:** {points}",
    },
    
    'en': {
        # ========== General Messages ==========
        'welcome': "👋 Welcome to {bot_name}\nAdvanced Free Fire Account Management System.",
        
        'subscribe_required': """Welcome to {bot_name} recovery services. Due to high demand and fraud, all services have been converted to paid subscription.

🆔 Your ID: `{user_id}`

Please click (Buy Now) and complete payment to access bot services.""",
        
        'choose_subscription': "📌 Please choose subscription type:",
        'subscription_activated': "✅ Subscription activated successfully! You can now use all services.",
        'already_subscribed': "✅ You are already subscribed until `{expiry}`.",
        'buy_now': "💰 Buy Now",
        'use_code': "🎫 Use Code",
        'services_explain': "📖 Services Explanation",
        'customer_service': "👥 Customer Service",
        'bot_group': "📱 Bot Group",
        'main_menu': "🏠 Main Menu",
        'back': "🔙 Back",
        'choose': "📌 Please choose a service from the buttons below:",
        
        # ========== Account Management ==========
        'enter_eat': "📥 **Add New Account**\n\nTo add an account, send the EAT link of the account.\n\n📌 **Example:**\n`https://discstore.recargajogo.com.br/?eat=...`\n\n⚠️ Make sure the link contains `eat=` and starts with `https://discstore.recargajogo.com.br/`",
        
        'account_linked': "✅ **Account linked successfully!**\n\n👤 **Name:** {name}\n🆔 **ID:** {id}\n🌍 **Server:** {region}",
        
        'account_exists': "⚠️ This account is already added!",
        'no_accounts': "📭 No saved accounts.\n\nYou can add a new account by clicking '➕ Add Account'.",
        'select_delete': "📋 Select account to delete:",
        'account_deleted': "🗑️ Account deleted successfully!",
        'select_account': "🎮 Choose an account to manage from the list:",
        
        # ========== Dashboard ==========
        'dashboard': """🏷️ **Dashboard:**

👤 **Name:** {name}
🆔 **ID:** {id}
🌍 **Server:** {region}
📅 **Check Time:** {check_time}
⏳ **Token Expiry:** {token_expiry}
📊 **Token Status:** {token_status}
🤖 **Emulator:** {emulator}
🔄 **Spam Status:** {spam_status}""",
        
        'account_controls': "🎮 **Account Control Panel:**\n👤 **Name:** {name}\n🆔 **ID:** {id}\n🌍 **Server:** {region}\n📱 **Emulator:** {emulator}",
        
        # ========== Service Buttons ==========
        'check_links': "🔗 Check Links",
        'check_recovery': "🔍 Check Recovery",
        'try_otp': "🧪 Try OTP",
        'add_change_recovery': "➕ Add/Change Recovery",
        'delete_links': "🗑️ Delete Secondary Links",
        'burn_token': "🔥 Burn Token",
        'spam_login': "📨 Spam Login",
        'permanent_ban': "🚫 Permanent Ban",
        
        # ========== Recovery Check ==========
        'recovery_result': """🔐 **Recovery Details**

📧 **Current Email:** {current_email}
📨 **Pending Email:** {pending_email}
⏳ **Time Remaining:** {countdown}
📌 **Status:** {status}

📖 **Explanation:**
{explanation}""",
        
        # ========== Links Check ==========
        'links_result': """🔗 **Linked Platforms**

{platforms}""",
        'fetching_links': "⏳ Fetching secondary links...",
        'links_found': "✅ Secondary links retrieved successfully!\n\n{links}",
        
        # ========== Recovery Change/Add ==========
        'enter_old_email': "📧 Send the old email (currently linked):",
        'enter_new_email': "📧 Send the new email to bind:",
        'enter_otp': "🔑 Send the OTP code received on your email:",
        'enter_email': "📧 Send the email address to bind (or send OTP):",
        'enter_secondary_password': "🔐 Send the secondary password (security_code) for the account:",
        'enter_bind_details': "📝 To add recovery, you need:\n1. Email\n2. OTP code\n3. Secondary password\n\nI'll ask for them step by step.",
        
        'otp_sent': "✅ OTP sent to `{email}` successfully.",
        'otp_verified': "✅ OTP verified successfully.",
        'identity_verified': "✅ Identity verified. Creating bind request...",
        'email_changed': "✅ Recovery email changed from `{old}` to `{new}` successfully.",
        'bind_request_created': "✅ Bind request created! Email `{email}` bound to account.",
        'unbind_request_created': "✅ Email unbound successfully.",
        'unbind_success': "✅ Recovery email `{email}` unbound successfully.",
        'rebind_request_created': "✅ Email rebound successfully.",
        'request_cancelled': "✅ Pending bind request cancelled.",
        'cancel_existing_request': "⏳ Cancelling any previous bind request...",
        'email_already_bound': "⚠️ This email is already bound to the account.",
        
        'operation_failed': "❌ Operation failed: {error}",
        'no_access_token': "❌ No valid access token for this account.",
        'invalid_input': "⚠️ Invalid input. Please try again.",
        'api_error': "❌ Error connecting to server. Please try again later.",
        'limit_reached': "⛔ Maximum attempts reached. Try after 24 hours.",
        
        # ========== Burn Token ==========
        'burn_success': "🔥 Token burned and revoked successfully (logged out from all devices).",
        'token_revoked': "✅ Logged out and token revoked successfully.",
        
        # ========== Spam Login ==========
        'spam_started': "📨 Spam login started... (Beta)",
        'spam_stopped': "⏹️ Spam login stopped.",
        
        # ========== Paid Services ==========
        'paid_service': "⚠️ Service '{service}' requires a paid subscription.\nContact the developer to activate.",
        
        # ========== Language ==========
        'choose_lang': "🌐 Choose your preferred language:",
        'lang_changed': "✅ Language changed to Arabic.",
        'lang_changed_en': "✅ Language changed to English.",
        'language': "🌐 Language",
        
        # ========== Terms & Conditions ==========
        'terms_text': """📜 **Terms & Conditions:**

1. **Responsible Use**: This bot is designed to help you protect and manage your accounts, and all use is at your own risk.

2. **Paid Services**: Paid features are premium and use paid resources, so prices are final and non-negotiable.

3. **Refund Policy**: No refunds after services are successfully activated.

4. **Ban Policy**: The administration reserves the right to ban anyone who attempts to manipulate or exploit the bot.

---
👨‍💻 **Developer:** iloveyoustore
📧 **Email:** bebekred@example.com""",
        
        # ========== New Services ==========
        'visit_account': "👀 Visit Account",
        'change_nickname': "✏️ Change Nickname",
        'guild_manage': "🏰 Guild Management",
        'send_friend': "👥 Friend Request",
        'check_ban': "🚫 Check Ban",
        'events_info': "📅 Game Events",
        'wishlist': "⭐ Wishlist",

        'visit_result': """👀 **Account Information**

🆔 **UID:** `{uid}`
👤 **Name:** {nickname}
🌍 **Region:** {region}
📊 **Level:** {level}
❤️ **Likes:** {likes}
📈 **Total Visits:** {total}
{extra}""",

        'nickname_changed': "✅ Nickname changed to `{new_name}` successfully!",
        'enter_new_nickname': "✏️ Send the new nickname you want:",
        
        'guild_joined': "✅ Joined guild `{clan_id}` successfully!",
        'guild_left': "✅ Left guild `{clan_id}` successfully!",
        'enter_clan_id': "🏰 Send the Clan ID:",
        
        'friend_sent': "✅ Friend request sent to `{uid}` successfully!",
        'friend_removed': "✅ Friend request removed from `{uid}` successfully!",
        'enter_target_uid': "👤 Send the target user's UID:",
        
        'ban_result': """🚫 **Ban Check Result**

📊 **Status:** {status}
🆔 **UID:** {uid}
👤 **Name:** {name}
🌍 **Region:** {region}""",

        'events_result': """📅 **Current Game Events**

{events}""",

        'wishlist_result': """⭐ **Wishlist**

{wishlist}""",

        # ========== Admin Messages ==========
        'admin_panel': "⚙️ **Admin Panel**",
        'user_list': "👥 **User List**\n{users}",
        'manage_codes': "🎫 **Code Management**\n{code_list}",
        'reseller_panel': "💼 **Reseller Panel**",
        'points_balance': "⭐ **Points Balance:** {points}",
    }
}

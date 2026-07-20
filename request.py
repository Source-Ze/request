import time
import sqlite3
import telebot
from telebot import types, apihelper
from telebot.types import ChatMemberUpdated

# =============================================================
# 1. Configuration (الإعدادات الأساسية)
# =============================================================
BOT_TOKEN = "8801995096:AAEYIN4YIa5Z_j65qB1a8KJYyGU-uLRsvbY"  # توكن البوت
SUDO_ADMIN = 8155068892             # Telegram ID الخاص بالمطور الأساسي

# 🔧 إعداد البروكسي الخاص بالحسابات المجانية في PythonAnywhere
apihelper.proxy = {
    'http': 'http://proxy.server:3128',
    'https': 'http://proxy.server:3128'
}

bot = telebot.TeleBot(BOT_TOKEN)

# =============================================================
# 2. Database Setup (إعداد قاعدة البيانات)
# =============================================================
DB_NAME = "bot_database.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    # جدول المطورين
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS admins (
            user_id INTEGER PRIMARY KEY
        )
    ''')

    # جدول المحظورين
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS banned (
            user_id INTEGER PRIMARY KEY
        )
    ''')

    # جدول إعدادات البوت (حالة التواصل)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    ''')

    # جدول بيانات المستخدمين المتقدمين
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            name TEXT,
            username TEXT,
            faculty TEXT,
            dept TEXT,
            track TEXT,
            progress TEXT
        )
    ''')

    # إضافة المطور الأساسي تلقائياً إذا لم يكن موجوداً
    cursor.execute("INSERT OR IGNORE INTO admins (user_id) VALUES (?)", (SUDO_ADMIN,))

    # ضبط حالة التواصل كـ "مفعل" في البداية إن لم تكن مسجلة
    cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('bot_active', 'true')")

    conn.commit()
    conn.close()

# تشغيل إعداد قاعدة البيانات
init_db()

# =============================================================
# 3. Database Helper Functions (دوال للتعامل مع الداتا)
# =============================================================
def is_admin(user_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM admins WHERE user_id = ?", (user_id,))
    res = cursor.fetchone()
    conn.close()
    return res is not None

def add_admin_db(user_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO admins (user_id) VALUES (?)", (user_id,))
    conn.commit()
    conn.close()

def remove_admin_db(user_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM admins WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()

def is_banned(user_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM banned WHERE user_id = ?", (user_id,))
    res = cursor.fetchone()
    conn.close()
    return res is not None

def ban_user_db(user_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO banned (user_id) VALUES (?)", (user_id,))
    conn.commit()
    conn.close()

def unban_user_db(user_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM banned WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()

def get_bot_active_status():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM settings WHERE key = 'bot_active'")
    res = cursor.fetchone()
    conn.close()
    return res[0] == 'true' if res else True

def set_bot_active_status(status: bool):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    val_str = 'true' if status else 'false'
    cursor.execute("UPDATE settings SET value = ? WHERE key = 'bot_active'", (val_str,))
    conn.commit()
    conn.close()

def save_user_data_db(user_id, name, username, faculty, dept, track, progress):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT OR REPLACE INTO users (user_id, name, username, faculty, dept, track, progress)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (user_id, name, username, faculty, dept, track, progress))
    conn.commit()
    conn.close()

def get_stats_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM users")
    users_count = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM admins")
    admins_count = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM banned")
    banned_count = cursor.fetchone()[0]
    conn.close()
    return users_count, admins_count, banned_count

def get_all_admins():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM admins")
    rows = cursor.fetchall()
    conn.close()
    return [r[0] for r in rows]

# =============================================================
# 4. Data Memory Temporary (لخطوات الاستبيان المباشرة فقط)
# =============================================================
temp_user_state = {}

DEPARTMENTS = {
    "علوم حاسب (CS)": ["Software Engineering", "Algorithms & Problem Solving", "Cyber Security", "Data Science"],
    "نظم معلومات (IS)": ["Database Admin", "Business Analysis", "ERP Systems", "Data Analytics"],
    "تكنولوجيا معلومات (IT)": ["Network Engineering", "Cyber Security", "Cloud Computing & DevOps", "System Admin"],
    "ذكاء اصطناعي (AI)": ["Machine Learning", "Deep Learning", "Computer Vision", "NLP"],
    "أمن سيبراني (Cyber Security)": [
        "Ethical Hacking & Penetration Testing (Red Team)",
        "SOC Analyst & Incident Response (Blue Team)",
        "Network Security",
        "Digital Forensics & Reverse Engineering",
        "Application & Web Security"
    ]
}

NON_CS_TRACKS = [
    "Web Development",
    "Mobile App Development",
    "Cyber Security & Ethical Hacking",
    "Network Engineering (CCNA)",
    "Data Analysis & Data Science",
    "UI/UX Design"
]

# =============================================================
# 5. Helper Keyboards
# =============================================================
def get_admin_keyboard():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    kb.add("🟢 تفعيل التواصل", "🔴 تعطيل التواصل")
    kb.add("📊 إحصائيات البوت")
    kb.add("➕ رفع مطور", "➖ تنزيل مطور")
    kb.add("🚫 حظر مستخدم", "✅ فك حظر مستخدم")
    kb.add("❌ إغلاق اللوحة")
    return kb

# =============================================================
# 6. Start Command Logic (تضمين الترحيب المعدل هنا)
# =============================================================
@bot.message_handler(commands=['start'])
def start_cmd(message):
    user_id = message.from_user.id

    if is_banned(user_id):
        bot.send_message(message.chat.id, "❌ أنت محظور من استخدام هذا البوت.")
        return

    # لو المستخدم أدمن داخل الخاص
    if is_admin(user_id) and message.chat.type == 'private':
        welcome_admin = (
            f"👑 **أهلاً بك يا بطل في لوحة تحكم المطورين!**\n\n"
            f"أنت مسجل كمطور في البوت (البيانات محفوظة دائماً في Database). يمكنك التحكم الكامل من الأزرار بالأسفل 👇"
        )
        bot.send_message(message.chat.id, welcome_admin, parse_mode="Markdown", reply_markup=get_admin_keyboard())
        return

    if not get_bot_active_status() and not is_admin(user_id):
        bot.send_message(message.chat.id, "⚠️ البوت قيد الصيانة أو تم تعطيل استقبال الطلبات حالياً، يرجى المحاولة لاحقاً.")
        return

    temp_user_state[user_id] = {}

    welcome_text = (
        "🏛️ **أهلاً بكم في: بوت جروب كلية الحاسبات والمعلومات** 💻✨\n\n"
        "الهدف من الجروب والبوت هو تبادل الخبرات الأكاديمية، المساعدة في المواد الدراسية، "
        "ومشاركة الكورسات والمصادر البرمجية وتقنيات الحاسب والشبكات والأمن السيبراني.\n\n"
        "📌 **قوانين التعامل:**\n"
        "▫️ الاحترام المتبادل بين جميع الأعضاء.\n"
        "▫️ يمنع نشر الإعلانات أو الروابط المجهولة (السبام).\n"
        "▫️ النقاشات في حدود ما يفيد الطلاب والجانب التقني والأكاديمي.\n\n"
        "🚀 *نتمنى لكم جميعاً توفيقاً ونجاحاً باهراً!*\n\n"
        "───────────────────\n"
        f"👋 **أهلاً بك يا {message.from_user.first_name}!**\n"
        f"👇 هل أنت طالب أو خريج في **كلية حاسبات ومعلومات / علوم حاسب**؟"
    )

    kb = types.InlineKeyboardMarkup()
    kb.add(
        types.InlineKeyboardButton("نعم ✅", callback_data="is_cs_yes"),
        types.InlineKeyboardButton("لا ❌", callback_data="is_cs_no")
    )
    bot.send_message(message.chat.id, welcome_text, parse_mode="Markdown", reply_markup=kb)

@bot.message_handler(commands=['admin'])
def admin_cmd(message):
    if is_admin(message.from_user.id):
        start_cmd(message)

# =============================================================
# 7. Group Member Event Handler (مراقبة الانضمام والحظر)
# =============================================================
@bot.chat_member_handler()
def handle_chat_member_update(update: ChatMemberUpdated):
    old_status = update.old_chat_member.status
    new_status = update.new_chat_member.status
    user = update.new_chat_member.user

    first_name = user.first_name or "بدون اسم"
    username = f"@{user.username}" if user.username else "لا يوجد يوزر"
    user_id = user.id
    chat_title = update.chat.title or "الجروب"

    # 🟢 1. حالة انضمام عضو جديد للجروب
    if old_status in ["left", "kicked", "restricted"] and new_status in ["member", "administrator"]:
        msg = (
            "📥 **إشعار انضمام عضو جديد للجروب!**\n\n"
            f"👤 **الاسم:** {first_name}\n"
            f"🏷️ **الـ Username:** {username}\n"
            f"🆔 **الـ ID:** `{user_id}`\n"
            f"👥 **الجروب:** {chat_title}"
        )
        for admin_id in get_all_admins():
            try:
                bot.send_message(admin_id, msg, parse_mode="Markdown")
            except Exception as e:
                print(f"Error notifying admin {admin_id}: {e}")

    # 🔴 2. حالة حظر/طرد عضو (Kicked / Banned)
    elif new_status in ["kicked", "banned"]:
        msg = (
            "🚫 **إشعار حظر/طرد عضو!**\n\n"
            f"👤 **الاسم:** {first_name}\n"
            f"🏷️ **الـ Username:** {username}\n"
            f"🆔 **الـ ID:** `{user_id}`\n"
            f"👥 **الجروب:** {chat_title}"
        )
        for admin_id in get_all_admins():
            try:
                bot.send_message(admin_id, msg, parse_mode="Markdown")
            except Exception as e:
                print(f"Error notifying admin {admin_id}: {e}")

# =============================================================
# 8. Admin Panel Logic
# =============================================================
@bot.message_handler(func=lambda m: m.text == "❌ إغلاق اللوحة" and is_admin(m.from_user.id))
def close_admin(message):
    bot.send_message(message.chat.id, "تم إغلاق لوحة التحكم بنجاح.", reply_markup=types.ReplyKeyboardRemove())

@bot.message_handler(func=lambda m: m.text == "🟢 تفعيل التواصل" and is_admin(m.from_user.id))
def enable_communication(message):
    set_bot_active_status(True)
    bot.send_message(message.chat.id, "🟢 **تم تفعيل استقبال البيانات والتواصل بنجاح!**", parse_mode="Markdown", reply_markup=get_admin_keyboard())

@bot.message_handler(func=lambda m: m.text == "🔴 تعطيل التواصل" and is_admin(m.from_user.id))
def disable_communication(message):
    set_bot_active_status(False)
    bot.send_message(message.chat.id, "🔴 **تم تعطيل استقبال البيانات والتواصل!**", parse_mode="Markdown", reply_markup=get_admin_keyboard())

@bot.message_handler(func=lambda m: m.text == "📊 إحصائيات البوت" and is_admin(m.from_user.id))
def bot_stats(message):
    users_cnt, admins_cnt, banned_cnt = get_stats_db()
    active_status = get_bot_active_status()

    stats = (
        f"📊 **إحصائيات البوت الحالية (من قاعدة البيانات DB):**\n\n"
        f"👥 عدد المسجلين الإجمالي: `{users_cnt}`\n"
        f"🛠 عدد المطورين المرفوعين: `{admins_cnt}`\n"
        f"🚫 عدد المستخدمين المحظورين: `{banned_cnt}`\n"
        f"⚡ حالة استقبال البيانات: `{'مفعل 🟢' if active_status else 'معطل 🔴'}`"
    )
    bot.send_message(message.chat.id, stats, parse_mode="Markdown")

# --- إدارة المطورين ---
@bot.message_handler(func=lambda m: m.text == "➕ رفع مطور" and is_admin(m.from_user.id))
def add_admin_prompt(message):
    msg = bot.send_message(message.chat.id, "أرسل الـ Telegram ID الخاص بالشخص المراد رفعه مطور:")
    bot.register_next_step_handler(msg, process_add_admin)

def process_add_admin(message):
    try:
        new_admin = int(message.text.strip())
        add_admin_db(new_admin)
        bot.send_message(message.chat.id, f"✅ تم رفع المستخدم `{new_admin}` كمطور وحفظه في DB بنجاح!", parse_mode="Markdown")
    except ValueError:
        bot.send_message(message.chat.id, "❌ خطأ! يرجى إرسال ID أرقام فقط.")

@bot.message_handler(func=lambda m: m.text == "➖ تنزيل مطور" and is_admin(m.from_user.id))
def remove_admin_prompt(message):
    msg = bot.send_message(message.chat.id, "أرسل الـ Telegram ID الخاص بالمطور المراد تنزيله:")
    bot.register_next_step_handler(msg, process_remove_admin)

def process_remove_admin(message):
    try:
        admin_id = int(message.text.strip())
        if admin_id == SUDO_ADMIN:
            bot.send_message(message.chat.id, "❌ لا يمكنك تنزيل المطور الأساسي (SUDO)!")
            return
        remove_admin_db(admin_id)
        bot.send_message(message.chat.id, f"✅ تم تنزيل المطور `{admin_id}` بنجاح.", parse_mode="Markdown")
    except ValueError:
        bot.send_message(message.chat.id, "❌ خطأ! يرجى إرسال ID أرقام فقط.")

# --- حظر وفك حظر ---
@bot.message_handler(func=lambda m: m.text == "🚫 حظر مستخدم" and is_admin(m.from_user.id))
def ban_prompt(message):
    msg = bot.send_message(message.chat.id, "أرسل الـ Telegram ID للمستخدم المراد حظره:")
    bot.register_next_step_handler(msg, process_ban)

def process_ban(message):
    try:
        user_id = int(message.text.strip())
        if is_admin(user_id):
            bot.send_message(message.chat.id, "❌ لا يمكنك حظر مطور!")
            return
        ban_user_db(user_id)
        bot.send_message(message.chat.id, f"🚫 تم حظر المستخدم `{user_id}` وتخزينه بالداتا بيز.", parse_mode="Markdown")
    except ValueError:
        bot.send_message(message.chat.id, "❌ خطأ! يرجى إرسال ID أرقام فقط.")

@bot.message_handler(func=lambda m: m.text == "✅ فك حظر مستخدم" and is_admin(m.from_user.id))
def unban_prompt(message):
    msg = bot.send_message(message.chat.id, "أرسل الـ Telegram ID للمستخدم المراد فك حظره:")
    bot.register_next_step_handler(msg, process_unban)

def process_unban(message):
    try:
        user_id = int(message.text.strip())
        unban_user_db(user_id)
        bot.send_message(message.chat.id, f"✅ تم فك حظر المستخدم `{user_id}` بنجاح.", parse_mode="Markdown")
    except ValueError:
        bot.send_message(message.chat.id, "❌ خطأ! يرجى إرسال ID أرقام فقط.")

# =============================================================
# 9. User Survey Flow
# =============================================================
def process_other_college(message):
    user_id = message.from_user.id
    college_name = message.text.strip()

    if user_id not in temp_user_state:
        temp_user_state[user_id] = {}

    temp_user_state[user_id]['faculty'] = f"خارج حاسبات ({college_name})"
    temp_user_state[user_id]['dept'] = "غير محدد (خارج حاسبات)"

    kb = types.InlineKeyboardMarkup(row_width=1)
    for track in NON_CS_TRACKS:
        kb.add(types.InlineKeyboardButton(track, callback_data=f"track_{track}"))

    bot.send_message(
        message.chat.id,
        f"تمام يا بطل! (كلية {college_name}) 🎯\nاختر التراك المهتم به أو تحاول تعلمه حالياً:",
        reply_markup=kb
    )

@bot.callback_query_handler(func=lambda call: True)
def handle_callbacks(call):
    user_id = call.from_user.id

    if is_banned(user_id) or (not get_bot_active_status() and not is_admin(user_id)):
        bot.answer_callback_query(call.id, "عذراً، البوت متوقف حالياً.", show_alert=True)
        return

    if user_id not in temp_user_state:
        temp_user_state[user_id] = {}

    if call.data == "is_cs_yes":
        temp_user_state[user_id]['faculty'] = "طالب/خريج حاسبات"
        kb = types.InlineKeyboardMarkup(row_width=1)
        for dept in DEPARTMENTS.keys():
            kb.add(types.InlineKeyboardButton(dept, callback_data=f"dept_{dept}"))
        bot.edit_message_text("عاش يا بطل! 💻 اختر القسم الخاص بك في الكلية:", call.message.chat.id, call.message.message_id, reply_markup=kb)

    elif call.data == "is_cs_no":
        msg = bot.edit_message_text("أهلاً بك! اكتب لنا اسم كليتك أو تخصصك الحالي الآن بالكتابة ✍️:", call.message.chat.id, call.message.message_id)
        bot.register_next_step_handler(msg, process_other_college)

    elif call.data.startswith("dept_"):
        dept_name = call.data.replace("dept_", "")
        temp_user_state[user_id]['dept'] = dept_name

        kb = types.InlineKeyboardMarkup(row_width=1)
        tracks = DEPARTMENTS.get(dept_name, NON_CS_TRACKS)
        for track in tracks:
            kb.add(types.InlineKeyboardButton(track, callback_data=f"track_{track}"))
        bot.edit_message_text(f"قسم {dept_name} ممتاز! 🚀\nاختر التراك المحدد الذي تركز عليه حالياً:", call.message.chat.id, call.message.message_id, reply_markup=kb)

    elif call.data.startswith("track_"):
        track_name = call.data.replace("track_", "")
        temp_user_state[user_id]['track'] = track_name

        kb = types.InlineKeyboardMarkup(row_width=1)
        kb.add(
            types.InlineKeyboardButton("🌱 ببدأ من الصفر / مبتدئ", callback_data="prog_مبتدئ (أساسيات)"),
            types.InlineKeyboardButton("⚡ قطعت شوط متوسط (طبق أجزاء ومشاريع صغيرة)", callback_data="prog_متوسط (تطبيقي)"),
            types.InlineKeyboardButton("🔥 متقدم وجاهز للمشاريع/العمل (مخلص شوط كبير)", callback_data="prog_متقدم (احترافي)")
        )
        bot.edit_message_text(f"تراك ({track_name}) 🎯!\nمستواك الحالي ووصلت لحد فين فيه؟", call.message.chat.id, call.message.message_id, reply_markup=kb)

    elif call.data.startswith("prog_"):
        progress = call.data.replace("prog_", "")

        username = f"@{call.from_user.username}" if call.from_user.username else "لا يوجد يوزر أوفيشيال"
        first_name = call.from_user.first_name or ""
        last_name = call.from_user.last_name or ""
        full_name = f"{first_name} {last_name}".strip()

        faculty = temp_user_state[user_id].get('faculty', 'غير معروف')
        dept = temp_user_state[user_id].get('dept', 'غير معروف')
        track = temp_user_state[user_id].get('track', 'غير معروف')

        # 💾 حفظ البيانات نهائياً في SQLite Database
        save_user_data_db(user_id, full_name, username, faculty, dept, track, progress)

        # مسح الداتا المؤقتة للمستخدم
        temp_user_state.pop(user_id, None)

        end_msg = (
            f"✅ **تم تسجيل وتوثيق بياناتك بنجاح!**\n\n"
            f"نشكرك جداً على وقتك، وسيتم مراجعة التخصص والتراك من قبل فريق المطورين للتواصل معك واستكمال الخطوات القادمة 🚀✨"
        )
        bot.edit_message_text(end_msg, call.message.chat.id, call.message.message_id, parse_mode="Markdown")

        # إرسال تقرير لكافة المطورين المسجلين في قاعدة البيانات
        admin_report = (
            f"📥 **تسجيل طلب جديد في البوت!**\n\n"
            f"👤 **الاسم:** {full_name}\n"
            f"🔗 **اليوزر:** {username}\n"
            f"🆔 **الـ ID:** `{user_id}`\n\n"
            f"🎓 **الكلية/التخصص:** {faculty}\n"
            f"🏛 **القسم:** {dept}\n"
            f"🎯 **التراك:** {track}\n"
            f"📊 **المستوى:** {progress}"
        )

        for admin_id in get_all_admins():
            try:
                bot.send_message(admin_id, admin_report, parse_mode="Markdown")
            except Exception as e:
                print(f"Error sending to admin {admin_id}: {e}")

# =============================================================
# 10. Execution
# =============================================================
if __name__ == "__main__":
    print("🤖 البوت يعمل بكفاءة وقاعدة البيانات SQLite متصلة...")

    bot.infinity_polling(
        skip_pending=True,
        allowed_updates=["message", "callback_query", "chat_member"]
    )

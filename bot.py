import sqlite3
import logging
import re
import pytz
from datetime import datetime, timedelta

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
    ChatMemberHandler,
    CallbackQueryHandler,
)

# ================= CONFIG =================
TOKEN = "8557455338:AAEYVbutR1kgm0pyG0u8lf7BL1EtLHhXecw"
CHANNEL_USERNAME = "@RekberEloise"
LOG_GROUP_ID = -5151128223  # ID Grup Done (Owner & Bot)
OWNER_ID = 8007886767         # ID @cinnamoroiLi
OWNER_USERNAME = "cinnamoroiLi"
TIMEZONE = pytz.timezone("Asia/Jakarta")

# ================= DATABASE =================
db = sqlite3.connect("bot.db", check_same_thread=False)
cursor = db.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    username TEXT,
    senin INTEGER DEFAULT 0,
    jumat INTEGER DEFAULT 0,
    minggu INTEGER DEFAULT 0,
    points INTEGER DEFAULT 0,
    total_absen INTEGER DEFAULT 0
)
""")

cursor.execute("CREATE TABLE IF NOT EXISTS used_usernames (username TEXT PRIMARY KEY, used_by INTEGER)")
cursor.execute("CREATE TABLE IF NOT EXISTS join_logs (username TEXT PRIMARY KEY, join_time TIMESTAMP)")
cursor.execute("CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)")
db.commit()

# Init Settings
cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('keyword', 'mangga')")
cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('konsekuensi', 'Tebus hukuman dengan post 50 list baru!')")
db.commit()

# ================= UTIL =================
def get_greeting():
    hour = datetime.now(TIMEZONE).hour
    if 5 <= hour < 12: return "Selamat Pagi 🌅"
    elif 12 <= hour < 15: return "Selamat Siang ☀️"
    elif 15 <= hour < 18: return "Selamat Sore ☁️"
    else: return "Selamat Malam 🌙"

def save_user(user):
    cursor.execute("INSERT OR IGNORE INTO users (user_id, username) VALUES (?, ?)", (user.id, user.username))
    db.commit()

# ================= HANDLERS =================

async def track_join(update: Update, context: ContextTypes.DEFAULT_TYPE):
    member = update.chat_member
    if member.new_chat_member.status == "member":
        username = member.new_chat_member.user.username
        if username:
            cursor.execute("INSERT OR REPLACE INTO join_logs (username, join_time) VALUES (?, ?)",
                           (username.lower(), datetime.now(TIMEZONE).isoformat()))
            db.commit()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    save_user(user)
    username = f"@{user.username}" if user.username else user.first_name

    # Bubble 1
    await update.message.reply_text(f"Bot by @{OWNER_USERNAME}, Hellow bellow {username}. 🫧")

    # Bubble 2
    markup = InlineKeyboardMarkup([
        [InlineKeyboardButton("🧁 Pilih Absen", callback_data="pilih_absen")],
        [InlineKeyboardButton("🏆 Leaderboard", callback_data="leaderboard_bbc"), 
         InlineKeyboardButton("💌 Tanya Cinna", callback_data="tanya_owner")],
        [InlineKeyboardButton("📜 Konsekuensi", callback_data="cek_konsekuensi")]
    ])

    text = f"{get_greeting()}, {username}.\n\n" \
           f"<b>Broadcast hari ini :</b> -\n" \
           f"<b>Broadcast 1 pekan :</b> -\n" \
           f"<i>Broadcast tertinggi : (jadwal kapan, dan berapa)</i> ☁️"
    
    await update.message.reply_text(text, parse_mode="HTML", reply_markup=markup)

async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    uid = query.from_user.id

    if query.data == "pilih_absen":
        markup = InlineKeyboardMarkup([
            [InlineKeyboardButton("Absen Senin : Upsubs 25s", callback_data="form_senin")],
            [InlineKeyboardButton("Absen Jumat : Jaseb 50 Lpm", callback_data="form_jumat")],
            [InlineKeyboardButton("Absen Minggu : Send mf 20x", callback_data="form_minggu")],
            [InlineKeyboardButton("⬅️ Back", callback_data="back_start")]
        ])
        await query.edit_message_text("Silahkan Pilih Absen, Untuk Reminder 🎀", reply_markup=markup)

    elif query.data == "form_senin":
        await query.message.reply_text("Silahkan kirim list 25 username @\nContoh:\n1. @user\n2. @user\n...")
        context.user_data['state'] = 'WAIT_SENIN'

    elif query.data == "form_jumat":
        await query.message.reply_text("Silahkan kirim screenshoot yang sudah di grid, Master akan mengeceknya! 📸")
        context.user_data['state'] = 'WAIT_JUMAT'

    elif query.data == "form_minggu":
        cursor.execute("SELECT value FROM settings WHERE key='keyword'")
        key = cursor.fetchone()[0]
        await query.message.reply_text(f"Kirim 20 link menfess dengan keyword: <b>{key}</b>", parse_mode="HTML")
        context.user_data['state'] = 'WAIT_MINGGU'

    elif query.data == "cek_konsekuensi":
        cursor.execute("SELECT value FROM settings WHERE key='konsekuensi'")
        kons = cursor.fetchone()[0]
        await query.message.reply_text(f"Hukuman telat absen:\n\n{kons} 📑")

    elif query.data == "leaderboard_bbc":
        cursor.execute("SELECT username, points FROM users ORDER BY points DESC LIMIT 5")
        rows = cursor.fetchall()
        text = "🏆 *JUARA CINNA**🏆\n\n"
        for i, row in enumerate(rows, 1):
            bonus = " (+50 pts)" if i <=3 else " (+25 pts)"
            text += f"{i}. @{row[0]} — {row[1]} pts{bonus}\n"
        await query.message.reply_text(text)

    elif query.data == "back_start":
        await start(update, context)

# ================= CORE LOGIC =================

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    state = context.user_data.get('state')

    # --- SENIN LOGIC ---
    if state == 'WAIT_SENIN':
        lines = update.message.text.strip().split("\n")
        usernames = [u.strip().lower() for u in lines if "@" in u]
        errors = []

        if len(usernames) < 25: errors.append("Jumlah username kurang dari 25.")
        if len(usernames) != len(set(usernames)): errors.append("Ada username double (-2 point).")
        
        for u in usernames:
            uname = u.replace("@", "").split()[0]
            cursor.execute("SELECT username FROM used_usernames WHERE username=?", (uname,))
            if cursor.fetchone(): errors.append(f"{u} sudah pernah digunakan.")
            
            cursor.execute("SELECT join_time FROM join_logs WHERE username=?", (uname,))
            row = cursor.fetchone()
            if not row: errors.append(f"{u} bukan member baru.")
            elif datetime.now(TIMEZONE) - datetime.fromisoformat(row[0]) > timedelta(days=1):
                errors.append(f"{u} join > 24 jam (-1 point).")

        if errors:
            await update.message.reply_text(f"Aduh 😿 Ada kesalahan:\n\n" + "\n".join(errors))
            return

        # Success Senin
        points = 50 + (len(usernames) - 25)
        cursor.execute("UPDATE users SET senin=1, points=points+?, total_absen=total_absen+1 WHERE user_id=?", (points, user.id))
        for u in usernames:
            cursor.execute("INSERT INTO used_usernames (username, used_by) VALUES (?, ?)", (u.replace("@",""), user.id))
        db.commit()
        await update.message.reply_text(f"Absensi di hari Senin Berhasil! Poin +{points}. Terimakasih! 🩵")
        context.user_data['state'] = None

    # --- JUMAT LOGIC ---
    elif state == 'WAIT_JUMAT' and update.message.photo:
        caption = f"Jaseb Jumat: @{user.username}\nID: `{user.id}`\nMaster reply /done 💭"
        await context.bot.send_photo(LOG_GROUP_ID, update.message.photo[-1].file_id, caption=caption)
        await update.message.reply_text("Bukti terkirim! Menunggu Master konfirmasi... 🎀")
        context.user_data['state'] = None

    # --- MINGGU LOGIC ---
    elif state == 'WAIT_MINGGU':
        links = re.findall(r'http[s]?://\S+', update.message.text)
        cursor.execute("SELECT value FROM settings WHERE key='keyword'")
        keyword = cursor.fetchone()[0]
        
        if len(links) >= 20 and keyword.lower() in update.message.text.lower():
            cursor.execute("UPDATE users SET minggu=1, total_absen=total_absen+1 WHERE user_id=?", (user.id,))
            db.commit()
            await update.message.reply_text(f"Absensi Minggu Berhasil! @{user.username} sudah absen sebanyak {user.id} kali. 🩵")
        else:
            await update.message.reply_text("Gagal! Link kurang dari 20 atau keyword salah. ❌")
        context.user_data['state'] = None

# ================= OWNER COMMANDS =================

async def owner_done(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id != LOG_GROUP_ID: return
    reply = update.message.reply_to_message
    if not reply or not reply.caption: return
    
    target_id = int(re.search(r'ID: `(\d+)`', reply.caption).group(1))
    
    if update.message.text.startswith('/done'):
        cursor.execute("UPDATE users SET jumat=1, total_absen=total_absen+1 WHERE user_id=?", (target_id,))
        db.commit()
        # Notif Ke User
        text = f"Jaseb Jumat kamu sudah di-done Master! 🩵\n\nJumat: ✅\nMakin rajin ya! 🧁"
        await context.bot.send_message(target_id, text)
        await update.message.reply_text("Konfirmasi sukses! ✅")

    elif update.message.text.startswith('/valid'):
        reason = update.message.text.split(',', 1)[1] if ',' in update.message.text else "Gambar buram"
        cursor.execute("UPDATE users SET points=points-1 WHERE user_id=?", (target_id,))
        db.commit()
        await context.bot.send_message(target_id, f"kringg, pesan dari master : {reason}.\n\notomatis pengurangan point -1")

# ================= APP START =================

def main():
    app = ApplicationBuilder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(ChatMemberHandler(track_join, ChatMemberHandler.CHAT_MEMBER))
    app.add_handler(CallbackQueryHandler(callback_handler))
    app.add_handler(CommandHandler(["done", "valid"], owner_done))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(MessageHandler(filters.PHOTO, handle_message))

    print("CinnaBot Running... 🩵")
    app.run_polling()

if __name__ == "__main__":
    main()

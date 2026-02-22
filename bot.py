import sqlite3
import logging
import re
import pytz
import asyncio
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
    total_absen INTEGER DEFAULT 0,
    total_bc INTEGER DEFAULT 0
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

    markup = InlineKeyboardMarkup([
        [InlineKeyboardButton("🧁 Pilih Absen", callback_data="pilih_absen")],
        [InlineKeyboardButton("🏆 Leaderboard", callback_data="leaderboard_bbc"), 
         InlineKeyboardButton("💌 Tanya Cinna", callback_data="tanya_owner")],
        [InlineKeyboardButton("📜 Konsekuensi", callback_data="cek_konsekuensi")]
    ])

    cursor.execute("SELECT COUNT(*) FROM users WHERE senin=1 OR jumat=1 OR minggu=1")
    done = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM users WHERE senin=0 AND jumat=0 AND minggu=0")
    belum = cursor.fetchone()[0]

    text = f"Halo Kakak manis! {get_greeting()}, @{username}. Senang banget deh bisa ketemu! 🧁.\n\n" \
            f"<b>Status Absen Pekan Ini:</b>\n" \
            f"✅ Done: {done}\n" \
            f"⛔ Belum: {belum}\n\n" \
            f"<i>Yuk, jangan lupa absen biar Master @{OWNER_USERNAME} nggak sedih! ☁️</i>"

    if update.message:
        await update.message.reply_text(text, parse_mode="HTML", reply_markup=markup)
    else:
        await update.callback_query.edit_message_text(text, parse_mode="HTML", reply_markup=markup)

async def cek_absen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    cursor.execute("SELECT senin, jumat, minggu, points FROM users WHERE user_id=?", (user.id,))
    row = cursor.fetchone()

    if not row:
        await update.message.reply_text("Data kamu belum terdaftar, yuk klik /start dulu! ✨")
        return

    senin, jumat, minggu, points = row
    s_status = "✅ Done" if senin else "⛔ Belum"
    j_status = "✅ Done" if jumat else "⛔ Belum"
    m_status = "✅ Done" if minggu else "⛔ Belum"

    text = (
        f"🎀 Status Absen 1 Pekan 🎀\n"
        f"Nama: @{user.username}\n\n"
        f"🗓 Senin: {s_status}\n"
        f"🗓 Jumat: {j_status}\n"
        f"🗓 Minggu: {m_status}\n\n"
        f"💰 Total Poin: {points} pts\n\n"
        f"<i>Jangan lupa absen ya!</i> ☁️"
    )
    await update.message.reply_text(text, parse_mode="HTML")

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
        await query.edit_message_text("Uwaaa! Semangat banget sih mau absen! 🍬\nSilakan pilih menu absennya di bawah ya! 🎀👇", reply_markup=markup)

    elif query.data == "form_senin":
        if datetime.now(TIMEZONE).weekday() != 0:
            await query.message.reply_text("Maaf ya, absen Senin cuma bisa dilakukan di hari Senin! 🧁")
            return
        await query.message.reply_text("Silahkan kirim list 25 username barunya yaa! @\nContoh:\n1. @user\n2. @user\n...")
        context.user_data['state'] = 'WAIT_SENIN'

    elif query.data == "form_jumat":
        if datetime.now(TIMEZONE).weekday() != 4:
            await query.message.reply_text("Eits! Balik lagi pas hari Jumat ya manis! 📸🍭")
            return
        await query.message.reply_text("📸 Mana nih foto grid jaseb-nya? Kirim ke Cinna ya! 🍭")
        context.user_data['state'] = 'WAIT_JUMAT'

    elif query.data == "form_minggu":
        if datetime.now(TIMEZONE).weekday() != 6:
            await query.message.reply_text("Sabar ya Kak, absen Minggu cuma dibuka hari Minggu! 🎀")
            return
        await query.message.reply_text("Waktunya laporan Minggu! 💭\nTulis laporan link menfess Kakak di bawah ya. 🤭")
        context.user_data['state'] = 'WAIT_MINGGU'

    elif query.data == "cek_konsekuensi":
        cursor.execute("SELECT value FROM settings WHERE key='konsekuensi'")
        kons = cursor.fetchone()[0]
        markup = InlineKeyboardMarkup([[InlineKeyboardButton("💌 Lapor Hukuman", callback_data="form_hukuman")]])
        await query.message.reply_text(f"Hukuman telat absen:\n\n{kons} 📑", reply_markup=markup)

    elif query.data == "form_hukuman":
        await query.message.reply_text("Silahkan kirim bukti/laporan hukuman Kakak di sini ya! 🥺🩵")
        context.user_data['state'] = 'WAIT_HUKUMAN'
        
    elif query.data == "leaderboard_bbc":
        cursor.execute("SELECT username, points FROM users ORDER BY points DESC LIMIT 5")
        rows = cursor.fetchall()
        text = "🏆 JUARA DI HATI CINNA 🏆\n\n"
        for i, row in enumerate(rows, 1):
            text += f"{i}. @{row[0]} — {row[1]} pts\n"
        await query.message.reply_text(text)

    elif query.data == "tanya_owner":
        await query.message.reply_text("Tulis pesanmu untuk Master di sini ya...")
        context.user_data['state'] = 'WAIT_TANYA'
        
    elif query.data == "back_start":
        await start(update, context)

# ================= CORE LOGIC =================

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    state = context.user_data.get('state')

    if state == 'WAIT_TANYA':
        text_pesan = update.message.text
        await context.bot.send_message(LOG_GROUP_ID, f"💌 *PESAN TANYA-CINNA*\nDari: @{user.username} (ID: `{user.id}`)\nIsi: {text_pesan}\n\n👉 Balas: `/jawab {user.id} [pesan]`")
        await update.message.reply_text("Pesanmu sudah Cinna sampaikan ke Master! ✨")
        context.user_data['state'] = None
        return
        
    elif state == 'WAIT_SENIN':
        lines = update.message.text.strip().split("\n")
        usernames = [u.strip().lower() for u in lines if "@" in u]
        errors = []
        if len(usernames) < 25: errors.append("Jumlah username kurang dari 25.")
        if len(usernames) != len(set(usernames)): errors.append("Ada username double.")
        
        for u in usernames:
            uname = u.replace("@", "").split()[0]
            cursor.execute("SELECT username FROM used_usernames WHERE username=?", (uname,))
            if cursor.fetchone(): errors.append(f"{u} sudah pernah digunakan.")
            cursor.execute("SELECT join_time FROM join_logs WHERE username=?", (uname,))
            row = cursor.fetchone()
            if row and (datetime.now(TIMEZONE) - datetime.fromisoformat(row[0]) > timedelta(days=1)):
                errors.append(f"{u} join > 24 jam.")

        if errors:
            await update.message.reply_text("Aduh 😿 Ada kesalahan:\n\n" + "\n".join(errors))
            return

        points = 50 + (len(usernames) - 25)
        cursor.execute("UPDATE users SET senin=1, points=points+?, total_absen=total_absen+1 WHERE user_id=?", (points, user.id))
        for u in usernames:
            cursor.execute("INSERT INTO used_usernames (username, used_by) VALUES (?, ?)", (u.replace("@",""), user.id))
        db.commit()
        await update.message.reply_text(f"Absensi Berhasil! Poin +{points}. 🩵")
        context.user_data['state'] = None

    elif state == 'WAIT_JUMAT' and update.message.photo:
        caption = f"Jaseb Jumat: @{user.username}\nID: `{user.id}`\nMaster reply /done 💭"
        await context.bot.send_photo(LOG_GROUP_ID, update.message.photo[-1].file_id, caption=caption)
        await update.message.reply_text("Bukti terkirim! Menunggu Master... 🎀")
        context.user_data['state'] = None

    elif state == 'WAIT_MINGGU':
        text_pesan = update.message.text
        caption = f"Absen Minggu: @{user.username}\nID: `{user.id}`\nIsi: {text_pesan}\n\nMaster reply /done 💭"
        await context.bot.send_message(LOG_GROUP_ID, caption)
        await update.message.reply_text("Laporan terkirim! Menunggu Master... 🎀")
        context.user_data['state'] = None

    elif state == 'WAIT_HUKUMAN':
        text_pesan = update.message.text
        caption = f"🚨 **LAPORAN HUKUMAN**\nDari: @{user.username}\nID: `{user.id}`\nIsi: {text_pesan}\n\nMaster reply `/hukuman_done` 💭"
        await context.bot.send_message(LOG_GROUP_ID, caption)
        await update.message.reply_text("Laporan hukuman terkirim! ✨")
        context.user_data['state'] = None
        
# ================= OWNER COMMANDS =================

async def owner_done(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id != LOG_GROUP_ID: return
    reply = update.message.reply_to_message
    if not reply or (not reply.caption and not reply.text): return
    source = reply.caption if reply.caption else reply.text
    match = re.search(r'ID: `(\d+)`', source)
    if not match: return
    target_id = int(match.group(1))

    if update.message.text.startswith('/done'):
        hari = "Minggu" if "Minggu" in source else "Jumat"
        db_col = "minggu" if "Minggu" in source else "jumat"
        cursor.execute(f"UPDATE users SET {db_col}=1, total_absen=total_absen+1 WHERE user_id=?", (target_id,))
        db.commit()
        await context.bot.send_message(target_id, f"Absen {hari} kamu sudah di-done Master! ✅\nMakin rajin ya! 🧁")
        await update.message.reply_text("Konfirmasi sukses! ✅")
    elif update.message.text.startswith('/valid'):
        cursor.execute("UPDATE users SET points=points-1 WHERE user_id=?", (target_id,))
        db.commit()
        await context.bot.send_message(target_id, "Laporan tidak valid. Pengurangan poin -1.")
        await update.message.reply_text("Dibatalkan! ✅")

async def hukuman_done(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id != LOG_GROUP_ID: return
    reply = update.message.reply_to_message
    if not reply or (not reply.caption and not reply.text): return
    source = reply.caption if reply.caption else reply.text
    match = re.search(r'ID: `(\d+)`', source)
    if not match: return
    target_id = int(match.group(1))
    await context.bot.send_message(target_id, "🩵 Hukuman kamu sudah diterima Master! Status aman (Poin tetap). ✅")
    await update.message.reply_text("Hukuman diverifikasi! ✅")

async def ubah_poin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID: return
    if len(context.args) < 2: return
    target_id, jumlah = context.args[0], int(context.args[1])
    cursor.execute("UPDATE users SET points = points + ? WHERE user_id = ?", (jumlah, target_id))
    db.commit()
    await update.message.reply_text(f"Poin user {target_id} berhasil diupdate! ✨")

async def jawab_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id != LOG_GROUP_ID and update.effective_user.id != OWNER_ID: return
    if len(context.args) < 2: return
    target_id, pesan = context.args[0], " ".join(context.args[1:])
    await context.bot.send_message(target_id, f"🎀 - *Jawaban Master:*\n\n{pesan}")
    await update.message.reply_text("Terkirim! ✅")

async def broadcast_owner(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID: return
    pesan = " ".join(context.args)
    cursor.execute("SELECT user_id FROM users")
    users = cursor.fetchall()
    for u in users:
        try: await context.bot.send_message(u[0], pesan)
        except: continue
    await update.message.reply_text("Broadcast selesai! 📢")

# ================= APP START =================

async def set_commands(app):
    await app.bot.set_my_commands([("start", "Memulai bot! ✨"), ("cek", "Cek absen pekanan 📑")])

def main():
    app = ApplicationBuilder().token(TOKEN).build()
    
    # Setup Commands
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(set_commands(app))
    except: pass
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("cek", cek_absen))
    app.add_handler(CommandHandler("jawab", jawab_user))
    app.add_handler(CommandHandler("poin", ubah_poin))
    app.add_handler(CommandHandler("bc", broadcast_owner))
    app.add_handler(ChatMemberHandler(track_join, ChatMemberHandler.CHAT_MEMBER))
    app.add_handler(CallbackQueryHandler(callback_handler))
    app.add_handler(CommandHandler(["done", "valid"], owner_done))
    app.add_handler(CommandHandler("hukuman_done", hukuman_done))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(MessageHandler(filters.PHOTO, handle_message))
    
    print("CinnaBot Running... 🩵")
    app.run_polling()

if __name__ == "__main__":
    main()

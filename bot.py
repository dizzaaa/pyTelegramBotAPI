import telebot
from telebot import types
import datetime
import re

# --- CONFIGURATION ---
TOKEN = "8557455338:AAEYVbutR1kgm0pyG0u8lf7BL1EtLHhXecw"
OWNER_ID = 8007886767  # ID @cinnamoroiLi
LOG_GROUP_ID = -5151128223 
CHANNEL_USERNAME = "@RekberEloise"

bot = telebot.TeleBot(TOKEN)

# Database sederhana (Dalam produksi nyata, gunakan SQLite/MongoDB)
user_data = {} 
settings = {"keyword": "mangga", "konsekuensi": "Belum diatur oleh Master."}

def get_greeting():
    hour = datetime.datetime.now().hour
    if 5 <= hour < 12: return "Selamat Pagi 🌅"
    elif 12 <= hour < 15: return "Selamat Siang ☀️"
    elif 15 <= hour < 18: return "Selamat Sore ☁️"
    else: return "Selamat Malam 🌙"

# --- HANDLERS ---

@bot.message_handler(commands=['start'])
def start_handler(message):
    name = message.from_user.first_name
    username = f"@{message.from_user.username}" if message.from_user.username else name
    
    # Bubble 1
    bot.send_message(message.chat.id, f"Bot by @cinnamoroiLi, Hellow bellow {username}! 🫧")
    
    # Bubble 2
    markup = types.InlineKeyboardMarkup()
    btn_absen = types.InlineKeyboardButton("✨ Absen Sekarang ✨", callback_data="pilih_absen")
    btn_bbc = types.InlineKeyboardButton("🏆 Leaderboard", callback_data="leaderboard")
    btn_tanya = types.InlineKeyboardButton("☁️ Tanya CinnaBot", callback_data="tanya_owner")
    markup.add(btn_absen)
    markup.add(btn_bbc, btn_tanya)

    text = f"{get_greeting()}, {username}.\n\n" \
           f"<b>Broadcast hari ini :</b> -\n" \
           f"<b>Broadcast 1 pekan :</b> -\n" \
           f"<i>Broadcast tertinggi : Senin, 150 Absen</i> ☁️"
    
    bot.send_message(message.chat.id, text, parse_mode="HTML", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: True)
def callback_listener(call):
    if call.data == "pilih_absen":
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("Senin: Upsubs 25s", callback_data="absen_senin"))
        markup.add(types.InlineKeyboardButton("Jumat: Jaseb 50 Lpm", callback_data="absen_jumat"))
        markup.add(types.InlineKeyboardButton("Minggu: Send mf 20x", callback_data="absen_minggu"))
        markup.add(types.InlineKeyboardButton("⬅️ Kembali", callback_data="back_home"))
        
        bot.edit_message_text("Silahkan Pilih Absen, Untuk Reminder 🎀", call.message.chat.id, call.message.message_id, reply_markup=markup)

    elif call.data == "absen_senin":
        msg = bot.send_message(call.message.chat.id, "Silahkan kirim list 25 username @\n(Kirim dalam 1 bubble chat ya sayang! 🩵)")
        bot.register_next_step_handler(msg, process_upsubs)

    elif call.data == "back_home":
        start_handler(call.message)

# --- LOGIC ABSENSI ---

def process_upsubs(message):
    # Regex untuk mencari username
    usernames = re.findall(r'@\w+', message.text)
    unique_users = set(usernames)
    
    if len(usernames) < 25:
        bot.reply_to(message, "Yahhh, listnya kurang dari 25 nih... 🥺 Coba lagi ya!")
        return

    # Cek duplikat
    if len(unique_users) < len(usernames):
        bot.reply_to(message, f"Ih, ada username double! 😠 Poin kamu -2 ya.")
        return

    # Simulasi pengecekan channel (Logic aslinya butuh bot jadi admin di channel)
    bot.reply_to(message, f"Absensi Senin Berhasil! {len(usernames)} username terdeteksi. Master akan mengeceknya! 🩵")

# --- FITUR OWNER ---

@bot.message_handler(commands=['setkeyword'])
def set_key(message):
    if message.from_user.id == OWNER_ID:
        new_key = message.text.split(maxsplit=1)[1]
        settings['keyword'] = new_key
        bot.reply_to(message, f"Keyword berhasil diganti jadi: {new_key} 🍭")

@bot.message_handler(commands=['done', 'valid'])
def handle_approval(message):
    if message.from_user.id == OWNER_ID:
        # Logika forward dan approval di sini
        pass

# Fitur Tanya Cinna (Relay)
@bot.callback_query_handler(func=lambda call: call.data == "tanya_owner")
def ask_owner(call):
    msg = bot.send_message(call.message.chat.id, "Mau tanya apa ke Master? Tulis di bawah ya! 💌")
    bot.register_next_step_handler(msg, forward_to_owner)

def forward_to_owner(message):
    bot.send_message(OWNER_ID, f"💌 *Pesan dari @{message.from_user.username}:*\n{message.text}")
    bot.reply_to(message, "Pesanmu sudah terkirim ke Master! Ditunggu ya jawabannya... ✨")

bot.infinity_polling()

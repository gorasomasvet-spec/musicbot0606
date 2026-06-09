import os
import telebot
from telebot import types
import yt_dlp
import database as db

# Получаем токен из переменных окружения Railway
API_TOKEN = os.environ.get('BOT_TOKEN')

# Если тестируешь локально, можешь временно раскомментировать строку ниже:
# API_TOKEN = 'СЮДА_ТОКЕН'

if not API_TOKEN:
    print("Ошибка: Укажи BOT_TOKEN в переменных Railway.")
    exit(1)

bot = telebot.TeleBot(API_TOKEN)
db.init_db()

# Временный кэш: file_id -> Название трека
songs_cache = {}

# Список популярных исполнителей СНГ
POPULAR_CIS_TRACKS = [
    "Miyagi & Эндшпиль",
    "Macan",
    "A.V.G",
    "Jakone",
    "Xcho",
    "Скриптонит",
    "Jony"
]

def main_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    btn_find = types.KeyboardButton("🔍 Найти песню")
    btn_popular = types.KeyboardButton("🔥 Популярное")
    btn_history = types.KeyboardButton("📜 История")
    btn_playlist = types.KeyboardButton("🎵 Мой плейлист")
    
    markup.add(btn_find, btn_popular)
    markup.add(btn_history, btn_playlist)
    return markup

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    bot.send_message(
        message.chat.id, 
        "Привет! Я твой скоростной музыкальный бот.\nИщи любые песни, открывай 'Популярное' и собирай плейлист!", 
        reply_markup=main_menu()
    )

@bot.message_handler(func=lambda message: True)
def handle_menu(message):
    if message.text == "🔍 Найти песню":
        msg = bot.send_message(message.chat.id, "Введите название песни или исполнителя:")
        bot.register_next_step_handler(msg, search_and_send_song)
        
    elif message.text == "🔥 Популярное":
        markup = types.InlineKeyboardMarkup(row_width=1)
        for artist in POPULAR_CIS_TRACKS:
            markup.add(types.InlineKeyboardButton(text=f"🎵 {artist}", callback_data=f"search_pop:{artist}"))
        bot.send_message(message.chat.id, "🔥 Популярные исполнители и треки в СНГ:", reply_markup=markup)
        
    elif message.text == "📜 История":
        history = db.get_history(message.from_user.id)
        if history:
            text = "Ваша история последних запросов:\n\n" + "\n".join([f"• {q}" for q in history])
        else:
            text = "Ваша история поиска пуста."
        bot.send_message(message.chat.id, text, reply_markup=main_menu())
        
    elif message.text == "🎵 Мой плейлист":
        playlist = db.get_playlist(message.from_user.id)
        if not playlist:
            bot.send_message(message.chat.id, "Ваш плейлист пуст. Нажмите «➕» под любой найденной песней.")
            return
            
        bot.send_message(message.chat.id, "📂 Открываю ваш плейлист...")
        
        # Моментальная отправка по file_id БЕЗ ПОВТОРНОГО СКАЧИВАНИЯ
        for track in playlist:
            track_id, title, file_id = track
            
            inline_kb = types.InlineKeyboardMarkup()
            btn_dots = types.InlineKeyboardButton("•••", callback_data=f"dots_{track_id}")
            inline_kb.add(btn_dots)
            
            try:
                bot.send_audio(message.chat.id, file_id, caption=title, reply_markup=inline_kb)
            except Exception:
                bot.send_message(message.chat.id, f"Не удалось загрузить трек: {title}")

# Скоростная функция поиска через yt-dlp
def search_and_send_song(message, query_text=None):
    query = query_text if query_text else message.text
    
    if not query_text and query in ["🔍 Найти песню", "🔥 Популярное", "📜 История", "🎵 Мой плейлист"]:
        handle_menu(message)
        return

    status_msg = bot.send_message(message.chat.id, "🚀 Ищу трек на максимальной скорости...")
    db.add_to_history(message.from_user.id, query)

    # Ультра-скоростные настройки поиска: ищем только аудио, берем 1-й результат
    ydl_opts = {
        'format': 'bestaudio/best',
        'default_search': 'ytsearch1',
        'outtmpl': '%(id)s.%(ext)s',
        'noplaylist': True,
        'quiet': True,
        'no_warnings': True,
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(query, download=True)
            if 'entries' in info and len(info['entries']) > 0:
                video_info = info['entries'][0]
            else:
                video_info = info
            
            title = video_info.get('title', 'Аудио трек')
            filename = f"{video_info['id']}.mp3"

        if os.path.exists(filename):
            bot.delete_message(message.chat.id, status_msg.message_id)
            
            # Кнопка ПЛЮС
            inline_kb = types.InlineKeyboardMarkup()
            btn_add = types.InlineKeyboardButton("➕ Добавить в плейлист", callback_data="add_to_pl")
            inline_kb.add(btn_add)
            
            # Отправка MP3 в Телеграм
            with open(filename, 'rb') as audio:
                sent_audio = bot.send_audio(message.chat.id, audio, caption=title, reply_markup=inline_kb)
            
            # Кэшируем file_id
            songs_cache[sent_audio.audio.file_id] = title
            
            # Очищаем диск на Railway
            os.remove(filename)
        else:
            bot.edit_message_text("❌ Ошибка при обработке аудио.", message.chat.id, status_msg.message_id)

    except Exception as e:
        print(f"Ошибка поиска: {e}")
        bot.delete_message(message.chat.id, status_msg.message_id)
        bot.send_message(message.chat.id, "❌ Не удалось найти или скачать этот трек.")

# Обработка инлайн-кнопок
@bot.callback_query_handler(func=lambda call: True)
def callback_listener(call):
    # Поиск из раздела Популярное
    if call.data.startswith("search_pop:"):
        artist_name = call.data.split(":")[1]
        bot.answer_callback_query(call.id, f"Поиск: {artist_name}")
        search_and_send_song(call.message, query_text=artist_name)
        
    # Кнопка Плюс (Добавить в плейлист)
    elif call.data == "add_to_pl":
        file_id = call.message.audio.file_id
        title = songs_cache.get(file_id, call.message.caption or "Любимый трек")
        
        db.add_to_playlist(call.from_user.id, title, file_id)
        bot.answer_callback_query(call.id, "✅ Добавлено в Мой плейлист!")
        
    # Кнопка Три точки в плейлисте
    elif call.data.startswith("dots_"):
        track_id = call.data.split("_")[1]
        
        inline_kb = types.InlineKeyboardMarkup()
        btn_delete = types.InlineKeyboardButton("🗑️ Убрать песню", callback_data=f"delete_{track_id}")
        inline_kb.add(btn_delete)
        
        bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=inline_kb)
        bot.answer_callback_query(call.id)
        
    # Кнопка "Убрать песню"
    elif call.data.startswith("delete_"):
        track_id = call.data.split("_")[1]
        db.remove_from_playlist(track_id)
        
        bot.delete_message(call.message.chat.id, call.message.message_id)
        bot.answer_callback_query(call.id, "❌ Удалено из плейлиста.")

if __name__ == '__main__':
    bot.infinity_polling()
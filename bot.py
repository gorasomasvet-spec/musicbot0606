import os
import telebot
from telebot import types
from sclib import SoundcloudAPI
import database as db

API_TOKEN = os.getenv("BOT_TOKEN")
bot = telebot.TeleBot(API_TOKEN)

# Инициализируем БД
db.init_db()

# Глобальный клиент SoundCloud API для быстрого поиска
sc_api = SoundcloudAPI()

# Временный кэш для сопоставления file_id -> название трека при нажатии кнопки Плюс
songs_cache = {}

# Список популярных СНГ треков/запросов для кнопки "Популярное"
POPULAR_CIS_TRACKS = [
    "Miyagi & Эндшпиль",
    "Macan",
    "A.V.G",
    "Jakone",
    "Xcho",
    "Скриптонит",
    "Jony"
]

# Главное меню с кнопками
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
        "Привет! Я твой скоростной музыкальный бот на базе SoundCloud.", 
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
            # Создаем быстрые кнопки для мгновенного поиска популярных артистов
            markup.add(types.InlineKeyboardButton(text=f"🎵 {artist}", callback_data=f"search_pop:{artist}"))
        bot.send_message(message.chat.id, "🔥 Популярные исполнители и треки в СНГ сейчас:", reply_markup=markup)
        
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
            bot.send_message(message.chat.id, "Ваш плейлист пуст. Нажмите «➕» под найденной песней.")
            return
            
        bot.send_message(message.chat.id, "📂 Открываю ваш плейлист...")
        
        # Пересылаем песни по file_id из базы данных (без повторного скачивания!)
        for track in playlist:
            track_id, title, file_id = track
            
            # Инлайн-кнопка "Три точки"
            inline_kb = types.InlineKeyboardMarkup()
            btn_dots = types.InlineKeyboardButton("•••", callback_data=f"dots_{track_id}")
            inline_kb.add(btn_dots)
            
            try:
                bot.send_audio(message.chat.id, file_id, caption=title, reply_markup=inline_kb)
            except Exception:
                bot.send_message(message.chat.id, f"Ошибка загрузки трека: {title}")

# Логика поиска через SoundCloud
def search_and_send_song(message, query_text=None):
    query = query_text if query_text else message.text
    
    # Защита от перехвата системных кнопок меню
    if not query_text and query in ["🔍 Найти песню", "🔥 Популярное", "📜 История", "🎵 Мой плейлист"]:
        handle_menu(message)
        return

    status_msg = bot.send_message(message.chat.id, "🚀 Ищу на SoundCloud, секунду...")
    db.add_to_history(message.from_user.id, query)

    try:
        # Быстрый поиск треков через soundcloud-lib
        # Передаем поисковый запрос во внутренний метод библиотеки
        search_results = sc_api.search_tracks(query)
        
        if not search_results:
            bot.edit_message_text("❌ Ничего не найдено по этому запросу.", message.chat.id, status_msg.message_id)
            return
            
        # Берем самый первый и релевантный трек
        track = next(search_results, None)
        if not track:
            bot.edit_message_text("❌ Трек не найден.", message.chat.id, status_msg.message_id)
            return

        title = f"{track.artist} - {track.title}"
        filename = f"{track.id}.mp3" # Сохраняем временно под ID трека

        # Скачиваем напрямую MP3 поток с серверов SoundCloud
        with open(filename, 'wb+') as fp:
            track.write_mp3_to(fp)

        if os.path.exists(filename):
            bot.delete_message(message.chat.id, status_msg.message_id)
            
            # Кнопка ПЛЮС для добавления в плейлист
            inline_kb = types.InlineKeyboardMarkup()
            btn_add = types.InlineKeyboardButton("➕ Добавить в плейлист", callback_data="add_to_pl")
            inline_kb.add(btn_add)
            
            # Отправка аудио в формате MP3
            with open(filename, 'rb') as audio:
                sent_audio = bot.send_audio(message.chat.id, audio, caption=title, reply_markup=inline_kb)
            
            # Фиксируем file_id в кэше
            songs_cache[sent_audio.audio.file_id] = title
            
            # Удаляем локальный файл, очищая диск на Railway
            os.remove(filename)
        else:
            bot.edit_message_text("❌ Ошибка при формировании MP3.", message.chat.id, status_msg.message_id)

    except Exception as e:
        print(f"SoundCloud Error: {e}")
        bot.delete_message(message.chat.id, status_msg.message_id)
        bot.send_message(message.chat.id, "❌ Произошла ошибка при поиске трека.")

# Обработчик инлайн-нажатий (кнопки под сообщениями)
@bot.callback_query_handler(func=lambda call: True)
def callback_listener(call):
    # Нажатие на популярный трек
    if call.data.startswith("search_pop:"):
        artist_name = call.data.split(":")[1]
        bot.answer_callback_query(call.id, f"Ищу треки: {artist_name}")
        search_and_send_song(call.message, query_text=artist_name)
        
    # Добавление в плейлист (кнопка Плюс)
    elif call.data == "add_to_pl":
        file_id = call.message.audio.file_id
        title = songs_cache.get(file_id, call.message.caption or "Любимый трек")
        
        db.add_to_playlist(call.from_user.id, title, file_id)
        bot.answer_callback_query(call.id, "✅ Песня добавлена в Мой плейлист!")
        
    # Кнопка "Три точки" в плейлисте
    elif call.data.startswith("dots_"):
        track_id = call.data.split("_")[1]
        
        # Меняем три точки на кнопку "Убрать песню"
        inline_kb = types.InlineKeyboardMarkup()
        btn_delete = types.InlineKeyboardButton("🗑️ Убрать песню", callback_data=f"delete_{track_id}")
        inline_kb.add(btn_delete)
        
        bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=inline_kb)
        bot.answer_callback_query(call.id)
        
    # Кнопка "Убрать песню"
    elif call.data.startswith("delete_"):
        track_id = call.data.split("_")[1]
        db.remove_from_playlist(track_id)
        
        # Полностью удаляем сообщение из чата, так как песня убрана
        bot.delete_message(call.message.chat.id, call.message.message_id)
        bot.answer_callback_query(call.id, "❌ Удалено из плейлиста.")

if __name__ == '__main__':
    bot.infinity_polling()
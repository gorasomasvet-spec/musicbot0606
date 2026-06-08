import asyncio
import os

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import (
    Message,
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    CallbackQuery
)

from music import search_music

BOT_TOKEN = os.getenv("BOT_TOKEN")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

history = {}
playlists = {}

menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🔍 Найти песню")],
        [KeyboardButton(text="📜 История")],
        [KeyboardButton(text="🎵 Мой плейлист")]
    ],
    resize_keyboard=True
)

@dp.message(Command("start"))
async def start(message: Message):
    await message.answer(
        "🎵 Music Bot\n\nВыберите действие:",
        reply_markup=menu
    )

@dp.message(F.text == "🔍 Найти песню")
async def search_button(message: Message):
    await message.answer(
        "Введите название песни:"
    )

@dp.message(F.text == "📜 История")
async def show_history(message: Message):
    user_id = message.from_user.id

    if user_id not in history or not history[user_id]:
        await message.answer("История пуста")
        return

    await message.answer(
        "📜 История:\n\n" +
        "\n".join(history[user_id])
    )

@dp.message(F.text == "🎵 Мой плейлист")
async def show_playlist(message: Message):
    user_id = message.from_user.id

    if user_id not in playlists or not playlists[user_id]:
        await message.answer("🎵 Плейлист пуст")
        return

    text = "🎵 Мой плейлист:\n\n"

    for song in playlists[user_id]:
        text += f"• {song}\n"

    await message.answer(text)

@dp.callback_query(F.data.startswith("add:"))
async def add_song(callback: CallbackQuery):
    title = callback.data[4:]

    user_id = callback.from_user.id

    if user_id not in playlists:
        playlists[user_id] = []

    if title not in playlists[user_id]:
        playlists[user_id].append(title)

    await callback.message.answer(
        f"✅ Добавлено:\n{title}"
    )

    await callback.answer()

@dp.message()
async def search_song(message: Message):
    user_id = message.from_user.id

    if user_id not in history:
        history[user_id] = []

    history[user_id].append(message.text)

    try:
        tracks = search_music(message.text)

        if not tracks:
            await message.answer(
                "Ничего не найдено"
            )
            return

        for track in tracks:

            kb = InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text="➕ Добавить",
                            callback_data=f"add:{track['title'][:40]}"
                        )
                    ]
                ]
            )

            await message.answer(
                f"🎵 {track['title']}",
                reply_markup=kb
            )

    except Exception as e:
        await message.answer(
            f"Ошибка поиска:\n{e}"
        )

async def main():
    me = await bot.get_me()
    print(f"Авторизован как @{me.username}")

    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
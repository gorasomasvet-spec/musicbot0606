import asyncio
import os

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import (
    Message,
    ReplyKeyboardMarkup,
    KeyboardButton
)

BOT_TOKEN = os.getenv("BOT_TOKEN")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🔍 Найти песню")],
        [KeyboardButton(text="📜 История")],
        [KeyboardButton(text="🎵 Мой плейлист")]
    ],
    resize_keyboard=True
)

history = {}

@dp.message(Command("start"))
async def start(message: Message):
    await message.answer(
        "🎵 Music Bot\n\nВыберите действие:",
        reply_markup=menu
    )

@dp.message(F.text == "🔍 Найти песню")
async def search_song(message: Message):
    await message.answer(
        "Напиши название песни:"
    )

@dp.message(F.text == "📜 История")
async def show_history(message: Message):
    user_id = message.from_user.id

    songs = history.get(user_id, [])

    if not songs:
        await message.answer("История пуста")
        return

    text = "\n".join(songs)

    await message.answer(
        f"📜 История:\n\n{text}"
    )

@dp.message(F.text == "🎵 Мой плейлист")
async def playlist(message: Message):
    await message.answer(
        "🎵 Пока плейлист пуст"
    )

@dp.message()
async def handle_text(message: Message):
    user_id = message.from_user.id

    if user_id not in history:
        history[user_id] = []

    history[user_id].append(message.text)

    await message.answer(
        f"🔎 Ищу песню: {message.text}"
    )

async def main():
    me = await bot.get_me()
    print(f"Авторизован как @{me.username}")

    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
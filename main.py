print("BOT STARTING...")
import asyncio
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command

from config import BOT_TOKEN
from db import connect, init, pool
from music import search_music

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# ---------- КНОПКИ ----------
menu = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="🔍 Найти песню", callback_data="search")],
    [InlineKeyboardButton(text="📜 История", callback_data="history")],
    [InlineKeyboardButton(text="🎵 Мой плейлист", callback_data="playlist")]
])

# ---------- START ----------
@dp.message(Command("start"))
async def start(message: Message):
    await message.answer("🎵 Music Bot", reply_markup=menu)

# ---------- ПОИСК ----------
@dp.callback_query(F.data == "search")
async def search(call: CallbackQuery):
    await call.message.answer("Напиши название песни")

# ---------- ИСТОРИЯ ----------
@dp.callback_query(F.data == "history")
async def history(call: CallbackQuery):
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT query FROM history WHERE user_id=$1",
            call.from_user.id
        )

    if not rows:
        await call.message.answer("История пустая")
        return

    text = "\n".join([r["query"] for r in rows])
    await call.message.answer(text)

# ---------- ПЛЕЙЛИСТ ----------
@dp.callback_query(F.data == "playlist")
async def playlist(call: CallbackQuery):
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT id, title FROM favorites WHERE user_id=$1",
            call.from_user.id
        )

    if not rows:
        await call.message.answer("Плейлист пуст")
        return

    for r in rows:
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⋯", callback_data=f"more_{r['id']}")]
        ])

        await call.message.answer(f"🎵 {r['title']}", reply_markup=kb)

# ---------- МЕНЮ У ТРЕКА ----------
@dp.callback_query(F.data.startswith("more_"))
async def more(call: CallbackQuery):
    track_id = call.data.split("_")[1]

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🗑 Удалить", callback_data=f"del_{track_id}")]
    ])

    await call.message.answer("Действия:", reply_markup=kb)

# ---------- УДАЛЕНИЕ ----------
@dp.callback_query(F.data.startswith("del_"))
async def delete(call: CallbackQuery):
    track_id = call.data.split("_")[1]

    async with pool.acquire() as conn:
        await conn.execute(
            "DELETE FROM favorites WHERE id=$1",
            int(track_id)
        )

    await call.message.answer("Удалено ❌")

# ---------- ОБРАБОТКА ТЕКСТА ----------
@dp.message()
async def handle_text(message: Message):
    results = search_music(message.text)

    async with pool.acquire() as conn:
        await conn.execute(
            "INSERT INTO history(user_id, query) VALUES($1,$2)",
            message.from_user.id,
            message.text
        )

    for r in results:
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="➕ Добавить", callback_data=f"add|{r['title']}|{r['url']}")]
        ])

        await message.answer(r["title"], reply_markup=kb)

# ---------- ДОБАВИТЬ В ПЛЕЙЛИСТ ----------
@dp.callback_query(F.data.startswith("add"))
async def add(call: CallbackQuery):
    _, title, url = call.data.split("|")

    async with pool.acquire() as conn:
        await conn.execute(
            "INSERT INTO favorites(user_id, title, url) VALUES($1,$2,$3)",
            call.from_user.id,
            title,
            url
        )

    await call.message.answer("Добавлено ✅")

# ---------- START APP ----------
async def main():
    await connect()
    await init()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
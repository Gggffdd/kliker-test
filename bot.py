import logging
from aiogram import Bot, Dispatcher, types
from aiogram.types import WebAppInfo, ReplyKeyboardMarkup, KeyboardButton
from aiogram.filters import Command
import sqlite3
import asyncio

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Инициализация бота
bot = Bot(token="87780179544:AAGGaZB4dOZFPKaBKYQtC9NfpHv3uwrFMyE")  # Замените на реальный токен!
dp = Dispatcher()

# Подключение к SQLite
conn = sqlite3.connect('notocoin.db')
cursor = conn.cursor()

# Создание таблицы игроков
cursor.execute('''
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    coins INTEGER DEFAULT 0,
    per_click INTEGER DEFAULT 1
)
''')
conn.commit()

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    user_id = message.from_user.id
    
    # Добавляем пользователя в БД
    cursor.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))
    conn.commit()
    
    # Создаем кнопку для Web App (правильный способ в aiogram 3.x)
    web_app_button = KeyboardButton(
        text="🎮 Открыть NFT-кликер",
        web_app=WebAppInfo(url="https://github.com/Gggffdd/kliker-test")  # Замените на ваш URL
    )
    
    markup = ReplyKeyboardMarkup(
        keyboard=[[web_app_button]],  # Теперь передаем список списков кнопок
        resize_keyboard=True
    )
    
    await message.answer(
        "Добро пожаловать в NFT-кликер!\n"
        "Нажмите кнопку ниже, чтобы начать.",
        reply_markup=markup
    )

async def main():
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())

import logging
from aiogram import Bot, Dispatcher, types
from aiogram.types import WebAppInfo, ReplyKeyboardMarkup, KeyboardButton
from aiogram.contrib.middlewares.logging import LoggingMiddleware
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import Command
import sqlite3
import json

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Инициализация бота
bot = Bot(token="ВАШ_TELEGRAM_BOT_TOKEN")  # Замените на ваш токен!
dp = Dispatcher(bot)
dp.middleware.setup(LoggingMiddleware())

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

# Команда /start
@dp.message_handler(Command("start"))
async def cmd_start(message: types.Message):
    user_id = message.from_user.id
    
    # Добавляем пользователя в БД, если его нет
    cursor.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))
    conn.commit()
    
    # Создаем кнопку для Web App
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    web_app_button = KeyboardButton(
        text="🎮 Открыть NFT-кликер",
        web_app=WebAppInfo(url="https://ВАШ_WEB_APP_URL.vercel.app")  # Замените на ваш URL!
    )
    markup.add(web_app_button)
    
    await message.answer(
        "Добро пожаловать в NFT-кликер!\n"
        "Нажми кнопку ниже, чтобы начать зарабатывать монеты.",
        reply_markup=markup
    )

# Обработка данных из Web App
@dp.message_handler(content_types=['web_app_data'])
async def handle_web_app_data(message: types.Message):
    user_id = message.from_user.id
    data = json.loads(message.web_app_data.data)
    
    if data['action'] == 'get_data':
        # Отправляем текущие данные игрока
        cursor.execute("SELECT coins, per_click FROM users WHERE user_id = ?", (user_id,))
        user_data = cursor.fetchone()
        if user_data:
            coins, per_click = user_data
            await bot.send_message(
                chat_id=message.chat.id,
                text=json.dumps({
                    'coins': coins,
                    'per_click': per_click
                }),
                reply_to_message_id=message.message_id
            )
    
    elif data['action'] == 'update':
        # Обновляем данные в БД
        coins = data.get('coins', 0)
        per_click = data.get('per_click', 1)
        cursor.execute(
            "UPDATE users SET coins = ?, per_click = ? WHERE user_id = ?",
            (coins, per_click, user_id)
        )
        conn.commit()

# Запуск бота
if __name__ == '__main__':
    from aiogram import executor
    executor.start_polling(dp, skip_updates=True)
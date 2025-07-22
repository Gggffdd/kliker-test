import os
import random
import logging
from flask import Flask, request, jsonify
import telebot
from telebot import types

# Настройка логгирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Инициализация Flask и бота
app = Flask(__name__)
bot = telebot.TeleBot(os.getenv('TELEGRAM_TOKEN'))

# Конфигурация
CONFIG = {
    'WEBHOOK_SECRET': os.getenv('WEBHOOK_SECRET', 'default_secret_key'),
    'VERCEL_URL': os.getenv('VERCEL_URL', 'https://kliker-test.vercel.app'),
    'INITIAL_BALANCE': 1000,
    'MIN_BET': 10,
    'MAX_BET': 1000
}

# Игровые данные
SLOT_SYMBOLS = ['🍒', '🍋', '🍇', '🍉', '🔔', '💎', '7️⃣', '🐶']
PAYOUTS = {
    '💎': {3: 5, 4: 20, 5: 100},
    '🐶': {3: 3, 4: 10, 5: 50},
    '7️⃣': {3: 2, 4: 7, 5: 25},
    '🔔': {3: 1, 4: 3, 5: 10}
}

# "База данных" в памяти
users_db = {}

@app.route('/')
def home():
    """Главная страница для проверки работы"""
    return "🎰 Dog House Slots Bot is Running! 🐶"

@app.route('/webhook', methods=['POST'])
def webhook():
    """Обработчик вебхука от Telegram"""
    # Проверка секретного ключа
    if request.headers.get('X-Telegram-Bot-Api-Secret-Token') != CONFIG['WEBHOOK_SECRET']:
        logger.warning("Unauthorized webhook attempt")
        return jsonify({"error": "Forbidden"}), 403

    try:
        update = telebot.types.Update.de_json(request.get_json())
        bot.process_new_updates([update])
        return jsonify({"status": "ok"}), 200
    except Exception as e:
        logger.error(f"Webhook processing error: {e}")
        return jsonify({"error": "Internal server error"}), 500

def get_user(user_id):
    """Получение или создание пользователя"""
    if user_id not in users_db:
        users_db[user_id] = {
            'balance': CONFIG['INITIAL_BALANCE'],
            'bet': 100
        }
    return users_db[user_id]

def create_keyboard(user_id):
    """Создание клавиатуры с действиями"""
    user = get_user(user_id)
    keyboard = types.InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        types.InlineKeyboardButton(
            text=f"🎰 Spin ({user['bet']})", 
            callback_data="spin"
        ),
        types.InlineKeyboardButton(
            text=f"💰 {user['balance']} coins", 
            callback_data="balance"
        ),
        types.InlineKeyboardButton(
            text="⚙️ Change Bet", 
            callback_data="change_bet"
        )
    )
    return keyboard

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    """Обработчик команды /start"""
    try:
        user = get_user(message.from_user.id)
        bot.send_message(
            message.chat.id,
            f"🐶 Welcome to Dog House Slots!\n\n"
            f"💰 Balance: {user['balance']} coins\n"
            f"🪙 Current bet: {user['bet']} coins\n\n"
            "Use the buttons below to play:",
            reply_markup=create_keyboard(message.from_user.id)
        )
    except Exception as e:
        logger.error(f"Start command error: {e}")

@bot.callback_query_handler(func=lambda call: call.data == 'spin')
def spin_handler(call):
    """Обработчик вращения слотов"""
    try:
        user = get_user(call.from_user.id)
        
        if user['balance'] < user['bet']:
            bot.answer_callback_query(call.id, "❌ Not enough coins!")
            return
        
        # Генерация результата
        result = [random.choice(SLOT_SYMBOLS) for _ in range(5)]
        win = calculate_win(result, user['bet'])
        user['balance'] += win - user['bet']
        
        # Ответ с результатом
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=f"🎰 {' '.join(result)}\n\n"
                 f"💎 Win: {win} coins\n"
                 f"💰 Balance: {user['balance']} coins",
            reply_markup=create_keyboard(call.from_user.id)
        )
        bot.answer_callback_query(call.id)
    except Exception as e:
        logger.error(f"Spin error: {e}")

def calculate_win(result, bet):
    """Расчет выигрыша"""
    win = 0
    for symbol in set(result):
        count = result.count(symbol)
        if symbol in PAYOUTS and count >= 3:
            win += bet * PAYOUTS[symbol][min(count, 5)]
    return win

@bot.callback_query_handler(func=lambda call: call.data == 'change_bet')
def change_bet_handler(call):
    """Обработчик изменения ставки"""
    try:
        user = get_user(call.from_user.id)
        keyboard = types.InlineKeyboardMarkup(row_width=3)
        keyboard.add(
            types.InlineKeyboardButton("-10", callback_data="bet_down"),
            types.InlineKeyboardButton(f"{user['bet']}", callback_data="bet_current"),
            types.InlineKeyboardButton("+10", callback_data="bet_up"),
            types.InlineKeyboardButton("🔙 Back", callback_data="menu_back")
        )
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=f"⚙️ Current bet: {user['bet']} coins\n"
                 f"Min: {CONFIG['MIN_BET']}, Max: {CONFIG['MAX_BET']}",
            reply_markup=keyboard
        )
    except Exception as e:
        logger.error(f"Change bet error: {e}")

@bot.callback_query_handler(func=lambda call: call.data.startswith('bet_'))
def bet_adjust_handler(call):
    """Обработчик изменения размера ставки"""
    try:
        user = get_user(call.from_user.id)
        action = call.data.split('_')[1]
        
        if action == 'up':
            user['bet'] = min(user['bet'] + 10, CONFIG['MAX_BET'])
        elif action == 'down':
            user['bet'] = max(user['bet'] - 10, CONFIG['MIN_BET'])
        
        change_bet_handler(call)
    except Exception as e:
        logger.error(f"Bet adjust error: {e}")

@bot.callback_query_handler(func=lambda call: call.data == 'menu_back')
def back_to_menu(call):
    """Возврат в главное меню"""
    try:
        user = get_user(call.from_user.id)
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=f"🐶 Dog House Slots\n\n"
                 f"💰 Balance: {user['balance']} coins\n"
                 f"🪙 Current bet: {user['bet']} coins",
            reply_markup=create_keyboard(call.from_user.id)
        )
    except Exception as e:
        logger.error(f"Back to menu error: {e}")

def setup_webhook():
    """Настройка вебхука"""
    try:
        bot.remove_webhook()
        bot.set_webhook(
            url=f"{CONFIG['VERCEL_URL']}/webhook",
            secret_token=CONFIG['WEBHOOK_SECRET'],
            drop_pending_updates=True
        )
        logger.info(f"Webhook set up for {CONFIG['VERCEL_URL']}")
    except Exception as e:
        logger.error(f"Webhook setup error: {e}")

# Инициализация при запуске
setup_webhook()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))

import os
import telebot
import random
import logging
from flask import Flask, request, jsonify
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

# Настройка логгирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Конфигурация из переменных окружения
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN', '7523520150:AAGMPibPAl8D0I0E6ZeNR3zuIp0qKcshXN0')
WEBHOOK_SECRET = os.environ.get('WEBHOOK_SECRET', 'd0gH0us3_S3cr3t_K3Y_2023_v2')
VERCEL_URL = os.environ.get('VERCEL_URL', 'https://kliker-test.vercel.app')

bot = telebot.TeleBot(TELEGRAM_TOKEN)
app = Flask(__name__)

# Мини-база данных в памяти (в реальном проекте используйте БД)
users_db = {}

# Символы для слотов и выплаты
SLOT_SYMBOLS = ['🍒', '🍋', '🍇', '🍉', '🔔', '💎', '7️⃣', '🐶']
PAYOUTS = {
    '💎': {3: 5, 4: 20, 5: 100},
    '🐶': {3: 3, 4: 10, 5: 50},
    '7️⃣': {3: 2, 4: 7, 5: 25},
    '🔔': {3: 1, 4: 3, 5: 10}
}

@app.route('/')
def home():
    return "🎰 Dog House Slots Bot is Running!"

@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        # Проверка секретного токена
        if request.headers.get('X-Telegram-Bot-Api-Secret-Token') != WEBHOOK_SECRET:
            logger.warning("Unauthorized webhook attempt")
            return jsonify({"error": "Forbidden"}), 403
        
        json_data = request.get_json()
        logger.info(f"Incoming update: {json_data}")
        
        update = telebot.types.Update.de_json(json_data)
        bot.process_new_updates([update])
        
        return jsonify({"status": "success"}), 200
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return jsonify({"error": "Internal Server Error"}), 500

def create_main_menu(user_id):
    user = users_db.get(user_id, {'balance': 1000, 'bet': 100})
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton(f"🎰 Spin ({user['bet']})", callback_data="spin"),
        InlineKeyboardButton("⚙️ Change Bet", callback_data="change_bet")
    )
    return markup

@bot.message_handler(commands=['start'])
def start(message):
    try:
        user_id = message.from_user.id
        if user_id not in users_db:
            users_db[user_id] = {'balance': 1000, 'bet': 100}
        
        user = users_db[user_id]
        bot.send_message(
            user_id,
            f"🐶 Welcome to Dog House Slots!\n\n"
            f"💰 Balance: {user['balance']} coins\n"
            f"🪙 Current bet: {user['bet']} coins",
            reply_markup=create_main_menu(user_id)
        )
    except Exception as e:
        logger.error(f"Start command error: {e}")

@bot.callback_query_handler(func=lambda call: call.data == 'spin')
def spin(call):
    try:
        user_id = call.from_user.id
        user = users_db.get(user_id)
        
        if not user:
            bot.answer_callback_query(call.id, "❌ User not found!")
            return
        
        if user['balance'] < user['bet']:
            bot.answer_callback_query(call.id, "❌ Not enough coins!")
            return
        
        # Генерация результата
        result = [random.choice(SLOT_SYMBOLS) for _ in range(5)]
        win = calculate_win(result, user['bet'])
        user['balance'] += win - user['bet']
        
        # Анимация вращения
        bot.answer_callback_query(call.id)
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text="🎰 Spinning... 🌀",
            reply_markup=None
        )
        
        # Задержка для эффекта вращения
        import time
        time.sleep(1.5)
        
        # Результат
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=f"🎰 {' '.join(result)}\n\n"
                 f"💎 Win: {win} coins\n"
                 f"💰 Balance: {user['balance']} coins",
            reply_markup=create_main_menu(user_id)
        )
    except Exception as e:
        logger.error(f"Spin error: {e}")

def calculate_win(result, bet):
    win = 0
    for symbol in set(result):
        count = result.count(symbol)
        if symbol in PAYOUTS and count >= 3:
            win += bet * PAYOUTS[symbol][min(count, 5)]
    return win

@bot.callback_query_handler(func=lambda call: call.data == 'change_bet')
def change_bet(call):
    try:
        user_id = call.from_user.id
        user = users_db.get(user_id)
        
        if not user:
            return
        
        markup = InlineKeyboardMarkup(row_width=3)
        markup.add(
            InlineKeyboardButton("-10", callback_data="bet_down"),
            InlineKeyboardButton(f"BET: {user['bet']}", callback_data="bet_current"),
            InlineKeyboardButton("+10", callback_data="bet_up"),
            InlineKeyboardButton("🔙 Back", callback_data="menu_back")
        )
        
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text="⚙️ Change your bet amount:",
            reply_markup=markup
        )
    except Exception as e:
        logger.error(f"Change bet error: {e}")

@bot.callback_query_handler(func=lambda call: call.data.startswith('bet_'))
def handle_bet_change(call):
    try:
        user_id = call.from_user.id
        user = users_db.get(user_id)
        
        if not user:
            return
        
        action = call.data.split('_')[1]
        
        if action == 'up':
            user['bet'] += 10
        elif action == 'down' and user['bet'] > 10:
            user['bet'] -= 10
        
        change_bet(call)
    except Exception as e:
        logger.error(f"Bet change error: {e}")

@bot.callback_query_handler(func=lambda call: call.data == 'menu_back')
def back_to_menu(call):
    try:
        user_id = call.from_user.id
        user = users_db.get(user_id)
        
        if user:
            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text=f"🐶 Dog House Slots\n\n💰 Balance: {user['balance']} coins",
                reply_markup=create_main_menu(user_id))
        else:
            start(call.message)
    except Exception as e:
        logger.error(f"Back to menu error: {e}")

def setup_webhook():
    try:
        bot.remove_webhook()
        bot.set_webhook(
            url=f"{VERCEL_URL}/webhook",
            secret_token=WEBHOOK_SECRET,
            drop_pending_updates=True
        )
        logger.info(f"Webhook configured for: {VERCEL_URL}")
    except Exception as e:
        logger.error(f"Webhook setup error: {e}")

# Инициализация вебхука при запуске
setup_webhook()

# Для запуска в Vercel
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))

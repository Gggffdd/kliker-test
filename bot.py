import os
import random
import logging
from flask import Flask, request, jsonify
import telebot
from telebot import types

# ======================
# КОНФИГУРАЦИЯ
# ======================
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN', 'ВАШ_ТОКЕН_БОТА')  # Замените на реальный токен
WEBHOOK_SECRET = os.getenv('WEBHOOK_SECRET', 'ваш_секретный_ключ')  # Любая случайная строка
VERCEL_URL = os.getenv('VERCEL_URL', 'https://kliker-test.vercel.app')  # Ваш домен

# Настройки игры
INITIAL_BALANCE = 1000
MIN_BET = 10
MAX_BET = 500

# Инициализация
app = Flask(__name__)
bot = telebot.TeleBot(TELEGRAM_TOKEN)

# Настройка логгирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ======================
# ИГРОВАЯ ЛОГИКА
# ======================
SLOT_SYMBOLS = ['🍒', '🍋', '🍇', '🍉', '🔔', '💎', '7️⃣', '🐶']
PAYOUTS = {
    '💎': {3: 10, 4: 50, 5: 200},
    '🐶': {3: 5, 4: 25, 5: 100},
    '7️⃣': {3: 3, 4: 15, 5: 75},
    '🔔': {3: 2, 4: 10, 5: 50}
}

# "База данных" в памяти (в продакшене используйте Redis/PostgreSQL)
users_db = {}

class User:
    def __init__(self, user_id):
        self.user_id = user_id
        self.balance = INITIAL_BALANCE
        self.bet = 100
        self.last_spin = None

    def to_dict(self):
        return {
            'balance': self.balance,
            'bet': self.bet,
            'last_spin': self.last_spin
        }

def get_user(user_id):
    if user_id not in users_db:
        users_db[user_id] = User(user_id)
    return users_db[user_id]

def calculate_win(result, bet):
    win = 0
    for symbol in set(result):
        count = result.count(symbol)
        if symbol in PAYOUTS and count >= 3:
            win += bet * PAYOUTS[symbol][min(count, 5)]
    return win

# ======================
# КЛАВИАТУРЫ
# ======================
def create_main_menu(user_id):
    user = get_user(user_id)
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton(f"🎰 Крутить ({user.bet})", callback_data="spin"),
        types.InlineKeyboardButton(f"💰 {user.balance} монет", callback_data="balance"),
        types.InlineKeyboardButton("⚙️ Изменить ставку", callback_data="change_bet")
    )
    return markup

def create_bet_menu(user_id):
    user = get_user(user_id)
    markup = types.InlineKeyboardMarkup(row_width=3)
    markup.add(
        types.InlineKeyboardButton("-10", callback_data="bet_down"),
        types.InlineKeyboardButton(f"{user.bet}", callback_data="bet_current"),
        types.InlineKeyboardButton("+10", callback_data="bet_up"),
        types.InlineKeyboardButton("🔙 Назад", callback_data="menu_back")
    )
    return markup

# ======================
# ОБРАБОТЧИКИ КОМАНД
# ======================
@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    try:
        user = get_user(message.from_user.id)
        bot.send_message(
            message.chat.id,
            f"🎰 Добро пожаловать в Dog House Slots!\n\n"
            f"💰 Баланс: {user.balance} монет\n"
            f"🪙 Текущая ставка: {user.bet} монет\n\n"
            "Используйте кнопки ниже для игры:",
            reply_markup=create_main_menu(message.from_user.id)
        )
    except Exception as e:
        logger.error(f"Error in send_welcome: {e}")

@bot.callback_query_handler(func=lambda call: call.data == 'spin')
def spin_handler(call):
    try:
        user = get_user(call.from_user.id)
        
        if user.balance < user.bet:
            bot.answer_callback_query(call.id, "❌ Недостаточно средств!")
            return
        
        # Генерация результата
        result = [random.choice(SLOT_SYMBOLS) for _ in range(5)]
        win = calculate_win(result, user.bet)
        user.balance += win - user.bet
        user.last_spin = {'result': result, 'win': win}
        
        # Формируем сообщение с результатом
        message = f"🎰 Результат: {' '.join(result)}\n\n"
        if win > 0:
            message += f"🎉 Поздравляем! Выигрыш: {win} монет!\n"
        else:
            message += "😢 Повезёт в следующий раз!\n"
        message += f"\n💰 Баланс: {user.balance} монет"
        
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=message,
            reply_markup=create_main_menu(call.from_user.id)
        )
        bot.answer_callback_query(call.id)
    except Exception as e:
        logger.error(f"Error in spin_handler: {e}")

@bot.callback_query_handler(func=lambda call: call.data == 'change_bet')
def change_bet_handler(call):
    try:
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=f"⚙️ Текущая ставка: {get_user(call.from_user.id).bet} монет\n"
                 f"Минимум: {MIN_BET}, Максимум: {MAX_BET}",
            reply_markup=create_bet_menu(call.from_user.id)
        )
    except Exception as e:
        logger.error(f"Error in change_bet_handler: {e}")

@bot.callback_query_handler(func=lambda call: call.data.startswith('bet_'))
def bet_adjust_handler(call):
    try:
        user = get_user(call.from_user.id)
        action = call.data.split('_')[1]
        
        if action == 'up':
            user.bet = min(user.bet + 10, MAX_BET)
        elif action == 'down':
            user.bet = max(user.bet - 10, MIN_BET)
        
        change_bet_handler(call)
    except Exception as e:
        logger.error(f"Error in bet_adjust_handler: {e}")

@bot.callback_query_handler(func=lambda call: call.data == 'menu_back')
def back_to_menu(call):
    try:
        user = get_user(call.from_user.id)
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=f"🎰 Dog House Slots\n\n"
                 f"💰 Баланс: {user.balance} монет\n"
                 f"🪙 Текущая ставка: {user.bet} монет",
            reply_markup=create_main_menu(call.from_user.id)
        )
    except Exception as e:
        logger.error(f"Error in back_to_menu: {e}")

# ======================
# WEBHOOK И ЗАПУСК
# ======================
@app.route('/')
def home():
    return "🎰 Dog House Slots Bot is Running! 🐶"

@app.route('/webhook', methods=['POST'])
def webhook():
    if request.headers.get('X-Telegram-Bot-Api-Secret-Token') != WEBHOOK_SECRET:
        return jsonify({"error": "Unauthorized"}), 403
    
    try:
        update = telebot.types.Update.de_json(request.get_json())
        bot.process_new_updates([update])
        return jsonify({"status": "ok"}), 200
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return jsonify({"error": "Internal server error"}), 500

def setup_webhook():
    try:
        bot.remove_webhook()
        bot.set_webhook(
            url=f"{VERCEL_URL}/webhook",
            secret_token=WEBHOOK_SECRET,
            drop_pending_updates=True
        )
        logger.info(f"Webhook configured for {VERCEL_URL}")
    except Exception as e:
        logger.error(f"Webhook setup error: {e}")

if __name__ == '__main__':
    # Локальный запуск
    logger.info("Starting bot in polling mode...")
    bot.remove_webhook()
    bot.polling(none_stop=True)
else:
    # Запуск на Vercel
    setup_webhook()

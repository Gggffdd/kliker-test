import os
import telebot
import random
from flask import Flask, request, jsonify
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

# Конфигурация
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')  # Получите @BotFather
VERCEL_URL = 'https://kliker-test.vercel.app'
WEBHOOK_SECRET = os.getenv('WEBHOOK_SECRET', 'your_very_strong_secret')

bot = telebot.TeleBot(TELEGRAM_TOKEN)
app = Flask(__name__)

# Мини-база данных (для продакшена используйте Redis/PostgreSQL)
users_db = {}

@app.route('/')
def home():
    return "🎰 Dog House Slots Bot is Running!"

@app.route('/webhook', methods=['POST'])
def webhook():
    if request.headers.get('X-Telegram-Bot-Api-Secret-Token') != WEBHOOK_SECRET:
        return jsonify({"status": "forbidden"}), 403
    
    json_data = request.get_json()
    update = telebot.types.Update.de_json(json_data)
    bot.process_new_updates([update])
    
    return jsonify({"status": "success"}), 200

@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id
    users_db[user_id] = {'balance': 1000, 'bet': 100}
    
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("🎰 Spin (100)", callback_data="spin"),
        InlineKeyboardButton("💰 Balance", callback_data="balance"),
        InlineKeyboardButton("⚙️ Change Bet", callback_data="change_bet")
    )
    
    bot.send_message(
        user_id,
        f"🐶 Welcome to Dog House Slots!\n\n"
        f"• Balance: {users_db[user_id]['balance']} coins\n"
        f"• Current bet: {users_db[user_id]['bet']} coins\n\n"
        "Select action:",
        reply_markup=markup
    )

@bot.callback_query_handler(func=lambda call: call.data == 'spin')
def spin(call):
    user_id = call.from_user.id
    user = users_db.get(user_id)
    
    if not user:
        return
    
    if user['balance'] < user['bet']:
        bot.answer_callback_query(call.id, "❌ Not enough balance!")
        return
    
    # Имитация вращения
    symbols = ['🍒', '🍋', '🍇', '🍉', '🔔', '💎', '7️⃣', '🐶']
    result = [random.choice(symbols) for _ in range(5)]
    
    # Расчет выигрыша (упрощенный)
    win = 0
    if result[0] == result[1] == result[2]:
        win = user['bet'] * 5
    
    user['balance'] += win - user['bet']
    
    # Отправка результата с анимацией
    with bot.retrieve_data(user_id) as data:
        data['last_result'] = result
    
    bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text=f"🎰 Spinning...",
    )
    
    bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text=f"🎰 Result: {' '.join(result)}\n\n"
             f"💸 Win: {win} coins\n"
             f"💰 Balance: {user['balance']} coins",
        reply_markup=get_main_menu()
    )

def get_main_menu():
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("🔄 Spin Again", callback_data="spin"),
        InlineKeyboardButton("🏠 Main Menu", callback_data="menu")
    )
    return markup

def setup_webhook():
    bot.remove_webhook()
    bot.set_webhook(
        url=f"{VERCEL_URL}/webhook",
        secret_token=WEBHOOK_SECRET,
        drop_pending_updates=True
    )
    print(f"Webhook configured for: {VERCEL_URL}")

if __name__ == '__main__':
    setup_webhook()
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))

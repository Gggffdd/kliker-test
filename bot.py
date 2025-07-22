import os
import telebot
import random
from flask import Flask, request, jsonify
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

# ======== КОНФИГУРАЦИЯ ======== (ЗАМЕНИТЕ ЭТИ ЗНАЧЕНИЯ!)
TELEGRAM_TOKEN = '6789012345:AAE1vzBE8x5T5w5fX0w1X5w5fX0w1X5w5fX0'
WEBHOOK_SECRET = 'd0gH0us3_S3cr3t_K3Y_2023_v2'  # Свой секретный ключ
VERCEL_URL = 'https://kliker-test.vercel.app'  # Ваш домен
# ==============================

bot = telebot.TeleBot(TELEGRAM_TOKEN)
app = Flask(__name__)

# Мини-база данных в памяти
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
    if request.headers.get('X-Telegram-Bot-Api-Secret-Token') != WEBHOOK_SECRET:
        return jsonify({"error": "Forbidden"}), 403
    
    update = telebot.types.Update.de_json(request.get_json())
    bot.process_new_updates([update])
    return "", 200

def create_main_menu(user_id):
    user = users_db.get(user_id, {'balance': 1000, 'bet': 100})
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton(f"🎰 Spin ({user['bet']})", callback_data="spin"),
        InlineKeyboardButton(f"💰 {user['balance']} coins", callback_data="balance"),
        InlineKeyboardButton("⚙️ Change Bet", callback_data="change_bet")
    )
    return markup

@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id
    if user_id not in users_db:
        users_db[user_id] = {'balance': 1000, 'bet': 100}
    
    bot.send_message(
        user_id,
        f"🐶 Welcome to Dog House Slots!\n\n"
        f"• Balance: {users_db[user_id]['balance']} coins\n"
        f"• Current bet: {users_db[user_id]['bet']} coins",
        reply_markup=create_main_menu(user_id)
    )

@bot.callback_query_handler(func=lambda call: call.data == 'spin')
def spin(call):
    user_id = call.from_user.id
    user = users_db.get(user_id)
    
    if not user:
        return
    
    if user['balance'] < user['bet']:
        bot.answer_callback_query(call.id, "❌ Not enough coins!")
        return
    
    # Генерация результата
    result = [random.choice(SLOT_SYMBOLS) for _ in range(5)]
    win = calculate_win(result, user['bet'])
    user['balance'] += win - user['bet']
    
    # Анимация вращения
    bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text="🎰 Spinning... 🌀"
    )
    
    # Результат
    bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text=f"🎰 {' '.join(result)}\n\n"
             f"💎 Win: {win} coins\n"
             f"💰 Balance: {user['balance']} coins",
        reply_markup=create_main_menu(user_id)
    )

def calculate_win(result, bet):
    win = 0
    for symbol in set(result):
        count = result.count(symbol)
        if symbol in PAYOUTS and count >= 3:
            win += bet * PAYOUTS[symbol][min(count, 5)]
    return win

@bot.callback_query_handler(func=lambda call: call.data == 'change_bet')
def change_bet(call):
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

@bot.callback_query_handler(func=lambda call: call.data.startswith('bet_'))
def handle_bet_change(call):
    user_id = call.from_user.id
    user = users_db.get(user_id)
    
    if not user:
        return
    
    action = call.data.split('_')[1]
    
    if action == 'up':
        user['bet'] += 10
    elif action == 'down' and user['bet'] > 10:
        user['bet'] -= 10
    
    change_bet(call)  # Обновляем меню

@bot.callback_query_handler(func=lambda call: call.data == 'menu_back')
def back_to_menu(call):
    user_id = call.from_user.id
    bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text=f"🐶 Dog House Slots\n\n💰 Balance: {users_db[user_id]['balance']} coins",
        reply_markup=create_main_menu(user_id)
    )

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

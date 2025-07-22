import os
import telebot
import random
from flask import Flask, request, jsonify
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

# Конфигурация
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN', '7523520150:AAGMPibPAl8D0I0E6ZeNR3zuIp0qKcshXN0')
SERVER_URL = os.getenv('SERVER_URL', 'https://yourdomain.com')

bot = telebot.TeleBot(TELEGRAM_TOKEN)
app = Flask(__name__)

# Игровые данные пользователей
user_data = {}

# Символы для слотов
SLOT_SYMBOLS = ['🍒', '🍋', '🍇', '🍉', '🔔', '💎', '7️⃣', '🐶']
PAYOUTS = {
    '💎': {3: 5, 4: 20, 5: 100},
    '🐶': {3: 3, 4: 10, 5: 50},
    '🔔': {3: 2, 4: 7, 5: 25},
    '🍇': {3: 1, 4: 3, 5: 10}
}

class User:
    def __init__(self, user_id):
        self.user_id = user_id
        self.balance = 0
        self.bet = 100

# Обработчик команды /start
@bot.message_handler(commands=['start'])
def handle_start(message):
    user_id = message.from_user.id
    if user_id not in user_data:
        user_data[user_id] = User(user_id)
    
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("🎰 Играть", callback_data="play_slot"))
    markup.add(InlineKeyboardButton("💰 Пополнить баланс", callback_data="deposit"))
    
    bot.send_message(
        user_id,
        f"🎰 Добро пожаловать в Dog House Slots!\n\n"
        f"💰 Ваш баланс: {user_data[user_id].balance} ₽\n"
        f"🪙 Текущая ставка: {user_data[user_id].bet} ₽\n\n"
        "Выберите действие:",
        reply_markup=markup
    )

# Обработчик callback-ов
@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    user_id = call.from_user.id
    if user_id not in user_data:
        user_data[user_id] = User(user_id)
    
    if call.data == "play_slot":
        play_slot(user_id)
    elif call.data == "deposit":
        show_deposit_options(user_id)
    elif call.data.startswith("bet_"):
        handle_bet_change(user_id, call.data)
    elif call.data == "back_to_menu":
        handle_start(call.message)

def play_slot(user_id):
    user = user_data[user_id]
    
    if user.balance < user.bet:
        bot.send_message(user_id, "❌ Недостаточно средств! Пополните баланс.")
        return
    
    # Спин
    user.balance -= user.bet
    result = [random.choice(SLOT_SYMBOLS) for _ in range(5)]
    
    # Расчет выигрыша
    win = 0
    for symbol in set(result):
        count = result.count(symbol)
        if symbol in PAYOUTS and count >= 3:
            win += user.bet * PAYOUTS[symbol][min(count, 5)]
    
    user.balance += win
    
    # Формируем сообщение
    message = "🎰 Результат:\n\n" + " ".join(result) + "\n\n"
    if win > 0:
        message += f"🎉 Вы выиграли {win} ₽!\n"
    else:
        message += "😢 Повезет в следующий раз!\n"
    
    message += f"\n💰 Баланс: {user.balance} ₽"
    
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("🔄 Крутить еще", callback_data="play_slot"))
    markup.add(InlineKeyboardButton("💰 Пополнить", callback_data="deposit"))
    markup.add(InlineKeyboardButton("📊 Изменить ставку", callback_data="change_bet"))
    
    bot.send_message(user_id, message, reply_markup=markup)

def show_deposit_options(user_id):
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("💳 Пополнить через CryptoBot", callback_data="cryptobot_payment"))
    markup.add(InlineKeyboardButton("🔙 Назад", callback_data="back_to_menu"))
    
    bot.send_message(
        user_id,
        "💰 Пополнение баланса\n\n"
        "Выберите способ оплаты:",
        reply_markup=markup
    )

def handle_bet_change(user_id, action):
    user = user_data[user_id]
    
    if action == "bet_up":
        user.bet += 50
    elif action == "bet_down" and user.bet > 50:
        user.bet -= 50
    
    markup = InlineKeyboardMarkup()
    markup.add(
        InlineKeyboardButton("⬇️", callback_data="bet_down"),
        InlineKeyboardButton(f"{user.bet} ₽", callback_data="current_bet"),
        InlineKeyboardButton("⬆️", callback_data="bet_up")
    )
    markup.add(InlineKeyboardButton("🔙 Назад", callback_data="back_to_menu"))
    
    bot.edit_message_text(
        f"📊 Изменение ставки\n\nТекущая ставка: {user.bet} ₽",
        user_id,
        message_id=call.message.message_id,
        reply_markup=markup
    )

# Webhook обработчик
@app.route('/telegram-webhook', methods=['POST'])
def telegram_webhook():
    if request.headers.get('X-Telegram-Bot-Api-Secret-Token') != os.getenv('WEBHOOK_SECRET'):
        return jsonify({"status": "error", "message": "Unauthorized"}), 401
    
    update = telebot.types.Update.de_json(request.get_json(force=True))
    bot.process_new_updates([update])
    return jsonify({"status": "success"}), 200

def run_flask():
    app.run(host='0.0.0.0', port=5000)

if __name__ == '__main__':
    # Удалить предыдущие webhook'и
    bot.remove_webhook()
    
    # Установить новый webhook
    webhook_url = f"{SERVER_URL}/telegram-webhook"
    bot.set_webhook(
        url=webhook_url,
        secret_token=os.getenv('WEBHOOK_SECRET', 'your_webhook_secret')
    )
    print(f"Webhook set to: {webhook_url}")
    
    # Запустить Flask
    from threading import Thread
    flask_thread = Thread(target=run_flask)
    flask_thread.start()

import os
import telebot
from flask import Flask, request

# Конфигурация (для Vercel используйте Environment Variables)
TOKEN = os.getenv('TELEGRAM_TOKEN', '7523520150:AAGMPibPAl8D0I0E6ZeNR3zuIp0qKcshXN0')  # Основной токен
SECRET = os.getenv('WEBHOOK_SECRET', 'СЛУЧАЙНЫЙ_СЕКРЕТ')  # Любая строка
DOMAIN = os.getenv('VERCEL_URL', 'https://kliker-test.vercel.app')

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

# Минимальная "база данных"
users = {}

@app.route('/')
def home():
    return "Bot is running!"

@app.route('/webhook', methods=['POST'])
def webhook():
    if request.headers.get('X-Telegram-Bot-Api-Secret-Token') != SECRET:
        return "Unauthorized", 403
    
    json_data = request.get_json()
    update = telebot.types.Update.de_json(json_data)
    bot.process_new_updates([update])
    return "OK", 200

@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id
    users[user_id] = {'balance': 1000, 'bet': 100}
    
    bot.send_message(
        user_id,
        f"🎰 Добро пожаловать!\n\n"
        f"💰 Баланс: {users[user_id]['balance']}\n"
        f"🪙 Ставка: {users[user_id]['bet']}\n\n"
        "Отправьте /spin для игры"
    )

@bot.message_handler(commands=['spin'])
def spin(message):
    user_id = message.from_user.id
    if user_id not in users:
        return start(message)
    
    user = users[user_id]
    if user['balance'] < user['bet']:
        return bot.send_message(user_id, "❌ Недостаточно средств!")
    
    # Простейшая логика слотов
    symbols = ['🍒', '🍋', '🍇', '🍉', '🔔', '💎']
    result = [random.choice(symbols) for _ in range(3)]
    win = 100 if len(set(result)) == 1 else 0
    
    user['balance'] += win - user['bet']
    
    bot.send_message(
        user_id,
        f"Результат: {' '.join(result)}\n\n"
        f"Выигрыш: {win}\n"
        f"Баланс: {user['balance']}"
    )

def set_webhook():
    bot.remove_webhook()
    bot.set_webhook(
        url=f"{DOMAIN}/webhook",
        secret_token=SECRET
    )

if __name__ == '__main__':
    # Локальный режим
    bot.remove_webhook()
    bot.polling()
else:
    # Режим Vercel
    set_webhook()

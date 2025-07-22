import os
from flask import Flask, request
import telebot

app = Flask(__name__)
bot = telebot.TeleBot(os.getenv('7523520150:AAGMPibPAl8D0I0E6ZeNR3zuIp0qKcshXN0'))

@app.route('/')
def home():
    return "🎰 Слот-бот работает! /start для начала"

@app.route('/webhook', methods=['POST'])
def webhook():
    if request.headers.get('X-Telegram-Bot-Api-Secret-Token') != os.getenv('WEBHOOK_SECRET'):
        return "Unauthorized", 403
    
    update = telebot.types.Update.de_json(request.get_json())
    bot.process_new_updates([update])
    return "OK", 200

@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(
        message.chat.id,
        "🐶 Добро пожаловать в Dog House Slots!\n\n"
        "Отправьте /spin чтобы крутить слоты"
    )

@bot.message_handler(commands=['spin'])
def spin(message):
    symbols = ['🍒', '🍋', '🍇', '💎']
    result = random.choices(symbols, k=3)
    win = 100 if len(set(result)) == 1 else 0
    
    bot.send_message(
        message.chat.id,
        f"Результат: {' '.join(result)}\n\n"
        f"Выигрыш: {win} монет"
    )

if __name__ == '__main__':
    bot.remove_webhook()
    bot.polling()
else:
    bot.remove_webhook()
    bot.set_webhook(
        url=os.getenv('VERCEL_URL') + '/webhook',
        secret_token=os.getenv('WEBHOOK_SECRET')
    )

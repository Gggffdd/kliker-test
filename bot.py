import os
import telebot
import requests
from flask import Flask, request, jsonify

# Конфигурация
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN', '7780179544:AAGGaZB4dOZFPKaBKYQtC9NfpHv3uwrFMyE')
CRYPTO_BOT_TOKEN = os.getenv('CRYPTO_BOT_TOKEN', '428290:AAW532c6iYZ0vr7zuBQtj4hi8UGBzofeKby')
SERVER_URL = os.getenv('SERVER_URL', 'https://yourdomain.com')

bot = telebot.TeleBot(TELEGRAM_TOKEN)
app = Flask(__name__)

# Обработчик команды /start
@bot.message_handler(commands=['start'])
def handle_start(message):
    try:
        if len(message.text.split()) > 1 and message.text.split()[1].startswith('pay_'):
            pay_url = message.text.split('pay_')[1]
            send_payment_instructions(message.chat.id, pay_url)
        else:
            bot.send_message(
                message.chat.id,
                "👋 Welcome to Dodgy Rabbit App!\n\n"
                "Use this bot to complete your payments. "
                "Start your purchase on our website and you'll be redirected here for payment."
            )
    except Exception as e:
        print(f"Error in handle_start: {e}")

def send_payment_instructions(chat_id, pay_url):
    try:
        markup = telebot.types.InlineKeyboardMarkup()
        markup.add(telebot.types.InlineKeyboardButton(
            text="💳 Pay Now",
            url=pay_url
        ))
        
        bot.send_message(
            chat_id,
            "🛒 Please complete your payment:\n\n"
            "1. Click the 'Pay Now' button below\n"
            "2. Follow the instructions in CryptoBot\n"
            "3. After payment, you'll receive a confirmation\n\n"
            "If you have any issues, please contact support.",
            reply_markup=markup
        )
    except Exception as e:
        print(f"Error sending payment instructions: {e}")

# Webhook обработчик для проверки платежей
@app.route('/telegram-webhook', methods=['POST'])
def telegram_webhook():
    if request.headers.get('X-Telegram-Bot-Api-Secret-Token') != os.getenv('WEBHOOK_SECRET'):
        return jsonify({"status": "error", "message": "Unauthorized"}), 401
    
    update = telebot.types.Update.de_json(request.get_json(force=True))
    bot.process_new_updates([update])
    return jsonify({"status": "success"}), 200

# Запуск Flask сервера для webhook
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
    
    # Запустить Flask в отдельном потоке
    from threading import Thread
    flask_thread = Thread(target=run_flask)
    flask_thread.start()
    
    # Также можно запустить polling для разработки
    # bot.polling(none_stop=True)

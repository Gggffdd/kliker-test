import os
import logging
import telebot
import requests
import json
from datetime import datetime, timedelta
import threading
from dotenv import load_dotenv

# Загрузка переменных окружения
load_dotenv()

# Настройка логгера
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('bot.log')
    ]
)
logger = logging.getLogger(__name__)

# Конфигурация
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
CRYPTOPAY_TOKEN = os.getenv('CRYPTOPAY_TOKEN')
SERVER_URL = os.getenv('SERVER_URL')
BOT_USERNAME = os.getenv('BOT_USERNAME')  # Без @

bot = telebot.TeleBot(TELEGRAM_TOKEN)

# Временное хранилище платежей
payments = {}

@bot.message_handler(commands=['start'])
def handle_start(message):
    try:
        # Проверяем наличие paymentId в команде
        if len(message.text.split()) > 1:
            payment_id = message.text.split()[1]
            logger.info(f"🚀 Payment session started: {payment_id}")
            
            # Сохраняем информацию о чате
            payments[payment_id] = {
                'chat_id': message.chat.id,
                'status': 'processing',
                'created_at': datetime.now()
            }
            
            # Создаем инвойс в CryptoPay
            response = create_crypto_invoice(
                amount=10.00,
                asset='USDT',
                description=f"Premium Subscription - {payment_id}",
                payload=json.dumps({
                    'payment_id': payment_id,
                    'user_id': message.from_user.id
                })
            )
            
            if response and 'result' in response:
                invoice = response['result']
                payments[payment_id]['invoice_id'] = invoice['id']
                
                # Отправляем кнопку оплаты
                markup = telebot.types.InlineKeyboardMarkup()
                btn = telebot.types.InlineKeyboardButton(
                    text="💳 Оплатить сейчас", 
                    url=invoice['pay_url']
                )
                markup.add(btn)
                
                bot.send_message(
                    message.chat.id,
                    "🔐 Оплатите премиум подписку:\n\n"
                    f"Сумма: 10.00 USDT\n"
                    "Ссылка действительна 15 минут\n\n"
                    "После оплаты доступ будет активирован автоматически",
                    reply_markup=markup
                )
                
                # Инструкция
                bot.send_message(
                    message.chat.id,
                    "ℹ️ Если возникли проблемы:\n"
                    "1. Убедитесь, что у вас достаточно средств\n"
                    "2. Используйте кошелек, поддерживающий TRC-20\n"
                    "3. Для помощи: @your_support"
                )
            else:
                bot.send_message(
                    message.chat.id,
                    "❌ Ошибка при создании платежа. Попробуйте позже."
                )
        else:
            bot.send_message(
                message.chat.id,
                "👋 Привет! Для оплаты перейдите по ссылке с сайта."
            )
            
    except Exception as e:
        logger.error(f"🔥 Error in start handler: {str(e)}")
        bot.send_message(
            message.chat.id,
            "⚠️ Произошла ошибка. Пожалуйста, попробуйте позже."
        )

def create_crypto_invoice(amount, asset, description, payload):
    url = "https://pay.crypt.bot/api/createInvoice"
    headers = {
        "Crypto-Pay-API-Token": CRYPTOPAY_TOKEN,
        "Content-Type": "application/json"
    }
    data = {
        "asset": asset,
        "amount": str(amount),
        "description": description,
        "payload": payload,
        "paid_btn_name": "open_bot",
        "paid_btn_url": f"https://t.me/{BOT_USERNAME}",
        "allow_anonymous": False,
        "expires_in": 900  # 15 минут
    }
    
    try:
        response = requests.post(url, headers=headers, json=data, timeout=10)
        response.raise_for_status()
        result = response.json()
        logger.info(f"CryptoPay response: {result}")
        
        if result.get('ok'):
            return result
        else:
            logger.error(f"❌ CryptoPay error: {result.get('error')}")
            return None
            
    except Exception as e:
        logger.error(f"🔥 Error creating invoice: {str(e)}")
        return None

def check_expired_payments():
    """Проверка просроченных платежей"""
    now = datetime.now()
    
    for payment_id, payment in list(payments.items()):
        if payment['status'] == 'processing':
            created = payment['created_at']
            if now > created + timedelta(minutes=16):  # +1 минута к сроку
                try:
                    chat_id = payment['chat_id']
                    bot.send_message(
                        chat_id,
                        "⌛ Время оплаты истекло. Пожалуйста, создайте новый заказ."
                    )
                    payments[payment_id]['status'] = 'expired'
                    logger.info(f"⏳ Payment expired: {payment_id}")
                except Exception as e:
                    logger.error(f"🔥 Error handling expired payment: {str(e)}")

# Запуск проверки просроченных платежей
def run_payment_checker():
    while True:
        check_expired_payments()
        threading.Event().wait(300)  # Проверка каждые 5 минут

if __name__ == '__main__':
    logger.info("🚀 Starting Crypto Payment Bot...")
    logger.info(f"🌐 Using SERVER_URL: {SERVER_URL}")
    
    # Запуск проверки платежей в фоне
    threading.Thread(target=run_payment_checker, daemon=True).start()
    
    # Запуск бота
    bot.infinity_polling()

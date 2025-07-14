const express = require('express');
const app = express();
const TelegramBot = require('node-telegram-bot-api');
const fetch = require('node-fetch');

// Конфигурация
const TELEGRAM_TOKEN = '7780179544:AAGGaZB4dOZFPKaBKYQtC9NfpHv3uwrFMyE';
const CRYPTOPAY_TOKEN = '428290:AAW532c6iYZ0vr7zuBQtj4hi8UGBzofeKby';
const bot = new TelegramBot(TELEGRAM_TOKEN, { polling: true });

// Middleware
app.use(express.json());

// Хранилище платежей (временное, для примера)
const payments = {};

// Команда /pay
bot.onText(/\/pay/, (msg) => {
  const chatId = msg.chat.id;
  const userId = msg.from.id;
  
  // Создаем инвойс
  createCryptoInvoice(userId, 10.00, 'USD', 'Premium подписка')
    .then(invoice => {
      payments[invoice.invoice_id] = { chatId, status: 'pending' };
      
      // Отправляем кнопку оплаты
      bot.sendMessage(chatId, 'Оплатите подписку:', {
        reply_markup: {
          inline_keyboard: [[
            { text: "💳 Оплатить", url: invoice.pay_url }
          ]]
        }
      });
    })
    .catch(error => {
      console.error('Ошибка создания инвойса:', error);
      bot.sendMessage(chatId, '❌ Ошибка при создании платежа');
    });
});

// Создание инвойса в CryptoPay
async function createCryptoInvoice(userId, amount, asset, description) {
  const response = await fetch('https://pay.crypt.bot/api/createInvoice', {
    method: 'POST',
    headers: {
      'Crypto-Pay-API-Token': CRYPTOPAY_TOKEN,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      asset: asset,
      amount: amount,
      description: description,
      paid_btn_name: 'return',
      payload: JSON.stringify({ userId }), // Важные метаданные
      allow_anonymous: false
    })
  });

  const data = await response.json();
  if (!data.ok) throw new Error(data.error);
  return data.result;
}

// Webhook для CryptoPay
app.post('/cryptobot-webhook', (req, res) => {
  const { invoice } = req.body;
  
  // Проверяем статус оплаты
  if (invoice.status === 'paid') {
    const meta = JSON.parse(invoice.payload);
    const payment = payments[invoice.invoice_id];
    
    if (payment) {
      // Обновляем статус
      payments[invoice.invoice_id].status = 'paid';
      
      // Уведомляем пользователя
      bot.sendMessage(payment.chatId, `✅ Оплата прошла успешно!`);
      
      // Здесь логика выдачи доступа/товара
    }
  }
  
  res.sendStatus(200);
});

// Запуск сервера
app.listen(3000, () => console.log('Server started on port 3000'));

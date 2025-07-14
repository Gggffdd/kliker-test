require('dotenv').config();
const express = require('express');
const app = express();
const bodyParser = require('body-parser');
const fetch = require('node-fetch');
const crypto = require('crypto');

// Конфигурация
const PORT = process.env.PORT || 3000;
const TELEGRAM_TOKEN = process.env.TELEGRAM_TOKEN;
const CRYPTOPAY_TOKEN = process.env.CRYPTOPAY_TOKEN;
const WEBHOOK_SECRET = process.env.WEBHOOK_SECRET;
const SERVER_URL = process.env.RENDER_EXTERNAL_URL || `http://localhost:${PORT}`;

app.use(bodyParser.json());
app.use(express.static('public')); // Обслуживаем статические файлы

// Хранилище платежей
const payments = {};

// Создание платежной сессии
app.post('/create-payment', (req, res) => {
    const paymentId = `pay-${Date.now()}-${Math.random().toString(36).substr(2, 5)}`;
    payments[paymentId] = {
        status: 'pending',
        createdAt: new Date(),
        product: 'Premium Subscription',
        amount: 10.00,
        currency: 'USD'
    };
    
    // Ссылка на бота с paymentId
    const botLink = `https://t.me/${process.env.BOT_USERNAME}?start=${paymentId}`;
    res.json({ 
        success: true, 
        botLink,
        paymentId
    });
});

// Верификация подписи вебхука
function verifySignature(body, signature) {
    const hmac = crypto.createHmac('sha256', WEBHOOK_SECRET);
    hmac.update(JSON.stringify(body));
    return hmac.digest('hex') === signature;
}

// Обработчик вебхуков от CryptoPay
app.post('/cryptobot-webhook', (req, res) => {
    const signature = req.headers['crypto-pay-api-signature'];
    
    if (!verifySignature(req.body, signature)) {
        console.error('⚠️ Invalid webhook signature');
        return res.status(401).send('Invalid signature');
    }
    
    const event = req.body;
    console.log('🔔 Received CryptoPay event:', event.event_type);
    
    if (event.event_type === 'invoice_paid') {
        const invoice = event.payload.invoice;
        
        // Поиск платежа по invoice_id
        const paymentEntry = Object.entries(payments).find(
            ([, data]) => data.invoiceId === invoice.id
        );
        
        if (paymentEntry) {
            const [paymentId, paymentData] = paymentEntry;
            paymentData.status = 'paid';
            paymentData.paidAt = new Date();
            
            console.log(`✅ Payment completed: ${paymentId}`);
            console.log(`💳 User: ${paymentData.chatId}, Amount: ${invoice.amount} ${invoice.asset}`);
            
            // Уведомление пользователя
            sendTelegramMessage(
                paymentData.chatId, 
                `🎉 Оплата прошла успешно!\n` +
                `Ваш премиум доступ активирован.\n` +
                `Сумма: ${invoice.amount} ${invoice.asset}\n` +
                `ID транзакции: ${invoice.hash}`
            );
        }
    }
    
    res.sendStatus(200);
});

// Отправка сообщения через Telegram API
async function sendTelegramMessage(chatId, text) {
    const url = `https://api.telegram.org/bot${TELEGRAM_TOKEN}/sendMessage`;
    try {
        await fetch(url, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ chat_id: chatId, text })
        });
    } catch (error) {
        console.error('❌ Error sending Telegram message:', error);
    }
}

// Старт сервера
app.listen(PORT, () => {
    console.log(`🚀 Server running on port ${PORT}`);
    console.log(`🌐 CryptoPay Webhook URL: ${SERVER_URL}/cryptobot-webhook`);
});

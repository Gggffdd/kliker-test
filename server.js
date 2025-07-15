require('dotenv').config();
const express = require('express');
const axios = require('axios');
const crypto = require('crypto');
const app = express();
const PORT = process.env.PORT || 3000;

// =============================================
// КОНФИГУРАЦИЯ
// =============================================
const CRYPTO_BOT_TOKEN = process.env.CRYPTO_BOT_TOKEN || '428290:AAW532c6iYZ0vr7zuBQtj4hi8UGBzofeKby';
const CRYPTO_BOT_API = 'https://pay.crypt.bot/api';
const TELEGRAM_BOT_URL = 'https://t.me/DodgyRabbitBot';
const WEBHOOK_SECRET = process.env.WEBHOOK_SECRET || 'your_webhook_secret';

// Временное хранилище заказов (в реальном проекте используйте БД)
const orders = new Map();

// =============================================
// НАСТРОЙКА СЕРВЕРА
// =============================================
app.use(express.json());
app.use(express.static('public'));

// Разрешаем CORS для тестирования
app.use((req, res, next) => {
  res.header('Access-Control-Allow-Origin', '*');
  res.header('Access-Control-Allow-Headers', 'Origin, X-Requested-With, Content-Type, Accept');
  next();
});

// =============================================
// MIDDLEWARE ДЛЯ ПРОВЕРКИ ПОДПИСИ CRYPTOBOT
// =============================================
const verifyWebhook = (req, res, next) => {
  const signature = req.headers['crypto-pay-api-signature'];
  if (!signature) {
    console.error('Missing signature header');
    return res.status(401).send('Unauthorized');
  }
  
  const hmac = crypto.createHmac('sha256', WEBHOOK_SECRET);
  const digest = hmac.update(JSON.stringify(req.body)).digest('hex');
  
  if (signature !== digest) {
    console.error('Invalid signature received');
    return res.status(401).send('Invalid signature');
  }
  
  next();
};

// =============================================
// РОУТЫ API
// =============================================

/**
 * Создание платежного инвойса
 * POST /api/create-invoice
 * Body: { userId, productId, amount, currency? }
 */
app.post('/api/create-invoice', async (req, res) => {
  try {
    const { userId, productId, amount, currency = 'USDT' } = req.body;
    
    // Валидация параметров
    if (!userId || !productId || !amount) {
      return res.status(400).json({ 
        error: 'Missing required fields',
        required: ['userId', 'productId', 'amount']
      });
    }

    // Создаем инвойс в CryptoBot
    const response = await axios.post(`${CRYPTO_BOT_API}/createInvoice`, {
      asset: currency,
      amount: amount.toString(),
      description: `Payment for product ${productId}`,
      paid_btn_name: 'viewItem',
      paid_btn_url: `${req.protocol}://${req.get('host')}/success`,
      payload: JSON.stringify({ userId, productId }),
      allow_comments: false,
      allow_anonymous: false,
    }, {
      headers: { 
        'Crypto-Pay-API-Token': CRYPTO_BOT_TOKEN,
        'Content-Type': 'application/json'
      }
    });

    const { invoice_id, pay_url } = response.data.result;
    
    // Сохраняем заказ
    orders.set(invoice_id, { 
      userId, 
      productId, 
      amount, 
      currency,
      status: 'pending',
      createdAt: new Date()
    });

    // Возвращаем ссылку для оплаты
    res.json({ 
      success: true,
      invoice_id,
      pay_url: `${TELEGRAM_BOT_URL}?start=pay_${encodeURIComponent(pay_url)}`,
      status: 'created',
      timestamp: new Date()
    });

  } catch (error) {
    console.error('Invoice creation error:', error.response?.data || error.message);
    res.status(500).json({ 
      success: false,
      error: 'Failed to create invoice',
      details: error.response?.data || error.message
    });
  }
});

/**
 * Webhook для обработки платежей от CryptoBot
 * POST /api/crypto-webhook
 */
app.post('/api/crypto-webhook', verifyWebhook, (req, res) => {
  try {
    const { invoice_id, status } = req.body;
    
    if (!orders.has(invoice_id)) {
      console.warn(`Order not found: ${invoice_id}`);
      return res.status(404).json({ error: 'Order not found' });
    }

    // Обновляем статус заказа
    const order = orders.get(invoice_id);
    order.status = status;
    order.updatedAt = new Date();
    orders.set(invoice_id, order);

    console.log(`Order status updated: ${invoice_id} -> ${status}`);

    if (status === 'paid') {
      // Здесь можно:
      // 1. Отправить уведомление пользователю
      // 2. Сохранить в БД
      // 3. Выдать товар/доступ
      console.log(`✅ Order paid: ${JSON.stringify(order)}`);
    }

    res.json({ success: true });

  } catch (error) {
    console.error('Webhook processing error:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
});

/**
 * Проверка статуса платежа
 * GET /api/check-payment/:invoice_id
 */
app.get('/api/check-payment/:invoice_id', async (req, res) => {
  try {
    const { invoice_id } = req.params;

    // Проверяем в CryptoBot
    const response = await axios.get(`${CRYPTO_BOT_API}/getInvoices?invoice_ids=${invoice_id}`, {
      headers: { 'Crypto-Pay-API-Token': CRYPTO_BOT_TOKEN }
    });

    const invoice = response.data.result.items[0];
    if (!invoice) {
      return res.status(404).json({ 
        error: 'Invoice not found',
        invoice_id
      });
    }

    res.json({
      success: true,
      invoice_id: invoice.invoice_id,
      status: invoice.status,
      paid: invoice.status === 'paid',
      amount: invoice.amount,
      currency: invoice.asset
    });

  } catch (error) {
    console.error('Payment check error:', error);
    res.status(500).json({ 
      error: 'Failed to check payment status',
      details: error.response?.data || error.message
    });
  }
});

// =============================================
// ЗАПУСК СЕРВЕРА
// =============================================
app.listen(PORT, () => {
  console.log(`🚀 Server running on port ${PORT}`);
  console.log(`🔗 CryptoBot Webhook URL: http://localhost:${PORT}/api/crypto-webhook`);
  console.log(`🔗 Create invoice endpoint: http://localhost:${PORT}/api/create-invoice`);
});

// Простой роут для проверки работы
app.get('/', (req, res) => {
  res.send('Dodgy Rabbit App API is running!');
});

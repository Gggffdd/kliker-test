require('dotenv').config();
const express = require('express');
const axios = require('axios');
const crypto = require('crypto');
const app = express();
const PORT = process.env.PORT || 3000;

// Конфигурация
const CRYPTO_BOT_TOKEN = process.env.CRYPTO_BOT_TOKEN || '428290:AAW532c6iYZ0vr7zuBQtj4hi8UGBzofeKby';
const CRYPTO_BOT_API = 'https://pay.crypt.bot/api';
const TELEGRAM_BOT_URL = 'https://t.me/DodgyRabbitBot';
const WEBHOOK_SECRET = process.env.WEBHOOK_SECRET || 'your_webhook_secret';

// Временное хранилище заказов (в продакшене используйте БД)
const orders = new Map();

app.use(express.json());
app.use(express.static('public'));

// Middleware для проверки подписи CryptoBot
const verifyWebhook = (req, res, next) => {
  const signature = req.headers['crypto-pay-api-signature'];
  if (!signature) return res.status(401).send('Unauthorized');
  
  const hmac = crypto.createHmac('sha256', WEBHOOK_SECRET);
  const digest = hmac.update(JSON.stringify(req.body)).digest('hex');
  
  if (signature !== digest) return res.status(401).send('Invalid signature');
  next();
};

// Создание инвойса
app.post('/api/create-invoice', async (req, res) => {
  try {
    const { userId, productId, amount, currency = 'USDT' } = req.body;
    
    if (!userId || !productId || !amount) {
      return res.status(400).json({ error: 'Missing required fields' });
    }

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
      headers: { 'Crypto-Pay-API-Token': CRYPTO_BOT_TOKEN }
    });

    const { invoice_id, pay_url } = response.data.result;
    orders.set(invoice_id, { userId, productId, amount, status: 'pending' });

    res.json({ 
      invoice_id,
      pay_url: `${TELEGRAM_BOT_URL}?start=pay_${encodeURIComponent(pay_url)}`,
      status: 'created'
    });
  } catch (error) {
    console.error('Invoice creation error:', error.response?.data || error.message);
    res.status(500).json({ error: 'Failed to create invoice' });
  }
});

// Webhook для обработки платежей
app.post('/api/crypto-webhook', verifyWebhook, (req, res) => {
  const { invoice_id, status } = req.body;
  
  if (!orders.has(invoice_id)) {
    return res.status(404).send('Order not found');
  }

  const order = orders.get(invoice_id);
  order.status = status;
  orders.set(invoice_id, order);

  if (status === 'paid') {
    // Здесь можно отправить уведомление пользователю
    console.log(`Order ${invoice_id} paid successfully`, order);
    // В реальном приложении сохраните в БД и предоставьте доступ к товару
  }

  res.sendStatus(200);
});

// Проверка статуса платежа
app.get('/api/check-payment/:invoice_id', async (req, res) => {
  try {
    const { invoice_id } = req.params;
    const response = await axios.get(`${CRYPTO_BOT_API}/getInvoices?invoice_ids=${invoice_id}`, {
      headers: { 'Crypto-Pay-API-Token': CRYPTO_BOT_TOKEN }
    });

    const invoice = response.data.result.items[0];
    if (!invoice) return res.status(404).json({ error: 'Invoice not found' });

    res.json({
      invoice_id: invoice.invoice_id,
      status: invoice.status,
      paid: invoice.status === 'paid'
    });
  } catch (error) {
    console.error('Payment check error:', error);
    res.status(500).json({ error: 'Failed to check payment status' });
  }
});

app.listen(PORT, () => {
  console.log(`Server running on port ${PORT}`);
  console.log(`CryptoBot Webhook URL: http://yourdomain.com/api/crypto-webhook`);
});

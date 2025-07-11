const express = require('express');
const axios = require('axios');
const bodyParser = require('body-parser');

const app = express();
app.use(bodyParser.json());

const CRYPTO_BOT_TOKEN = '428290:AAW532c6iYZ0vr7zuBQtj4hi8UGBzofeKby'; // Замените на ваш API-ключ
const CRYPTO_BOT_API = 'https://pay.crypt.bot/api';

// Создание инвойса
app.post('/createInvoice', async (req, res) => {
    const { amount, currency, coinsAmount } = req.body;

    try {
        const response = await axios.post(`${CRYPTO_BOT_API}/createInvoice`, {
            asset: currency,
            amount: amount.toString(),
            description: `Пополнение на ${coinsAmount} монет`,
        }, {
            headers: { 'Crypto-Pay-API-Token': CRYPTO_BOT_TOKEN }
        });

        res.json({
            success: true,
            invoiceId: response.data.result.invoice_id,
            payUrl: response.data.result.pay_url,
            address: response.data.result.address,
        });
    } catch (error) {
        res.status(500).json({ success: false, error: error.message });
    }
});

// Проверка статуса платежа
app.get('/checkInvoice/:invoiceId', async (req, res) => {
    const { invoiceId } = req.params;

    try {
        const response = await axios.get(`${CRYPTO_BOT_API}/getInvoices?invoice_ids=${invoiceId}`, {
            headers: { 'Crypto-Pay-API-Token': CRYPTO_BOT_TOKEN }
        });

        const invoice = response.data.result.items[0];
        res.json({
            status: invoice.status, // "active", "paid" или "expired"
            amount: invoice.amount,
            currency: invoice.asset,
        });
    } catch (error) {
        res.status(500).json({ success: false, error: error.message });
    }
});

app.listen(3000, () => console.log('Сервер запущен на порту 3000'));

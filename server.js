const express = require('express');
const axios = require('axios');
const bodyParser = require('body-parser');
const app = express();

app.use(bodyParser.json());

// Конфигурация бота
const BOT_TOKEN = '8098501828:AAFNGBZIQ6KoIgihZRlB8HwGoDwmThZ9egI';
const TELEGRAM_API = 'https://api.telegram.org/bot' + BOT_TOKEN;

// Получение баланса звезд
app.post('/get-stars-balance', async (req, res) => {
    try {
        const userId = req.body.user_id;
        
        const response = await axios.post(`${TELEGRAM_API}/getStarTransactions`, {
            user_id: userId,
            offset: 0,
            limit: 1
        });
        
        // Последняя транзакция содержит текущий баланс
        const lastTransaction = response.data.result.transactions[0];
        const balance = lastTransaction ? lastTransaction.star_count : 0;
        
        res.json({
            ok: true,
            balance: balance
        });
    } catch (error) {
        console.error('Balance error:', error.response?.data || error.message);
        res.status(500).json({
            ok: false,
            description: 'Error fetching star balance'
        });
    }
});

// Обработка покупки
app.post('/process-purchase', async (req, res) => {
    try {
        const { user_id, item_id, price } = req.body;
        
        // Создаем транзакцию списания
        const response = await axios.post(`${TELEGRAM_API}/refundStarTransaction`, {
            user_id: user_id,
            telegram_charge_id: `purchase_${Date.now()}`,
            amount: price
        });
        
        if (response.data.ok) {
            // Получаем новый баланс
            const balanceResponse = await axios.post(`${TELEGRAM_API}/getStarTransactions`, {
                user_id: user_id,
                offset: 0,
                limit: 1
            });
            
            const lastTransaction = balanceResponse.data.result.transactions[0];
            const newBalance = lastTransaction ? lastTransaction.star_count : 0;
            
            res.json({
                ok: true,
                new_balance: newBalance
            });
        } else {
            res.status(400).json({
                ok: false,
                description: response.data.description || 'Purchase failed'
            });
        }
    } catch (error) {
        console.error('Purchase error:', error.response?.data || error.message);
        res.status(500).json({
            ok: false,
            description: 'Error processing purchase'
        });
    }
});

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
    console.log(`Server running on port ${PORT}`);
});

const express = require('express');
const axios = require('axios');
const bodyParser = require('body-parser');

const app = express();
app.use(bodyParser.json());

const CRYPTOBOT_TOKEN = '428290:AAW532c6iYZ0vr7zuBQtj4hi8UGBzofeKby';
const MERCHANT_TOKEN = 'ВАШ_MERCHANT_TOKEN'; // Из настроек CryptoBot
const BOT_TOKEN = '7780179544:AAGGaZB4dOZFPKaBKYQtC9NfpHv3uwrFMyE'; // От @BotFather

// Создание инвойса
app.post('/createInvoice', async (req, res) => {
  try {
    const response = await axios.post(
      `https://pay.crypt.bot/api/createInvoice`,
      {
        asset: req.body.currency,
        amount: req.body.amount,
        description: `Покупка ${req.body.coinsAmount} монет`,
        hidden_message: `USER_ID:${req.body.userId}`,
        payload: JSON.stringify({
          coins: req.body.coinsAmount,
          effect: req.body.effect
        })
      },
      {
        headers: {
          'Crypto-Pay-API-Token': CRYPTOBOT_TOKEN
        }
      }
    );

    res.json(response.data.result);
  } catch (error) {
    console.error(error);
    res.status(500).send('Ошибка создания инвойса');
  }
});

// Обработка вебхука
app.post('/crypto-webhook', async (req, res) => {
  const event = req.body;
  
  if (event.invoice && event.invoice.status === 'paid') {
    const payload = JSON.parse(event.invoice.payload);
    const userId = event.invoice.hidden_message.split(':')[1];
    
    // Зачислить средства пользователю
    // Здесь ваша логика зачисления монет
    
    // Уведомить пользователя
    await axios.post(`https://api.telegram.org/bot${BOT_TOKEN}/sendMessage`, {
      chat_id: userId,
      text: `Оплата получена! Зачислено ${payload.coins} монет!`
    });
  }
  
  res.sendStatus(200);
});

app.listen(3000, () => console.log('Сервер запущен на порту 3000'));

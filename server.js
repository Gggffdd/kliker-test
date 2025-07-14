require('dotenv').config();
const express = require('express');
const cors = require('cors');
const axios = require('axios');
const crypto = require('crypto');
const bodyParser = require('body-parser');

const app = express();
app.use(cors());
app.use(bodyParser.json());

const PORT = process.env.PORT || 3000;
const BOT_API_URL = process.env.BOT_API_URL || 'http://localhost:5000';
const API_SECRET = process.env.API_SECRET;

// Mock database
const ordersDB = new Map();

// Middleware for API authentication
const authenticate = (req, res, next) => {
  const authHeader = req.headers['authorization'];
  if (authHeader && authHeader === `Bearer ${API_SECRET}`) {
    next();
  } else {
    res.status(401).json({ error: 'Unauthorized' });
  }
};

// Generate unique order ID
function generateOrderId() {
  return `order_${crypto.randomBytes(8).toString('hex')}`;
}

// Create order endpoint
app.post('/api/orders', async (req, res) => {
  try {
    const { productId, amount, currency = 'USD' } = req.body;
    
    if (!productId || !amount) {
      return res.status(400).json({ error: 'Missing required fields' });
    }

    const orderId = generateOrderId();
    const orderData = {
      id: orderId,
      productId,
      amount,
      currency,
      status: 'pending',
      createdAt: new Date().toISOString()
    };

    // Save to "database"
    ordersDB.set(orderId, orderData);

    // Request payment link from bot
    const botResponse = await axios.post(`${BOT_API_URL}/api/payments`, {
      orderId,
      amount,
      currency
    }, {
      headers: { Authorization: `Bearer ${API_SECRET}` }
    });

    if (!botResponse.data.success) {
      throw new Error('Failed to create payment');
    }

    // Update order with payment info
    orderData.paymentLink = botResponse.data.paymentLink;
    orderData.invoiceId = botResponse.data.invoiceId;
    ordersDB.set(orderId, orderData);

    res.json({
      success: true,
      orderId,
      paymentLink: botResponse.data.paymentLink
    });
  } catch (error) {
    console.error('Order creation error:', error);
    res.status(500).json({ 
      success: false,
      error: 'Failed to create order' 
    });
  }
});

// Payment confirmation endpoint
app.post('/api/payments/confirm', authenticate, (req, res) => {
  const { orderId, invoiceId } = req.body;
  
  if (!ordersDB.has(orderId)) {
    return res.status(404).json({ success: false, error: 'Order not found' });
  }

  const order = ordersDB.get(orderId);
  order.status = 'paid';
  order.paidAt = new Date().toISOString();
  order.invoiceId = invoiceId;

  // Here you would typically:
  // 1. Fulfill the order (send product, etc.)
  // 2. Notify the user
  // 3. Update other systems

  res.json({ success: true, order });
});

// Get order status
app.get('/api/orders/:orderId', (req, res) => {
  const orderId = req.params.orderId;
  
  if (!ordersDB.has(orderId)) {
    return res.status(404).json({ error: 'Order not found' });
  }

  res.json(ordersDB.get(orderId));
});

app.listen(PORT, () => {
  console.log(`Server running on port ${PORT}`);
});

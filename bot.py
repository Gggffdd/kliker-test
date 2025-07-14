import os
from flask import Flask, request, jsonify
from cryptopay import CryptoPay
from telegram import Bot, Update
from telegram.ext import Dispatcher, MessageHandler, Filters, CallbackContext
import threading
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

class PaymentBot:
    def __init__(self):
        self.token = os.getenv('TELEGRAM_BOT_TOKEN')
        self.crypto_token = os.getenv('CRYPTOPAY_TOKEN')
        self.api_secret = os.getenv('API_SECRET')
        
        self.bot = Bot(token=self.token)
        self.dispatcher = Dispatcher(self.bot, None, use_context=True)
        
        self.cryptopay = CryptoPay(
            token=self.crypto_token,
            api_url="https://pay.crypt.bot/api"
        )
        
        self.setup_handlers()
    
    def setup_handlers(self):
        self.dispatcher.add_handler(
            MessageHandler(Filters.text & ~Filters.command, self.handle_message)
        )
    
    def handle_message(self, update: Update, context: CallbackContext):
        chat_id = update.effective_chat.id
        text = update.message.text
        
        if text.lower() == '/start':
            self.bot.send_message(
                chat_id=chat_id,
                text="Welcome to the payment bot! Send /pay to create a payment."
            )
    
    def create_payment_link(self, order_id, amount, currency='USD'):
        try:
            asset = currency.upper()
            amount_str = str(amount)
            
            invoice = self.cryptopay.create_invoice(
                asset=asset,
                amount=amount_str,
                description=f"Payment for order #{order_id}",
                hidden_message="Thank you for your purchase!",
                payload=order_id,
                expires_in=3600  # 1 hour expiration
            )
            
            return {
                'success': True,
                'paymentLink': invoice.bot_invoice_url,
                'invoiceId': invoice.invoice_id
            }
        except Exception as e:
            logger.error(f"Payment creation error: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def verify_payment(self, invoice_id):
        try:
            invoice = self.cryptopay.get_invoices(invoice_ids=invoice_id)
            if invoice and invoice.status == 'paid':
                return True
            return False
        except Exception as e:
            logger.error(f"Payment verification error: {str(e)}")
            return False

bot = PaymentBot()

@app.route('/api/payments', methods=['POST'])
def create_payment():
    auth_header = request.headers.get('Authorization')
    if not auth_header or auth_header != f'Bearer {bot.api_secret}':
        return jsonify({'success': False, 'error': 'Unauthorized'}), 401
    
    data = request.get_json()
    order_id = data.get('orderId')
    amount = data.get('amount')
    currency = data.get('currency', 'USD')
    
    if not all([order_id, amount]):
        return jsonify({'success': False, 'error': 'Missing required fields'}), 400
    
    result = bot.create_payment_link(order_id, amount, currency)
    return jsonify(result)

@app.route('/api/webhook/cryptopay', methods=['POST'])
def cryptopay_webhook():
    try:
        update = request.get_json()
        if not update:
            return jsonify({'status': 'error', 'message': 'Empty data'}), 400
        
        # Verify webhook signature (important for security)
        # Implementation depends on CryptoPay library version
        
        if update.get('status') == 'paid':
            order_id = update.get('payload')
            invoice_id = update.get('invoice_id')
            
            # Verify payment
            if bot.verify_payment(invoice_id):
                # Notify main server
                # In production, use async task queue
                import requests
                requests.post(
                    'http://localhost:3000/api/payments/confirm',
                    json={'orderId': order_id, 'invoiceId': invoice_id},
                    headers={'Authorization': f'Bearer {bot.api_secret}'}
                )
                
                # Notify user
                user_chat_id = update.get('user_chat_id')
                if user_chat_id:
                    bot.bot.send_message(
                        chat_id=user_chat_id,
                        text=f"✅ Payment confirmed! Order #{order_id} is completed."
                    )
                
                return jsonify({'status': 'success'})
        
        return jsonify({'status': 'ignored'})
    except Exception as e:
        logger.error(f"Webhook error: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/health')
def health_check():
    return jsonify({'status': 'ok'})

def run_bot():
    bot.dispatcher.start_polling()

if __name__ == '__main__':
    # Start bot polling in a separate thread
    bot_thread = threading.Thread(target=run_bot)
    bot_thread.start()
    
    # Start Flask server
    app.run(host='0.0.0.0', port=5000, debug=False)

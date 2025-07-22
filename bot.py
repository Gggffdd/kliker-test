import os
from flask import Flask
app = Flask(__name__)

@app.route('/')
def home():
    return "Бот работает! Добавьте /webhook для Telegram"

@app.route('/webhook', methods=['POST'])
def webhook():
    return "Это вебхук", 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)

from flask import Flask, request, jsonify
import requests
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

# Конфигурация
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
BITRIX_WEBHOOK = os.getenv('BITRIX_WEBHOOK')

def send_telegram_message(chat_id, text):
    """Отправка сообщения в Telegram"""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    data = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML"
    }
    response = requests.post(url, json=data)
    return response.json()

@app.route('/webhook/bitrix', methods=['POST'])
def bitrix_webhook():
    """Обработка вебхука от Bitrix24"""
    data = request.json
    
    # Проверяем, что это комментарий к сделке
    if data.get('event') == 'ONCRMDEALCOMMENTADD':
        comment_data = data.get('data', {})
        deal_id = comment_data.get('FIELDS', {}).get('ENTITY_ID')
        
        # Получаем информацию о сделке
        deal_url = f"{BITRIX_WEBHOOK}crm.deal.get.json"
        deal_params = {"id": deal_id}
        deal_response = requests.get(deal_url, params=deal_params)
        deal_info = deal_response.json().get('result', {})
        
        # Получаем Telegram ID из пользовательского поля
        telegram_id = deal_info.get('UF_CRM_DEAL_TELEGRAM_ID')
        
        if telegram_id:
            # Получаем текст комментария
            comment_text = comment_data.get('FIELDS', {}).get('COMMENT', '')
            
            # Отправляем сообщение в Telegram
            message = f"💬 <b>Сообщение от менеджера:</b>\n\n{comment_text}"
            send_telegram_message(telegram_id, message)
    
    return jsonify({"status": "ok"})

@app.route('/webhook/telegram', methods=['POST'])
def telegram_webhook():
    """Обработка вебхука от Telegram"""
    data = request.json
    
    # Проверяем, что это сообщение от пользователя
    if 'message' in data:
        message = data['message']
        chat_id = message['chat']['id']
        text = message.get('text', '')
        
        # Получаем список сделок с этим Telegram ID
        deals_url = f"{BITRIX_WEBHOOK}crm.deal.list.json"
        deals_params = {
            "filter[UF_CRM_DEAL_TELEGRAM_ID]": str(chat_id),
            "select": ["ID", "TITLE"]
        }
        deals_response = requests.get(deals_url, params=deals_params)
        deals = deals_response.json().get('result', [])
        
        if deals:
            # Берем последнюю сделку
            deal = deals[0]
            deal_id = deal['ID']
            
            # Добавляем комментарий к сделке
            comment_url = f"{BITRIX_WEBHOOK}crm.timeline.comment.add.json"
            comment_data = {
                "fields": {
                    "ENTITY_ID": deal_id,
                    "ENTITY_TYPE": "deal",
                    "COMMENT": f"Сообщение от клиента:\n{text}",
                    "AUTHOR_ID": BITRIX_RESPONSIBLE_ID
                }
            }
            requests.post(comment_url, json=comment_data)
    
    return jsonify({"status": "ok"})

@app.route("/bitrix-to-telegram", methods=["POST"])
def bitrix_to_telegram():
    data = request.json
    with open("bitrix_debug.json", "w") as f:
        import json
        json.dump(data, f, indent=2)
    # ... остальной код ...

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000) 
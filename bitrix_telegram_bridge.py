from flask import Flask, request, jsonify
import requests
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

# Конфигурация
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
BITRIX_WEBHOOK = os.getenv('BITRIX_WEBHOOK')
BITRIX_WEBHOOK_DEAL = os.getenv('BITRIX_WEBHOOK_DEAL') or BITRIX_WEBHOOK

def send_telegram_message(chat_id, text):
    """Отправка сообщения в Telegram"""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    data = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
    response = requests.post(url, json=data)
    print("Telegram response:", response.text)

@app.route('/webhook/bitrix', methods=['POST'])
def bitrix_webhook():
    """Обработка вебхука от Bitrix24"""
    data = request.json
    
    print("Webhook called, data:", data)
    
    # Проверяем, что это комментарий к сделке
    if data.get('event') == 'ONCRMDEALCOMMENTADD':
        comment_data = data.get('data', {})
        deal_id = comment_data.get('FIELDS', {}).get('ENTITY_ID')
        
        # Получаем информацию о сделке
        deal_url = f"{BITRIX_WEBHOOK_DEAL}crm.deal.get.json"
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
            print("Telegram ID:", telegram_id)
            print("Comment text:", comment_text)
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
        deals_url = f"{BITRIX_WEBHOOK_DEAL}crm.deal.list.json"
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
            comment_url = f"{BITRIX_WEBHOOK_DEAL}crm.timeline.comment.add.json"
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
    with open("bitrix_debug.txt", "w") as f:
        f.write("Headers:\n" + str(request.headers) + "\n\n")
        f.write("Data:\n" + str(request.data) + "\n\n")
        f.write("Form:\n" + str(request.form) + "\n\n")
        try:
            f.write("JSON:\n" + str(request.get_json(force=True)) + "\n\n")
        except Exception as e:
            f.write(f"JSON decode error: {e}\n\n")
    return "OK", 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000) 
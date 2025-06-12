import os
import logging
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext, ConversationHandler
import requests
import json
import time
from dotenv import load_dotenv

# Config (replace with os.environ.get for production)
load_dotenv()
TELEGRAM_API_TOKEN = os.getenv("TELEGRAM_API_TOKEN")
BITRIX_WEBHOOK = os.getenv("BITRIX_WEBHOOK")
BITRIX_RESPONSIBLE_ID = int(os.getenv("BITRIX_RESPONSIBLE_ID"))
BITRIX_CATEGORY_ID = int(os.getenv("BITRIX_CATEGORY_ID"))
BITRIX_STAGE_ID = os.getenv("BITRIX_STAGE_ID")
BITRIX_DISK_FOLDER_ID = int(os.getenv("BITRIX_DISK_FOLDER_ID"))  # <-- ID вашей папки на диске Bitrix24

# States for ConversationHandler
ASK_PHONE, ASK_SCREENSHOT = range(2)

# Символьные коды пользовательских полей
UF_FIELD_1 = "UF_CRM_DEAL_1739785496195"
UF_FIELD_2 = "UF_CRM_1749667910221"
UF_TELEGRAM_ID = "UF_CRM_DEAL_TELEGRAM_ID"  # ID созданного поля для Telegram ID

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def start_keyboard():
    return ReplyKeyboardMarkup(
        [[KeyboardButton("Send phone number", request_contact=True)]],
        resize_keyboard=True,
        one_time_keyboard=True
    )

def start(update: Update, context: CallbackContext):
    logger.info(f"User {update.effective_user.id} started the bot")
    update.message.reply_text(
        "👋 Добро пожаловать в бот переноса бонусов Subway!\nПожалуйста, отправьте свой номер телефона для начала.",
        reply_markup=start_keyboard()
    )
    return ASK_PHONE

def ask_screenshot(update: Update, context: CallbackContext):
    logger.info(f"User {update.effective_user.id} sent phone number")
    if update.message.contact:
        phone = update.message.contact.phone_number
        logger.info(f"Phone number from contact: {phone}")
    else:
        phone = update.message.text
        logger.info(f"Phone number from text: {phone}")
    context.user_data['phone'] = phone
    update.message.reply_text(
        "Спасибо! Теперь, пожалуйста, загрузите скриншот из старого приложения Subway с вашим бонусным балансом."
    )
    return ASK_SCREENSHOT

def handle_screenshot(update: Update, context: CallbackContext):
    logger.info(f"User {update.effective_user.id} sent a photo")
    if not update.message.photo:
        logger.warning("User sent message without photo")
        update.message.reply_text("Пожалуйста, загрузите скриншот (фото) из старого приложения.")
        return ASK_SCREENSHOT
    # Get the largest photo
    photo_file = update.message.photo[-1]
    logger.info(f"Photo file_id: {photo_file.file_id}")
    photo = photo_file.get_file()
    photo_bytes = photo.download_as_bytearray()
    # Save photo temporarily
    photo_path = f"/tmp/{update.message.from_user.id}_screenshot_{int(time.time())}.jpg"
    with open(photo_path, 'wb') as f:
        f.write(photo_bytes)
    logger.info(f"Photo saved to {photo_path}")
    # Prepare Bitrix24 deal
    phone = context.user_data.get('phone', 'Unknown')
    telegram_id = update.message.from_user.id
    logger.info(f"Creating Bitrix24 deal for phone: {phone}, telegram_id: {telegram_id}")

    try:
        # Step 1: Get uploadUrl
        upload_disk_url = f"{BITRIX_WEBHOOK}disk.folder.uploadfile.json?id={BITRIX_DISK_FOLDER_ID}"
        logger.info("Requesting uploadUrl from Bitrix24 disk")
        filename = os.path.basename(photo_path)
        with open(photo_path, 'rb') as f:
            r = requests.post(upload_disk_url, files={'file': (filename, f)})
        r.raise_for_status()
        response_data = r.json()
        logger.info(f"Bitrix24 response: {json.dumps(response_data, indent=2)}")
        if 'result' not in response_data or 'uploadUrl' not in response_data['result']:
            raise Exception(f"Unexpected response format: {response_data}")
        upload_url = response_data['result']['uploadUrl']
        logger.info(f"Got uploadUrl: {upload_url}")

        # Step 2: Upload file to uploadUrl
        with open(photo_path, 'rb') as f:
            upload_response = requests.post(upload_url, files={'file': f})
        try:
            upload_response.raise_for_status()
        except requests.exceptions.HTTPError:
            logger.error(f"Upload error response: {upload_response.text}")
            raise
        upload_result = upload_response.json()
        logger.info(f"Upload result: {json.dumps(upload_result, indent=2)}")
        if 'result' not in upload_result or 'ID' not in upload_result['result']:
            raise Exception(f"No file id in upload result: {upload_result}")
        file_id = upload_result['result']['ID']
        logger.info(f"File uploaded successfully, file_id: {file_id}")

        # Step 3: Create the deal with both custom fields
        deal_fields = {
            'TITLE': f'Subway Bonus Transfer: {phone}',
            'CATEGORY_ID': BITRIX_CATEGORY_ID,
            'STAGE_ID': BITRIX_STAGE_ID,
            'ASSIGNED_BY_ID': BITRIX_RESPONSIBLE_ID,
            'COMMENTS': f'Phone: {phone}\nTelegram ID: {telegram_id}',
            UF_FIELD_1: file_id,
            UF_FIELD_2: file_id,
            UF_TELEGRAM_ID: str(telegram_id)  # Сохраняем Telegram ID в пользовательском поле
        }
        upload_url = f"{BITRIX_WEBHOOK}crm.deal.add.json"
        logger.info("Creating Bitrix24 deal")
        r2 = requests.post(upload_url, json={'fields': deal_fields})
        r2.raise_for_status()
        deal_response = r2.json()
        logger.info(f"Deal creation response: {json.dumps(deal_response, indent=2)}")
        if 'result' in deal_response:
            logger.info("Deal created successfully")
            update.message.reply_text("✅ Ваша заявка отправлена! Наши сотрудники свяжутся с вами в ближайшее время.")

            # После создания сделки:
            deal_id = deal_response['result']  # ID созданной сделки
            download_url = upload_result['result'].get('DOWNLOAD_URL')
            comment_text = "Фото приложения"
            if download_url:
                comment_text += f"\n[img width=300]{download_url}[/img]"

            timeline_url = f"{BITRIX_WEBHOOK}crm.timeline.comment.add.json"
            timeline_data = {
                "fields": {
                    "ENTITY_ID": deal_id,
                    "ENTITY_TYPE": "deal",
                    "COMMENT": comment_text,
                    "AUTHOR_ID": BITRIX_RESPONSIBLE_ID
                }
            }
            timeline_resp = requests.post(timeline_url, json=timeline_data)
            logger.info(f"Timeline comment response: {timeline_resp.text}")
        else:
            raise Exception(f"Failed to create deal: {deal_response}")
    except requests.exceptions.RequestException as e:
        logger.error(f"Network error: {str(e)}")
        update.message.reply_text("❌ Произошла сетевая ошибка. Пожалуйста, попробуйте позже.")
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        update.message.reply_text("❌ Произошла ошибка при отправке вашей заявки. Пожалуйста, попробуйте позже.")
    finally:
        if os.path.exists(photo_path):
            os.remove(photo_path)
            logger.info(f"Temporary file {photo_path} removed")
    return ConversationHandler.END

def cancel(update: Update, context: CallbackContext):
    logger.info(f"User {update.effective_user.id} cancelled the operation")
    update.message.reply_text('Операция отменена. Чтобы начать заново, введите /start.')
    return ConversationHandler.END

def error_handler(update: Update, context: CallbackContext):
    logger.error(f"Update {update} caused error {context.error}")

def main():
    logger.info("Starting bot...")
    updater = Updater(TELEGRAM_API_TOKEN)
    dp = updater.dispatcher

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            ASK_PHONE: [MessageHandler(Filters.contact | Filters.text & ~Filters.command, ask_screenshot)],
            ASK_SCREENSHOT: [MessageHandler(Filters.photo, handle_screenshot)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )
    dp.add_handler(conv_handler)
    dp.add_error_handler(error_handler)

    logger.info("Bot is running...")
    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()

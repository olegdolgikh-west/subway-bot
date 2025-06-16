import os
import logging
import re
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext, ConversationHandler
import time
from dotenv import load_dotenv

# Config
load_dotenv()
TELEGRAM_API_TOKEN = os.getenv("TELEGRAM_API_TOKEN")
TARGET_GROUP_ID = os.getenv("TARGET_GROUP_ID")  # ID группы для пересылки сообщений

# States for ConversationHandler
ASK_PHONE, ASK_SCREENSHOT = range(2)

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def start_keyboard():
    return ReplyKeyboardMarkup(
        [[KeyboardButton("Отправить номер телефона", request_contact=True)]],
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

def is_valid_phone(phone: str) -> bool:
    """Проверяет, является ли строка валидным номером телефона."""
    # Удаляем все нецифровые символы
    phone = re.sub(r'\D', '', phone)
    # Проверяем длину (должно быть 10-15 цифр)
    return 10 <= len(phone) <= 15

def ask_screenshot(update: Update, context: CallbackContext):
    logger.info(f"User {update.effective_user.id} sent phone number")
    if update.message.contact:
        phone = update.message.contact.phone_number
        logger.info(f"Phone number from contact: {phone}")
    else:
        phone = update.message.text
        logger.info(f"Phone number from text: {phone}")
        
        # Проверяем валидность номера телефона
        if not is_valid_phone(phone):
            update.message.reply_text(
                "❌ Пожалуйста, введите корректный номер телефона или поделитесь контактом, нажав на кнопку ниже.",
                reply_markup=start_keyboard()
            )
            return ASK_PHONE
    
    context.user_data['phone'] = phone
    
    # Отправляем пример скриншота с подробными инструкциями
    update.message.reply_text(
        "Спасибо! Теперь, пожалуйста, загрузите скриншот из старого приложения Subway с вашим бонусным балансом.\n\n"
        "Как получить скриншот:\n"
        "1. Откройте старое приложение Subway\n"
        "2. Нажмите на три полоски (меню) в верхнем левом углу\n"
        "3. Нажмите на свое имя/профиль\n"
        "4. Сделайте скриншот экрана с балансом бонусов\n\n"
        "Вот пример того, как должен выглядеть скриншот:"
    )
    
    # Отправляем пример скриншота
    update.message.reply_photo(
        photo='AgACAgIAAxkBAAIBsmhQLP_7jf7e8WPjy_MziDZmE7XNAAJm-DEbNSWBSqmshIIrHby9AQADAgADeQADNgQ',
        caption="Пример скриншота с балансом бонусов"
    )
    
    return ASK_SCREENSHOT

def handle_screenshot(update: Update, context: CallbackContext):
    logger.info(f"User {update.effective_user.id} sent a photo")
    if not update.message.photo:
        logger.warning("User sent message without photo")
        update.message.reply_text("Пожалуйста, загрузите скриншот (фото) из старого приложения.")
        return ASK_SCREENSHOT

    # Get user information
    user = update.message.from_user
    phone = context.user_data.get('phone', 'Unknown')
    
    # Prepare message text
    message_text = (
        f"🆕 Новая заявка на перенос бонусов!\n\n"
        f"👤 Пользователь: {user.first_name} {user.last_name if user.last_name else ''}\n"
        f"🆔 Telegram ID: {user.id}\n"
        f"📱 Телефон: {phone}\n"
        f"👤 Username: @{user.username if user.username else 'не указан'}"
    )

    try:
        # Forward the photo and message to the target group
        context.bot.send_photo(
            chat_id=TARGET_GROUP_ID,
            photo=update.message.photo[-1].file_id,
            caption=message_text
        )
        
        update.message.reply_text("✅ Ваша заявка отправлена! Наши сотрудники свяжутся с вами в ближайшее время.")
        logger.info(f"Successfully forwarded information to group {TARGET_GROUP_ID}")
        
    except Exception as e:
        logger.error(f"Error forwarding message to group: {str(e)}")
        update.message.reply_text("❌ Произошла ошибка при отправке вашей заявки. Пожалуйста, попробуйте позже.")
    
    return ConversationHandler.END

def cancel(update: Update, context: CallbackContext):
    logger.info(f"User {update.effective_user.id} cancelled the operation")
    update.message.reply_text('Операция отменена. Чтобы начать заново, введите /start.')
    return ConversationHandler.END

def error_handler(update: Update, context: CallbackContext):
    logger.error(f"Update {update} caused error {context.error}")

def get_file_id(update: Update, context: CallbackContext):
    if update.message.photo:
        file_id = update.message.photo[-1].file_id
        update.message.reply_text(f"File ID: {file_id}")

def main():
    logger.info("Starting bot...")
    updater = Updater(TELEGRAM_API_TOKEN)
    dp = updater.dispatcher

    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler('start', start),
            MessageHandler(Filters.text & ~Filters.command, start)  # Добавляем обработчик для любого текстового сообщения
        ],
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

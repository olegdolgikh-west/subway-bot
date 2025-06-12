# Subway Bonus Transfer Bot

Telegram бот для переноса бонусов из старого приложения Subway в новое. Интегрирован с Bitrix24 для управления заявками.

## Функциональность

- Прием номера телефона пользователя
- Загрузка скриншота с балансом бонусов
- Создание сделки в Bitrix24
- Двусторонняя коммуникация между менеджером и клиентом через Bitrix24 и Telegram

## Установка

1. Клонируйте репозиторий:
```bash
git clone https://github.com/your-username/subway-bot.git
cd subway-bot
```

2. Создайте виртуальное окружение и установите зависимости:
```bash
python3 -m venv venv
source venv/bin/activate  # для Linux/Mac
# или
venv\Scripts\activate  # для Windows
pip install -r requirements.txt
```

3. Создайте файл .env с необходимыми переменными окружения:
```
TELEGRAM_BOT_TOKEN=ваш-токен-бота
BITRIX_WEBHOOK=ваш-вебхук-bitrix24
```

## Запуск

1. Запуск основного бота:
```bash
python bot.py
```

2. Запуск моста между Bitrix24 и Telegram:
```bash
python bitrix_telegram_bridge.py
```

## Структура проекта

- `bot.py` - основной бот для приема заявок
- `bitrix_telegram_bridge.py` - мост между Bitrix24 и Telegram
- `add_telegram_field.py` - скрипт для добавления поля Telegram ID в Bitrix24
- `requirements.txt` - зависимости проекта

## Настройка Bitrix24

1. Создайте пользовательское поле для Telegram ID в сделках
2. Настройте вебхук для получения уведомлений о новых комментариях
3. Укажите URL вебхука в настройках интеграции

## Лицензия

MIT 
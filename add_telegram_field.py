import requests

BITRIX_WEBHOOK = "https://subwest.bitrix24.ru/rest/8/9wd0tkluq4jgn78m/"

# Параметры нового пользовательского поля
field_data = {
    "fields": {
        "FIELD_NAME": "UF_CRM_DEAL_TELEGRAM_ID",
        "EDIT_FORM_LABEL": {
            "ru": "Telegram ID пользователя"
        },
        "LIST_COLUMN_LABEL": {
            "ru": "Telegram ID"
        },
        "USER_TYPE_ID": "string",
        "XML_ID": "TELEGRAM_ID",
        "SETTINGS": {
            "DEFAULT_VALUE": "",
            "SIZE": 20,
            "ROWS": 1,
            "MIN_LENGTH": 0,
            "MAX_LENGTH": 0,
            "REGEXP": ""
        }
    }
}

# Добавляем поле в сделки
url = f"{BITRIX_WEBHOOK}crm.deal.userfield.add.json"
response = requests.post(url, json=field_data)

print("Response:", response.json()) 
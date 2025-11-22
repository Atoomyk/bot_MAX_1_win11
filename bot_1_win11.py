import asyncio
import logging
import os
import time
import re
import aiohttp
import json
from functools import wraps
from dotenv import load_dotenv

from maxapi import Bot, Dispatcher
from maxapi.types import (
    BotStarted,
    MessageCallback,
    MessageCreated,
    Attachment,
    ButtonsPayload,
    CallbackButton,
    LinkButton,
    RequestContactButton
)
from maxapi.utils.inline_keyboard import AttachmentType

# Импорт системы логирования
from logging_config import setup_logging, log_user_event, log_system_event, log_data_event, log_security_event, \
    log_transport_event

# Настройка логирования
setup_logging()

# Загрузка переменных окружения
load_dotenv()
TOKEN = os.getenv("MAXAPI_TOKEN")

X_TUNNEL_URL = "https://0a430bc8-6c9e-491d-b543-48003d4177ef.tunnel4.com"

bot = Bot(TOKEN)
dp = Dispatcher()

# Константы API
MAX_API_BASE_URL = "https://platform-api.max.ru"
HEADERS = {
    "Accept": "application/json",
    "Content-Type": "application/json",
    "Authorization": f"{TOKEN}"
}

# Callback-константы
SOGL_LINK = "https://sevmiac.ru/upload/iblock/d73/sttjnvlhg3j2df943ve0fv3husrlm8oj.pdf"
CONTINUE_CALLBACK = "start_continue"
AGREEMENT_CALLBACK = "agreement_accepted"
ADMIN_CONTACT = "@admin_MIAC"

CORRECT_FIO_CALLBACK = "correct_fio"
CORRECT_BIRTH_DATE_CALLBACK = "correct_birth_date"
CORRECT_PHONE_CALLBACK = "correct_phone"
CONFIRM_DATA_CALLBACK = "confirm_data"
CONFIRM_PHONE_CALLBACK = "confirm_phone"
REJECT_PHONE_CALLBACK = "reject_phone"

# Ссылки для кнопок главного меню
GOSUSLUGI_APPOINTMENT_URL = "https://www.gosuslugi.ru/10700"
GOSUSLUGI_MEDICAL_EXAM_URL = "https://www.gosuslugi.ru/647521/1/form"
GOSUSLUGI_DOCTOR_HOME_URL = "https://www.gosuslugi.ru/600361"
GOSUSLUGI_ATTACH_TO_POLYCLINIC_URL = "https://www.gosuslugi.ru/600360"
CONTACT_CENTER_URL = "https://sevmiac.ru/ekc/"
MAP_OF_MEDICAL_INSTITUTIONS_URL = "https://yandex.ru/maps/959/sevastopol/search/%D0%B1%D0%BE%D0%BB%D1%8C%D0%BD%D0%B8%D1%86%D1%8B%20%D1%81%D0%B5%D0%B2%D0%B0%D1%81%D1%82%D0%BE%D0%BF%D0%BE%D0%BB%D1%8C/?ll=33.542596%2C44.577279&profile-mode=1&sctx=ZAAAAAgCEAAaKAoSCc0iFFtBJUNAEfYM4ZhlAUtAEhIJPgXAeAYN1z8RHCjwTj49wj8iBgABAgQFBigEOABAvwdIAWIaYWRkX3NuaXBwZXQ9bWV0YXJlYWx0eS8xLnhiHGFkZF9zbmlwcGV0=PW1haW5fYXNwZWN0cy8xLnhiKXJlYXJyPXNjaGVtZV9Mb2NhbC9HZW8vTWV0YVJlYWx0eUtwcz0xMDAyagJydZUBAAAAAJ0BzczMPaABAagBAL0B09dLsMIBhwGI0oWYBI%2BevdYEmM%2BXmoAChf6Czky%2F3bm7BMGrr6oE1Oz6ngT91qOQtQK8ib%2FOiAXoteKRBMXVwJYEgcLQhgaczPbLBriO%2FskE1uOJgtoFkJjwtQaD48Tekgeq8ezXBq%2FLm%2BDCBMfokZuaA8nSo%2FkEiuHzlv8GktWn1IYB7bCdwuQF04y6xTmCAifQsdC%2B0LvRjNC90LjRhtGLINGB0LXQstCw0YHRgtC%2B0L%2FQvtC70YyKAiwxODQxMDU5NTYkMTg0MTA1OTU4JDUzNDM3MjYwNTU5JDE5ODM5NTI4OTU0MpICAzk1OZoCDGRlc2t0b3AtbWFwc6oCDDE2NTc0MjkxODkzOQ%3D%3D&sll=33.542596%2C44.577279&source=wizbiz_new_map_multi&sspn=0.240326%2C0.097050&z=13"

# Импорт базы данных
from user_database import db

# Глобальные переменные
user_states = {}
processed_events = {}  # Объединенная защита от дублирования


# --- УНИВЕРСАЛЬНЫЕ ФУНКЦИИ ---

def anti_duplicate(rate_limit=1.0):
    """Декоратор для защиты от дублирования событий"""

    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            event = args[0] if args else None
            chat_id = None

            # Получаем chat_id из разных типов событий
            if hasattr(event, 'message') and hasattr(event.message, 'recipient'):
                chat_id = str(event.message.recipient.chat_id)
            elif hasattr(event, 'chat_id'):
                chat_id = str(event.chat_id)

            if not chat_id:
                return await func(*args, **kwargs)

            # Проверяем частоту запросов
            current_time = time.time()
            if chat_id in processed_events:
                last_time = processed_events[chat_id].get('last_time', 0)
                if current_time - last_time < rate_limit:
                    return

            # Обновляем время последнего обработки
            if chat_id not in processed_events:
                processed_events[chat_id] = {}
            processed_events[chat_id]['last_time'] = current_time

            return await func(*args, **kwargs)

        return wrapper

    return decorator


def create_keyboard(buttons_config):
    """Универсальная функция создания клавиатуры"""
    if not buttons_config:
        return None

    # Поддерживаем разные форматы кнопок
    formatted_buttons = []
    for row in buttons_config:
        button_row = []
        for button in row:
            if isinstance(button, dict):
                # Создаем кнопку из словаря
                if button.get('type') == 'callback':
                    btn = CallbackButton(text=button['text'], payload=button['payload'])
                elif button.get('type') == 'link':
                    btn = LinkButton(text=button['text'], url=button['url'])
                elif button.get('type') == 'contact':
                    btn = RequestContactButton(text=button['text'])
                else:
                    continue
                button_row.append(btn)
            else:
                # Уже созданная кнопка
                button_row.append(button)
        if button_row:
            formatted_buttons.append(button_row)

    if not formatted_buttons:
        return None

    buttons_payload = ButtonsPayload(buttons=formatted_buttons)
    return Attachment(
        type=AttachmentType.INLINE_KEYBOARD,
        payload=buttons_payload
    )


async def validate_and_process_input(chat_id_str, input_text, input_type, bot_instance, chat_id, user_data,
                                     next_step_func):
    """Универсальная функция валидации и обработки ввода"""
    validator_map = {
        'fio': db.validate_fio,
        'birth_date': db.validate_birth_date,
        'phone': db.validate_phone
    }

    error_messages = {
        'fio': "❌ Ошибка формата!\n\nПожалуйста, введите ваше ФИО в формате: Фамилия Имя Отчество\n\nПример: Иванов Иван Иванович",
        'birth_date': "❌ Ошибка формата!\n\nПожалуйста, введите дату рождения в формате: ДД.ММ.ГГГГ\n\nПример: 13.03.2003",
        'phone': "❌ Неверный формат номера телефона."
    }

    if input_type not in validator_map:
        return False

    if not validator_map[input_type](input_text):
        log_user_event(chat_id_str, f"invalid_{input_type}_format", input=input_text)
        await bot_instance.send_message(chat_id=chat_id, text=error_messages[input_type])
        return False

    # Сохраняем данные
    user_data[input_type] = input_text
    log_data_event(chat_id_str, f"{input_type}_entered", **{input_type: input_text})

    # Вызываем следующую функцию
    await next_step_func(bot_instance, chat_id, user_data)
    return True


async def request_data_correction(bot_instance: Bot, chat_id: int, user_data: dict, data_type: str):
    """Универсальная функция запроса исправления данных"""
    correction_configs = {
        'fio': {
            'state': 'waiting_fio_correction',
            'log_event': 'fio_correction_requested',
            'message': "Введите ваше ФИО для исправления:\n\nФормат: Фамилия Имя Отчество\nПример: Иванов Иван Иванович"
        },
        'birth_date': {
            'state': 'waiting_birth_date_correction',
            'log_event': 'birth_date_correction_requested',
            'message': "Введите вашу дату рождения для исправления:\n\nФормат: ДД.ММ.ГГГГ\nПример: 13.03.2003"
        }
    }

    if data_type not in correction_configs:
        return

    config = correction_configs[data_type]
    user_states[str(chat_id)] = {'state': config['state'], 'data': user_data}
    log_user_event(str(chat_id), config['log_event'])

    await bot_instance.send_message(chat_id=chat_id, text=config['message'])


# --- ОСНОВНЫЕ ФУНКЦИИ БОТА ---

async def get_webhook_subscriptions(silent=False):
    """Получить список всех вебхук-подписок"""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{MAX_API_BASE_URL}/subscriptions", headers=HEADERS) as response:
                if response.status == 200:
                    data = await response.json()
                    subscriptions = data.get('subscriptions', [])

                    if not silent:
                        print(f"\n=== ТЕКУЩИЕ ВЕБХУКИ ===")
                        print(f"Найдено подписок: {len(subscriptions)}")
                        for i, sub in enumerate(subscriptions, 1):
                            print(f"{i}. URL: {sub.get('url', 'N/A')}")
                            print(f"   Время: {sub.get('time', 'N/A')}")
                            print(f"   Типы: {', '.join(sub.get('update_types', []))}")

                    return subscriptions
                else:
                    if not silent:
                        print(f"❌ Ошибка получения вебхуков: {response.status}")
                    return []
    except Exception as e:
        if not silent:
            print(f"❌ Ошибка при запросе вебхуков: {str(e)}")
        return []


async def setup_webhook():
    """Настраивает вебхук через Xtunnel"""
    print("🔄 Настройка вебхука...")
    await get_webhook_subscriptions(silent=False)

    print(f"🔄 Устанавливаю новый вебхук: {X_TUNNEL_URL}")
    await bot.subscribe_webhook(
        url=X_TUNNEL_URL,
        update_types=["message_created", "message_callback", "bot_started"]
    )

    final_subscriptions = await get_webhook_subscriptions(silent=True)
    print("✅ Вебхук успешно настроен!" if final_subscriptions else "❌ Ошибка настройки вебхука")


def create_main_menu_keyboard():
    """Создает клавиатуру главного меню"""
    buttons_config = [
        [{'type': 'link', 'text': 'Записаться на приём к врачу', 'url': GOSUSLUGI_APPOINTMENT_URL}],
        [{'type': 'link', 'text': 'Профосмотр/диспансеризация', 'url': GOSUSLUGI_MEDICAL_EXAM_URL}],
        [{'type': 'link', 'text': 'Вызов врача на дом', 'url': GOSUSLUGI_DOCTOR_HOME_URL}],
        [{'type': 'link', 'text': 'Прикрепление к поликлинике', 'url': GOSUSLUGI_ATTACH_TO_POLYCLINIC_URL}],
        [{'type': 'link', 'text': 'Ближайшие гос мед учреждения', 'url': MAP_OF_MEDICAL_INSTITUTIONS_URL}],
        [{'type': 'link', 'text': 'Единый контакт-центр', 'url': CONTACT_CENTER_URL}]
    ]
    return create_keyboard(buttons_config)


async def send_main_menu(bot_instance: Bot, chat_id: int, greeting_name: str):
    """Отправляет главное меню с приветствием"""
    keyboard = create_main_menu_keyboard()
    await bot_instance.send_message(
        chat_id=chat_id,
        text=f"Здравствуйте, {greeting_name}!\n\nВыберите услугу:",
        attachments=[keyboard] if keyboard else []
    )


async def send_agreement_message(bot_instance: Bot, chat_id: int):
    """Отправляет сообщение с соглашением"""
    keyboard = create_keyboard([[
        {'type': 'callback', 'text': 'Согласие на обработку персональных данных', 'payload': AGREEMENT_CALLBACK}
    ]])

    await bot_instance.send_message(
        chat_id=chat_id,
        text=f'Продолжая, Вы даёте согласие на обработку персональных данных.\nОзнакомиться с документом вы можете по ссылке {SOGL_LINK}',
        attachments=[keyboard] if keyboard else []
    )


async def start_registration_process(bot_instance: Bot, chat_id: int):
    """Начинает процесс регистрации - подтверждение телефона"""
    user_states[str(chat_id)] = {'state': 'waiting_phone_confirmation', 'data': {}}
    log_user_event(str(chat_id), "registration_started")

    await bot_instance.send_message(
        chat_id=chat_id,
        text='Для начала работы необходимо подтвердить номер и пройти регистрацию.'
    )
    await request_contact(bot_instance, chat_id)


async def request_contact(bot_instance: Bot, chat_id: int):
    """Запрашивает контакт пользователя"""
    keyboard = create_keyboard([[
        {'type': 'contact', 'text': '📇 Отправить контакт'}
    ]])

    await bot_instance.send_message(
        chat_id=chat_id,
        text="Нажмите кнопку ниже чтобы поделиться контактом:",
        attachments=[keyboard] if keyboard else []
    )


async def send_phone_confirmation(bot_instance: Bot, chat_id: int, phone: str):
    """Отправляет сообщение с подтверждением номера телефона"""
    keyboard = create_keyboard([[
        {'type': 'callback', 'text': '✅ Да, номер верный', 'payload': CONFIRM_PHONE_CALLBACK},
        {'type': 'callback', 'text': '❌ Нет, неверный номер', 'payload': REJECT_PHONE_CALLBACK}
    ]])

    await bot_instance.send_message(
        chat_id=chat_id,
        text=f"📞 Ваш номер телефона определён:\n\n📱 {phone}\n\nПожалуйста, проверьте актуальность номера:",
        attachments=[keyboard] if keyboard else []
    )


async def handle_incorrect_phone(bot_instance: Bot, chat_id: int):
    """Обработка неверного номера телефона"""
    log_user_event(str(chat_id), "phone_rejected")
    await bot_instance.send_message(
        chat_id=chat_id,
        text="❌ Пожалуйста, отправьте контакт с правильным номером телефона."
    )
    await request_contact(bot_instance, chat_id)


async def start_fio_request(bot_instance: Bot, chat_id: int, user_data: dict):
    """Начинает процесс ввода ФИО"""
    user_states[str(chat_id)] = {'state': 'waiting_fio', 'data': user_data}
    log_user_event(str(chat_id), "fio_input_started")

    await bot_instance.send_message(
        chat_id=chat_id,
        text='Пожалуйста, введите ваше ФИО в формате:\nФамилия Имя Отчество\n\nПример: Иванов Иван Иванович'
    )


async def request_birth_date(bot_instance: Bot, chat_id: int, user_data: dict):
    """Запрашивает дату рождения"""
    user_states[str(chat_id)] = {'state': 'waiting_birth_date', 'data': user_data}

    await bot_instance.send_message(
        chat_id=chat_id,
        text="Отлично!\nТеперь введите вашу дату рождения\n\nФормат: ДД.ММ.ГГГГ\nПример: 13.03.2003"
    )


async def send_confirmation_message(bot_instance: Bot, chat_id: int, user_data: dict):
    """Отправляет сообщение с подтверждением данных"""
    fio = user_data.get('fio', 'Не указано')
    birth_date = user_data.get('birth_date', 'Не указано')
    phone = user_data.get('phone', 'Не указано')

    log_data_event(str(chat_id), "confirmation_prepared", fio=fio, birth_date=birth_date, phone=phone)

    keyboard = create_keyboard([
        [{'type': 'callback', 'text': '⚠️ Исправить ФИО', 'payload': CORRECT_FIO_CALLBACK}],
        [{'type': 'callback', 'text': '⚠️ Исправить дату рождения', 'payload': CORRECT_BIRTH_DATE_CALLBACK}],
        [{'type': 'callback', 'text': '✅ Всё верно, подтвердить', 'payload': CONFIRM_DATA_CALLBACK}]
    ])

    await bot_instance.send_message(
        chat_id=chat_id,
        text=f"📋 Пожалуйста, проверьте введенные данные:\n\n👤 ФИО: {fio}\n🎂 Дата рождения: {birth_date}\n📞 Телефон: {phone}\n\nЕсли всё верно - нажмите 'Подтвердить', или выберите что нужно исправить:",
        attachments=[keyboard] if keyboard else []
    )


async def complete_registration(bot_instance: Bot, chat_id: int, user_data: dict):
    """Завершает регистрацию и показывает главное меню"""
    fio = user_data['fio']
    birth_date = user_data['birth_date']
    phone = user_data['phone']

    success = db.register_user(str(chat_id), fio, phone, birth_date)

    if success:
        user_states.pop(str(chat_id), None)
        greeting_name = db.get_user_greeting(str(chat_id))
        log_data_event(str(chat_id), "registration_completed", fio=fio, phone=phone, status="success")

        await bot_instance.send_message(
            chat_id=chat_id,
            text="✅ Успешная регистрация!\nТеперь вы можете пользоваться всеми функциями бота."
        )
        await send_main_menu(bot_instance, chat_id, greeting_name)
    else:
        user_states.pop(str(chat_id), None)
        log_data_event(str(chat_id), "registration_failed", fio=fio, phone=phone, status="duplicate")
        await bot_instance.send_message(
            chat_id=chat_id,
            text=f"🚨 Ошибка при регистрации. Комбинация ФИО и телефона уже существует.\n\nПожалуйста, обратитесь к администратору, {ADMIN_CONTACT}."
        )


# --- ОБРАБОТЧИКИ СОБЫТИЙ ---

@dp.bot_started()
@anti_duplicate()
async def bot_started(event: BotStarted):
    """Обработка запуска бота"""
    chat_id = event.chat_id
    chat_id_str = str(chat_id)

    log_user_event(chat_id_str, "bot_started")

    try:
        if db.is_user_registered(chat_id_str):
            greeting_name = db.get_user_greeting(chat_id_str)
            log_user_event(chat_id_str, "already_registered")
            await send_main_menu(event.bot, chat_id, greeting_name)
        else:
            log_user_event(chat_id_str, "new_user_detected")
            keyboard = create_keyboard([[
                {'type': 'callback', 'text': 'Продолжить', 'payload': CONTINUE_CALLBACK}
            ]])

            await event.bot.send_message(
                chat_id=chat_id,
                text='Здравствуйте! 👩‍⚕️\n\nВы обратились в Медицинский информационно-аналитический центр города Севастополя.\nНаша система позволяет Вам удобно и быстро решить следующие задачи:\n\n📌 Записаться на приём к врачу;\n📌 Вызвать врача на дом;\n📌 Записаться на профилактический медосмотр/диспансеризацию;\n📌 Прикрепиться к поликлинике;\n📌 Получать уведомления о записи к врачу с возможностью её отмены;\n📌 Найти ближайшие государственные медицинские учреждения.',
                attachments=[keyboard] if keyboard else []
            )
    except Exception as e:
        log_system_event("bot_started", "message_send_failed", error=str(e), chat_id=chat_id_str)


@dp.message_callback()
@anti_duplicate()
async def message_callback(event: MessageCallback):
    """Обработка нажатий на инлайн-кнопки"""
    chat_id = event.message.recipient.chat_id
    chat_id_str = str(chat_id)
    payload = event.callback.payload

    log_user_event(chat_id_str, "button_pressed", payload=payload)

    # Обработка разных callback-ов
    if payload == CONTINUE_CALLBACK:
        await send_agreement_message(event.bot, chat_id)

    elif payload == AGREEMENT_CALLBACK:
        log_security_event(chat_id_str, "consent_accepted")
        await start_registration_process(event.bot, chat_id)

    elif payload == CONFIRM_PHONE_CALLBACK:
        await handle_phone_confirmation(event, chat_id_str, chat_id)

    elif payload == REJECT_PHONE_CALLBACK:
        log_user_event(chat_id_str, "phone_rejected")
        await handle_incorrect_phone(event.bot, chat_id)

    elif payload == CORRECT_FIO_CALLBACK:
        await handle_data_correction(event, chat_id_str, chat_id, 'fio')

    elif payload == CORRECT_BIRTH_DATE_CALLBACK:
        await handle_data_correction(event, chat_id_str, chat_id, 'birth_date')

    elif payload == CONFIRM_DATA_CALLBACK:
        await handle_data_confirmation(event, chat_id_str, chat_id)


async def handle_phone_confirmation(event, chat_id_str, chat_id):
    """Обработка подтверждения телефона"""
    log_user_event(chat_id_str, "phone_confirmed")
    current_state = user_states.get(chat_id_str, {})
    user_data = current_state.get('data', {})

    if 'phone' not in user_data:
        log_data_event(chat_id_str, "phone_missing_on_confirmation")
        await event.bot.send_message(chat_id=chat_id,
                                     text="❌ Ошибка: номер телефона не найден. Начинаем регистрацию заново.")
        await start_registration_process(event.bot, chat_id)
        return

    await start_fio_request(event.bot, chat_id, user_data)


async def handle_data_correction(event, chat_id_str, chat_id, data_type):
    """Обработка исправления данных"""
    current_data = user_states.get(chat_id_str, {}).get('data', {})
    current_data.pop(data_type, None)
    await request_data_correction(event.bot, chat_id, current_data, data_type)


async def handle_data_confirmation(event, chat_id_str, chat_id):
    """Обработка подтверждения данных"""
    log_user_event(chat_id_str, "user confirmed the registration")
    user_data = user_states.get(chat_id_str, {}).get('data', {})

    if user_data and all(key in user_data for key in ['fio', 'birth_date', 'phone']):
        await complete_registration(event.bot, chat_id, user_data)
    else:
        missing_fields = [key for key in ['fio', 'birth_date', 'phone'] if key not in user_data]
        log_data_event(chat_id_str, "incomplete_data_on_confirmation", missing=missing_fields)
        await event.bot.send_message(chat_id=chat_id, text="❌ Не все данные заполнены. Начинаем регистрацию заново.")
        await start_registration_process(event.bot, chat_id)


@dp.message_created()
@anti_duplicate()
async def handle_message(event: MessageCreated):
    """Обработка всех текстовых сообщений"""
    chat_id = event.message.recipient.chat_id
    chat_id_str = str(chat_id)

    # Проверяем базовые условия
    if not event.message.body or not event.message.body.text:
        if event.message.body and event.message.body.attachments:
            await handle_contact_message(event)
        return

    if not event.message.sender:
        return

    message_text = event.message.body.text.strip()
    if not message_text:
        return

    log_user_event(chat_id_str, "message_sent", text=message_text)

    # Если пользователь не зарегистрирован и не в процессе регистрации, игнорируем
    if not db.is_user_registered(chat_id_str) and chat_id_str not in user_states:
        log_user_event(chat_id_str, "message_ignored_unregistered")
        return

    state_info = user_states.get(chat_id_str)
    if not state_info:
        if db.is_user_registered(chat_id_str):
            greeting_name = db.get_user_greeting(chat_id_str)
            await event.bot.send_message(chat_id=chat_id, text="✅ Вы уже в системе.")
            await send_main_menu(event.bot, chat_id, greeting_name)
        return

    state = state_info.get('state')
    user_data = state_info.get('data', {})

    # Обработка разных состояний
    state_handlers = {
        'waiting_fio': lambda: validate_and_process_input(
            chat_id_str, message_text, 'fio', event.bot, chat_id, user_data, request_birth_date
        ),
        'waiting_birth_date': lambda: validate_and_process_input(
            chat_id_str, message_text, 'birth_date', event.bot, chat_id, user_data,
            lambda bot, cid, data: user_states.update(
                {chat_id_str: {'state': 'waiting_confirmation', 'data': data}}) or send_confirmation_message(bot, cid,
                                                                                                             data)
        ),
        'waiting_fio_correction': lambda: validate_and_process_input(
            chat_id_str, message_text, 'fio', event.bot, chat_id, user_data,
            lambda bot, cid, data: user_states.update(
                {chat_id_str: {'state': 'waiting_confirmation', 'data': data}}) or send_confirmation_message(bot, cid,
                                                                                                             data)
        ),
        'waiting_birth_date_correction': lambda: validate_and_process_input(
            chat_id_str, message_text, 'birth_date', event.bot, chat_id, user_data,
            lambda bot, cid, data: user_states.update(
                {chat_id_str: {'state': 'waiting_confirmation', 'data': data}}) or send_confirmation_message(bot, cid,
                                                                                                             data)
        )
    }

    if state in state_handlers:
        result = state_handlers[state]()
        if asyncio.iscoroutine(result):
            await result


async def handle_contact_message(event: MessageCreated):
    """Обработка сообщений с контактами"""
    chat_id = event.message.recipient.chat_id
    chat_id_str = str(chat_id)

    state_info = user_states.get(chat_id_str)
    if not state_info or state_info.get('state') != 'waiting_phone_confirmation':
        return

    contact_attachments = [attr for attr in event.message.body.attachments if attr.type == "contact"]
    if not contact_attachments:
        return

    for contact in contact_attachments:
        try:
            payload = contact.payload
            vcf_info = payload.vcf_info
            phone_match = re.search(r'TEL[^:]*:([^\r\n]+)', vcf_info)

            if phone_match:
                phone = phone_match.group(1).strip()
                clean_phone = re.sub(r'[^\d+]', '', phone)
                if not clean_phone.startswith('+'):
                    clean_phone = '+' + clean_phone

                if not db.validate_phone(clean_phone):
                    log_user_event(chat_id_str, "invalid_phone_format", phone=clean_phone)
                    await event.bot.send_message(chat_id=chat_id, text="❌ Неверный формат номера телефона.")
                    return

                user_data = state_info.get('data', {})
                user_data['phone'] = clean_phone
                user_states[chat_id_str] = {'state': 'waiting_phone_confirmation', 'data': user_data}

                log_data_event(chat_id_str, "phone_extracted", phone=clean_phone)
                await send_phone_confirmation(event.bot, chat_id, clean_phone)

            else:
                log_user_event(chat_id_str, "phone_extraction_failed")
                await event.bot.send_message(chat_id=chat_id, text="❌ Не удалось определить номер телефона.")

        except Exception as e:
            log_system_event("contact_handler", "processing_failed", error=str(e), chat_id=chat_id_str)
            await event.bot.send_message(chat_id=chat_id, text="❌ Произошла ошибка при обработке контакта.")


# --- ЗАПУСК ВЕБХУКА ---
async def main():
    log_system_event("bot", "starting")
    await setup_webhook()
    log_system_event("bot", "webhook_server_starting")

    await dp.handle_webhook(
        bot=bot,
        host='0.0.0.0',
        port=80,
        log_level='info'
    )


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        log_system_event("bot", "stopped_manually")
    except Exception as e:
        log_system_event("bot", "crashed", error=str(e))
        raise
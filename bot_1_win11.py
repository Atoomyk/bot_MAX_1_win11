import asyncio
import logging
import os
import time
import re
import aiohttp
import json
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


async def get_webhook_subscriptions(silent=False):
    """Получить список всех вебхук-подписок"""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                    f"{MAX_API_BASE_URL}/subscriptions",
                    headers=HEADERS
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    subscriptions = data.get('subscriptions', [])

                    # ВЫВОД В КОНСОЛЬ ТОЛЬКО ЕСЛИ НЕ SILENT MODE
                    if not silent:
                        print(f"\n=== ТЕКУЩИЕ ВЕБХУКИ ===")
                        print(f"Найдено подписок: {len(subscriptions)}")

                        for i, sub in enumerate(subscriptions, 1):
                            print(f"{i}. URL: {sub.get('url', 'N/A')}")
                            print(f"   Время: {sub.get('time', 'N/A')}")
                            print(f"   Типы: {', '.join(sub.get('update_types', []))}")
                            print()

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

    # Получаем и выводим текущие вебхуки (ПЕРВЫЙ РАЗ - ПОКАЗЫВАЕМ)
    current_subscriptions = await get_webhook_subscriptions(silent=False)

    # Настраиваем новый вебхук
    print(f"🔄 Устанавливаю новый вебхук: {X_TUNNEL_URL}")
    await bot.subscribe_webhook(
        url=X_TUNNEL_URL,
        update_types=[
            "message_created",
            "message_callback",
            "bot_started"
        ]
    )

    # Проверяем результат (ВТОРОЙ РАЗ - НЕ ПОКАЗЫВАЕМ)
    final_subscriptions = await get_webhook_subscriptions(silent=True)
    if final_subscriptions:
        print("✅ Вебхук успешно настроен!")
    else:
        print("❌ Ошибка настройки вебхука")


SOGL_LINK = "https://sevmiac.ru/upload/iblock/d73/sttjnvlhg3j2df943ve0fv3husrlm8oj.pdf"
CONTINUE_CALLBACK = "start_continue"
AGREEMENT_CALLBACK = "agreement_accepted"
ADMIN_CONTACT = "@admin_MIAC"

# Новые callback-ы для системы исправления данных
CORRECT_FIO_CALLBACK = "correct_fio"
CORRECT_BIRTH_DATE_CALLBACK = "correct_birth_date"
CORRECT_PHONE_CALLBACK = "correct_phone"
CONFIRM_DATA_CALLBACK = "confirm_data"

# Callback-ы для проверки телефона
CONFIRM_PHONE_CALLBACK = "confirm_phone"
REJECT_PHONE_CALLBACK = "reject_phone"

# Ссылки для кнопок главного меню
GOSUSLUGI_APPOINTMENT_URL = "https://www.gosuslugi.ru/10700"
GOSUSLUGI_MEDICAL_EXAM_URL = "https://www.gosuslugi.ru/647521/1/form"
GOSUSLUGI_DOCTOR_HOME_URL = "https://www.gosuslugi.ru/600361"
GOSUSLUGI_ATTACH_TO_POLYCLINIC_URL = "https://www.gosuslugi.ru/600360"
CONTACT_CENTER_URL = "https://sevmiac.ru/ekc/"
MAP_OF_MEDICAL_INSTITUTIONS_URL = "https://yandex.ru/maps/959/sevastopol/search/%D0%B1%D0%BE%D0%BB%D1%8C%D0%BD%D0%B8%D1%86%D1%8B%20%D1%81%D0%B5%D0%B2%D0%B0%D1%81%D1%82%D0%BE%D0%BF%D0%BE%D0%BB%D1%8C/?ll=33.542596%2C44.577279&profile-mode=1&sctx=ZAAAAAgCEAAaKAoSCc0iFFtBJUNAEfYM4ZhlAUtAEhIJPgXAeAYN1z8RHCjwTj49wj8iBgABAgQFBigEOABAvwdIAWIaYWRkX3NuaXBwZXQ9bWV0YXJlYWx0eS8xLnhiHGFkZF9zbmlwcGV0=PW1haW5fYXNwZWN0cy8xLnhiKXJlYXJyPXNjaGVtZV9Mb2NhbC9HZW8vTWV0YVJlYWx0eUtwcz0xMDAyagJydZUBAAAAAJ0BzczMPaABAagBAL0B09dLsMIBhwGI0oWYBI%2BevdYEmM%2BXmoAChf6Czky%2F3bm7BMGrr6oE1Oz6ngT91qOQtQK8ib%2FOiAXoteKRBMXVwJYEgcLQhgaczPbLBriO%2FskE1uOJgtoFkJjwtQaD48Tekgeq8ezXBq%2FLm%2BDCBMfokZuaA8nSo%2FkEiuHzlv8GktWn1IYB7bCdwuQF04y6xTmCAifQsdC%2B0LvRjNC90LjRhtGLINGB0LXQstCw0YHRgtC%2B0L%2FQvtC70YyKAiwxODQxMDU5NTYkMTg0MTA1OTU4JDUzNDM3MjYwNTU5JDE5ODM5NTI4OTU0MpICAzk1OZoCDGRlc2t0b3AtbWFwc6oCDDE2NTc0MjkxODkzOQ%3D%3D&sll=33.542596%2C44.577279&source=wizbiz_new_map_multi&sspn=0.240326%2C0.097050&z=13"

# Импорт базы данных из отдельного файла
from user_database import db

# Словари для хранения состояний и защиты от дублирования
user_states = {}
processed_messages = set()
processed_callbacks = set()
last_processed = {}


# --- Вспомогательные функции ---
def create_main_menu_keyboard():
    """Создает клавиатуру главного меню с 4 кнопками"""
    buttons = [
        [LinkButton(text="Записаться на приём к врачу", url=GOSUSLUGI_APPOINTMENT_URL)],
        [LinkButton(text="Профосмотр/диспансеризация", url=GOSUSLUGI_MEDICAL_EXAM_URL)],
        [LinkButton(text="Вызов врача на дом", url=GOSUSLUGI_DOCTOR_HOME_URL)],
        [LinkButton(text="Прикрепление к поликлинике", url=GOSUSLUGI_ATTACH_TO_POLYCLINIC_URL)],
        [LinkButton(text="Ближайшие гос мед учреждения", url=MAP_OF_MEDICAL_INSTITUTIONS_URL)],
        [LinkButton(text="Единый контакт-центр", url=CONTACT_CENTER_URL)]
    ]

    buttons_payload = ButtonsPayload(buttons=buttons)
    keyboard_attachment = Attachment(
        type=AttachmentType.INLINE_KEYBOARD,
        payload=buttons_payload
    )

    return keyboard_attachment


async def send_main_menu(bot_instance: Bot, chat_id: int, greeting_name: str):
    """Отправляет главное меню с приветствием"""
    keyboard = create_main_menu_keyboard()

    await bot_instance.send_message(
        chat_id=chat_id,
        text=f"Здравствуйте, {greeting_name}!\n\n"
             "Выберите услугу:",
        attachments=[keyboard]
    )


async def send_agreement_message(bot_instance: Bot, chat_id: int):
    """Отправляет сообщение с соглашением"""
    agreement_button = CallbackButton(
        text="Согласие на обработку персональных данных",
        payload=AGREEMENT_CALLBACK
    )

    buttons_payload = ButtonsPayload(buttons=[[agreement_button]])
    keyboard_attachment = Attachment(
        type=AttachmentType.INLINE_KEYBOARD,
        payload=buttons_payload
    )

    await bot_instance.send_message(
        chat_id=chat_id,
        text='Продолжая, Вы даёте согласие на обработку персональных данных.\n'
             f'Ознакомиться с документом вы можете по ссылке {SOGL_LINK}',
        attachments=[keyboard_attachment]
    )


async def start_registration_process(bot_instance: Bot, chat_id: int):
    """Начинает процесс регистрации - подтверждение телефона"""
    user_states[str(chat_id)] = {'state': 'waiting_phone_confirmation', 'data': {}}

    # Логирование начала регистрации
    log_user_event(str(chat_id), "registration_started")

    # Сообщение о необходимости подтвердить номер
    await bot_instance.send_message(
        chat_id=chat_id,
        text='Для начала работы необходимо подтвердить номер и пройти регистрацию.'
    )

    # Запрос контакта
    await request_contact(bot_instance, chat_id)


async def request_contact(bot_instance: Bot, chat_id: int):
    """Запрашивает контакт пользователя"""
    contact_button = RequestContactButton(text="📇 Отправить контакт")
    buttons_payload = ButtonsPayload(buttons=[[contact_button]])
    keyboard_attachment = Attachment(
        type=AttachmentType.INLINE_KEYBOARD,
        payload=buttons_payload
    )

    await bot_instance.send_message(
        chat_id=chat_id,
        text="Нажмите кнопку ниже чтобы поделиться контактом:",
        attachments=[keyboard_attachment]
    )


async def send_phone_confirmation(bot_instance: Bot, chat_id: int, phone: str):
    """Отправляет сообщение с подтверждением номера телефона"""
    confirm_button = CallbackButton(
        text="✅ Да, номер верный",
        payload=CONFIRM_PHONE_CALLBACK
    )
    reject_button = CallbackButton(
        text="❌ Нет, неверный номер",
        payload=REJECT_PHONE_CALLBACK
    )

    buttons_payload = ButtonsPayload(buttons=[[confirm_button, reject_button]])
    keyboard_attachment = Attachment(
        type=AttachmentType.INLINE_KEYBOARD,
        payload=buttons_payload
    )

    await bot_instance.send_message(
        chat_id=chat_id,
        text=f"📞 Ваш номер телефона определён:\n\n"
             f"📱 {phone}\n\n"
             f"Пожалуйста, проверьте актуальность номера:",
        attachments=[keyboard_attachment]
    )


async def handle_incorrect_phone(bot_instance: Bot, chat_id: int):
    """Обработка неверного номера телефона - запрашиваем контакт заново"""
    log_user_event(str(chat_id), "phone_rejected")

    await bot_instance.send_message(
        chat_id=chat_id,
        text="❌ Пожалуйста, отправьте контакт с правильным номером телефона."
    )

    # Запрашиваем контакт снова
    await request_contact(bot_instance, chat_id)


async def start_fio_request(bot_instance: Bot, chat_id: int, user_data: dict):
    """Начинает процесс ввода ФИО"""
    user_states[str(chat_id)] = {'state': 'waiting_fio', 'data': user_data}

    # Логирование начала ввода ФИО
    log_user_event(str(chat_id), "fio_input_started")

    await bot_instance.send_message(
        chat_id=chat_id,
        text='Пожалуйста, введите ваше ФИО в формате:\n'
             'Фамилия Имя Отчество\n\n'
             'Пример: Иванов Иван Иванович'
    )


async def request_fio_correction(bot_instance: Bot, chat_id: int, user_data: dict):
    """Запрашивает ФИО для исправления и возвращает к подтверждению"""
    log_user_event(str(chat_id), "fio_correction_requested")
    # Сохраняем текущие данные (особенно телефон)
    user_states[str(chat_id)] = {'state': 'waiting_fio_correction', 'data': user_data}

    await bot_instance.send_message(
        chat_id=chat_id,
        text="Введите ваше ФИО для исправления:\n\n"
             "Формат: Фамилия Имя Отчество\n"
             "Пример: Иванов Иван Иванович"
    )


async def request_birth_date_correction(bot_instance: Bot, chat_id: int, user_data: dict):
    """Запрашивает дату рождения для исправления и возвращает к подтверждению"""
    log_user_event(str(chat_id), "birth_date_correction_requested")
    # Сохраняем текущие данные (особенно телефон)
    user_states[str(chat_id)] = {'state': 'waiting_birth_date_correction', 'data': user_data}

    await bot_instance.send_message(
        chat_id=chat_id,
        text="Введите вашу дату рождения для исправления:\n\n"
             "Формат: ДД.ММ.ГГГГ\n"
             "Пример: 13.03.2003"
    )


async def request_birth_date(bot_instance: Bot, chat_id: int, user_data: dict):
    """Запрашивает дату рождения"""
    # Сохраняем текущие данные перед переходом к следующему шагу
    user_states[str(chat_id)] = {'state': 'waiting_birth_date', 'data': user_data}

    await bot_instance.send_message(
        chat_id=chat_id,
        text="Отлично!\n"
             "Теперь введите вашу дату рождения\n\n"
             "Формат: ДД.ММ.ГГГГ\n"
             "Пример: 13.03.2003"
    )


async def send_confirmation_message(bot_instance: Bot, chat_id: int, user_data: dict):
    """Отправляет сообщение с подтверждением данных (с телефоном, но без кнопки исправления телефона)"""
    fio = user_data.get('fio', 'Не указано')
    birth_date = user_data.get('birth_date', 'Не указано')
    phone = user_data.get('phone', 'Не указано')

    # Логирование данных для подтверждения
    log_data_event(str(chat_id), "confirmation_prepared", fio=fio, birth_date=birth_date, phone=phone)

    # Создаем кнопки для исправления (без кнопки телефона)
    correct_fio_button = CallbackButton(
        text="⚠️ Исправить ФИО",
        payload=CORRECT_FIO_CALLBACK
    )
    correct_birth_date_button = CallbackButton(
        text="⚠️ Исправить дату рождения",
        payload=CORRECT_BIRTH_DATE_CALLBACK
    )
    confirm_button = CallbackButton(
        text="✅ Всё верно, подтвердить",
        payload=CONFIRM_DATA_CALLBACK
    )

    buttons_payload = ButtonsPayload(buttons=[
        [correct_fio_button],
        [correct_birth_date_button],
        [confirm_button]
    ])
    keyboard_attachment = Attachment(
        type=AttachmentType.INLINE_KEYBOARD,
        payload=buttons_payload
    )

    await bot_instance.send_message(
        chat_id=chat_id,
        text="📋 Пожалуйста, проверьте введенные данные:\n\n"
             f"👤 ФИО: {fio}\n"
             f"🎂 Дата рождения: {birth_date}\n"
             f"📞 Телефон: {phone}\n\n"
             "Если всё верно - нажмите 'Подтвердить', "
             "или выберите что нужно исправить:",
        attachments=[keyboard_attachment]
    )


async def complete_registration(bot_instance: Bot, chat_id: int, user_data: dict):
    """Завершает регистрацию и показывает главное меню"""
    fio = user_data['fio']
    birth_date = user_data['birth_date']
    phone = user_data['phone']

    success = db.register_user(str(chat_id), fio, phone, birth_date)

    if success:
        # Удаляем состояние перед отправкой сообщения
        user_states.pop(str(chat_id), None)

        # Получаем приветствие по имени и отчеству
        greeting_name = db.get_user_greeting(str(chat_id))

        # Логирование успешной регистрации
        log_data_event(str(chat_id), "registration_completed", fio=fio, phone=phone, status="success")

        # Отправляем сообщение об успешной регистрации
        await bot_instance.send_message(
            chat_id=chat_id,
            text=f"✅ Успешная регистрация!\n"
                 f"Теперь вы можете пользоваться всеми функциями бота."
        )

        # Отправляем главное меню
        await send_main_menu(bot_instance, chat_id, greeting_name)

    else:
        # Ошибка при сохранении
        user_states.pop(str(chat_id), None)
        log_data_event(str(chat_id), "registration_failed", fio=fio, phone=phone, status="duplicate")
        await bot_instance.send_message(
            chat_id=chat_id,
            text=f"🚨 Ошибка при регистрации. Комбинация ФИО и телефона уже существует.\n\n"
                 f"Пожалуйста, обратитесь к администратору, {ADMIN_CONTACT}."
        )


# --- Обработчики событий ---

@dp.bot_started()
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
            continue_button = CallbackButton(
                text="Продолжить",
                payload=CONTINUE_CALLBACK
            )
            buttons_payload = ButtonsPayload(buttons=[[continue_button]])
            keyboard_attachment = Attachment(
                type=AttachmentType.INLINE_KEYBOARD,
                payload=buttons_payload
            )
            await event.bot.send_message(
                chat_id=chat_id,
                text='Здравствуйте! 👩‍⚕️\n\n'
                     'Вы обратились в Медицинский информационно-аналитический центр города Севастополя.\n'
                     'Наша система позволяет Вам удобно и быстро решить следующие задачи:\n\n'
                     '📌 Записаться на приём к врачу;\n'
                     '📌 Вызвать врача на дом;\n'
                     '📌 Записаться на профилактический медосмотр/диспансеризацию;\n'
                     '📌 Прикрепиться к поликлинике;\n'
                     '📌 Получать уведомления о записи к врачу с возможностью её отмены;\n'
                     '📌 Найти ближайшие государственные медицинские учреждения.',
                attachments=[keyboard_attachment]
            )
    except Exception as e:
        log_system_event("bot_started", "message_send_failed", error=str(e), chat_id=chat_id_str)


@dp.message_callback()
async def message_callback(event: MessageCallback):
    """Обработка нажатий на инлайн-кнопки"""
    chat_id = event.message.recipient.chat_id
    chat_id_str = str(chat_id)

    # Защита от дублирования
    current_time = time.time()
    if chat_id_str in last_processed:
        if current_time - last_processed[chat_id_str] < 1.0:
            return
    last_processed[chat_id_str] = current_time

    callback_id = event.callback.callback_id if hasattr(event.callback, 'callback_id') else None
    if callback_id and callback_id in processed_callbacks:
        return
    if callback_id:
        processed_callbacks.add(callback_id)
        if len(processed_callbacks) > 1000:
            processed_callbacks.clear()

    payload = event.callback.payload

    # Логирование callback события
    log_user_event(chat_id_str, "button_pressed", payload=payload)

    if payload == CONTINUE_CALLBACK:
        log_system_event("callback_handler", "continue_processed", chat_id=chat_id_str)
        await send_agreement_message(event.bot, chat_id)

    elif payload == AGREEMENT_CALLBACK:
        log_security_event(chat_id_str, "consent_accepted")
        await start_registration_process(event.bot, chat_id)

    # Обработка подтверждения телефона
    elif payload == CONFIRM_PHONE_CALLBACK:
        log_user_event(chat_id_str, "phone_confirmed")
        # Получаем текущие данные с телефоном
        current_state = user_states.get(chat_id_str, {})
        user_data = current_state.get('data', {})

        # ВАЖНО: Проверяем, что телефон действительно есть в данных
        if 'phone' not in user_data:
            log_data_event(chat_id_str, "phone_missing_on_confirmation")
            await event.bot.send_message(
                chat_id=chat_id,
                text="❌ Ошибка: номер телефона не найден. Начинаем регистрацию заново."
            )
            await start_registration_process(event.bot, chat_id)
            return

        await start_fio_request(event.bot, chat_id, user_data)

    # Обработка отклонения телефона
    elif payload == REJECT_PHONE_CALLBACK:
        log_user_event(chat_id_str, "phone_rejected")
        await handle_incorrect_phone(event.bot, chat_id)

    # Обработка кнопок исправления данных
    elif payload == CORRECT_FIO_CALLBACK:
        # Сохраняем уже введенные данные кроме ФИО
        current_data = user_states.get(chat_id_str, {}).get('data', {})
        current_data.pop('fio', None)  # Удаляем старое ФИО
        log_user_event(chat_id_str, "fio_correction_requested")
        await request_fio_correction(event.bot, chat_id, current_data)

    elif payload == CORRECT_BIRTH_DATE_CALLBACK:
        # Сохраняем уже введенные данные кроме даты рождения
        current_data = user_states.get(chat_id_str, {}).get('data', {})
        current_data.pop('birth_date', None)  # Удаляем старую дату
        log_user_event(chat_id_str, "birth_date_correction_requested")
        await request_birth_date_correction(event.bot, chat_id, current_data)

    elif payload == CONFIRM_DATA_CALLBACK:
        log_user_event(chat_id_str, "user confirmed the registration")
        # Завершаем регистрацию
        user_data = user_states.get(chat_id_str, {}).get('data', {})

        if user_data and all(key in user_data for key in ['fio', 'birth_date', 'phone']):
            await complete_registration(event.bot, chat_id, user_data)
        else:
            # Если данных недостаточно, начинаем заново
            missing_fields = [key for key in ['fio', 'birth_date', 'phone'] if key not in user_data]
            log_data_event(chat_id_str, "incomplete_data_on_confirmation", missing=missing_fields)
            await event.bot.send_message(
                chat_id=chat_id,
                text="❌ Не все данные заполнены. Начинаем регистрацию заново."
            )
            await start_registration_process(event.bot, chat_id)


@dp.message_created()
async def handle_message(event: MessageCreated):
    """Обработка всех текстовых сообщений"""
    chat_id = event.message.recipient.chat_id
    chat_id_str = str(chat_id)

    # Проверяем базовые условия
    if not event.message.body or not event.message.body.text:
        # Проверяем наличие контактов
        if event.message.body and event.message.body.attachments:
            await handle_contact_message(event)
        return

    if not event.message.sender:
        return

    # Защита от дублирования
    message_id = event.message.body.mid if hasattr(event.message.body, 'mid') else None
    if message_id and message_id in processed_messages:
        return
    if message_id:
        processed_messages.add(message_id)
        if len(processed_messages) > 100:
            processed_messages.clear()

    message_text = event.message.body.text.strip()

    if not message_text:
        return

    # Логирование ВСЕХ сообщений от пользователя
    log_user_event(chat_id_str, "message_sent", text=message_text)

    # Если пользователь не зарегистрирован и не в процессе регистрации, игнорируем
    if not db.is_user_registered(chat_id_str) and chat_id_str not in user_states:
        log_user_event(chat_id_str, "message_ignored_unregistered")
        return

    # Проверяем состояние пользователя (процесс регистрации)
    state_info = user_states.get(chat_id_str)

    if not state_info:
        # Пользователь зарегистрирован, но не в процессе регистрации
        if db.is_user_registered(chat_id_str):
            greeting_name = db.get_user_greeting(chat_id_str)
            await event.bot.send_message(
                chat_id=chat_id,
                text="✅ Вы уже в системе."
            )
            await send_main_menu(event.bot, chat_id, greeting_name)
        return

    state = state_info.get('state')
    user_data = state_info.get('data', {})

    # --- Ожидание ФИО ---
    if state == 'waiting_fio':

        if not db.validate_fio(message_text):
            log_user_event(chat_id_str, "invalid_fio_format", input=message_text)
            await event.message.answer(
                "❌ Ошибка формата!\n\n"
                "Пожалуйста, введите ваше ФИО в таком формате: Фамилия Имя Отчество\n\n"
                "Пример: Иванов Иван Иванович"
            )
            return

        # Сохраняем ФИО
        user_data['fio'] = message_text
        log_data_event(chat_id_str, "fio_entered", fio=message_text)

        # Переходим к вводу даты рождения
        await request_birth_date(event.bot, chat_id, user_data)

    # --- Ожидание даты рождения ---
    elif state == 'waiting_birth_date':

        if not db.validate_birth_date(message_text):
            log_user_event(chat_id_str, "invalid_birth_date_format", input=message_text)
            await event.message.answer(
                "❌ Ошибка формата!\n\n"
                "Пожалуйста, введите дату рождения в формате: ДД.ММ.ГГГГ\n\n"
                "Пример: 13.03.2003"
            )
            return

        # Сохраняем дату рождения
        user_data['birth_date'] = message_text
        log_data_event(chat_id_str, "birth_date_entered", birth_date=message_text)

        # Все данные собраны - переходим к подтверждению
        user_states[chat_id_str] = {
            'state': 'waiting_confirmation',
            'data': user_data
        }
        await send_confirmation_message(event.bot, chat_id, user_data)

    # --- Исправление ФИО ---
    elif state == 'waiting_fio_correction':

        if not db.validate_fio(message_text):
            log_user_event(chat_id_str, "invalid_fio_format_correction", input=message_text)
            await event.message.answer(
                "❌ Ошибка формата!\n\n"
                "Пожалуйста, введите ваше ФИО в таком формате: Фамилия Имя Отчество\n\n"
                "Пример: Иванов Иван Иванович"
            )
            return

        # Сохраняем исправленное ФИО
        user_data['fio'] = message_text
        log_data_event(chat_id_str, "fio_corrected", fio=message_text)

        # Возвращаем к подтверждению данных
        user_states[chat_id_str] = {
            'state': 'waiting_confirmation',
            'data': user_data
        }
        await send_confirmation_message(event.bot, chat_id, user_data)

    # --- Исправление даты рождения ---
    elif state == 'waiting_birth_date_correction':

        if not db.validate_birth_date(message_text):
            log_user_event(chat_id_str, "invalid_birth_date_format_correction", input=message_text)
            await event.message.answer(
                "❌ Ошибка формата!\n\n"
                "Пожалуйста, введите дату рождения в формате: ДД.ММ.ГГГГ\n\n"
                "Пример: 13.03.2003"
            )
            return

        # Сохраняем исправленную дату рождения
        user_data['birth_date'] = message_text
        log_data_event(chat_id_str, "birth_date_corrected", birth_date=message_text)

        # Возвращаем к подтверждению данных
        user_states[chat_id_str] = {
            'state': 'waiting_confirmation',
            'data': user_data
        }
        await send_confirmation_message(event.bot, chat_id, user_data)


async def handle_contact_message(event: MessageCreated):
    """Обработка сообщений с контактами"""
    chat_id = event.message.recipient.chat_id
    chat_id_str = str(chat_id)

    # Проверяем состояние пользователя
    state_info = user_states.get(chat_id_str)
    if not state_info or state_info.get('state') != 'waiting_phone_confirmation':
        return

    # Ищем контакты
    contact_attachments = [attr for attr in event.message.body.attachments if attr.type == "contact"]

    if not contact_attachments:
        return

    for contact in contact_attachments:
        try:
            payload = contact.payload
            vcf_info = payload.vcf_info

            # Ищем телефон в VCF
            phone_match = re.search(r'TEL[^:]*:([^\r\n]+)', vcf_info)
            if phone_match:
                phone = phone_match.group(1).strip()
                # Очищаем номер и добавляем +
                clean_phone = re.sub(r'[^\d+]', '', phone)
                if not clean_phone.startswith('+'):
                    clean_phone = '+' + clean_phone

                # Валидация телефона
                if not db.validate_phone(clean_phone):
                    log_user_event(chat_id_str, "invalid_phone_format", phone=clean_phone)
                    await event.bot.send_message(
                        chat_id=chat_id,
                        text="❌ Неверный формат номера телефона."
                    )
                    return
            else:
                log_user_event(chat_id_str, "phone_extraction_failed")
                await event.bot.send_message(
                    chat_id=chat_id,
                    text="❌ Не удалось определить номер телефона."
                )
                return

            # Сохраняем телефон в данных пользователя
            user_data = state_info.get('data', {})
            user_data['phone'] = clean_phone
            # Обновляем состояние с сохраненным телефоном
            user_states[chat_id_str] = {'state': 'waiting_phone_confirmation', 'data': user_data}

            log_data_event(chat_id_str, "phone_extracted", phone=clean_phone)

            # Отправляем подтверждение номера
            await send_phone_confirmation(event.bot, chat_id, clean_phone)

        except Exception as e:
            log_system_event("contact_handler", "processing_failed", error=str(e), chat_id=chat_id_str)
            await event.bot.send_message(
                chat_id=chat_id,
                text="❌ Произошла ошибка при обработке контакта."
            )


# --- Запуск вебхука ---

async def main():
    # Логирование запуска бота
    log_system_event("bot", "starting")

    # Настраиваем вебхук
    await setup_webhook()

    # Затем запускаем сервер
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
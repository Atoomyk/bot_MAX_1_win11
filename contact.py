import asyncio
import logging
import os
import re
from dotenv import load_dotenv

from maxapi import Bot, Dispatcher
from maxapi.types import (
    MessageCreated,
    RequestContactButton,
    ButtonsPayload,
    Attachment,
    BotStarted
)
from maxapi.utils.inline_keyboard import AttachmentType

# Загрузка токена из .env
load_dotenv()
TOKEN = os.getenv("MAXAPI_TOKEN")

bot = Bot(TOKEN)
dp = Dispatcher()

logging.basicConfig(level=logging.INFO)


# --- Обработка запуска бота ---
@dp.bot_started()
async def handle_bot_started(event: BotStarted):
    contact_button = RequestContactButton(text="📇 Отправить контакт")
    buttons_payload = ButtonsPayload(buttons=[[contact_button]])
    keyboard_attachment = Attachment(
        type=AttachmentType.INLINE_KEYBOARD,
        payload=buttons_payload
    )

    await bot.send_message(
        chat_id=event.chat_id,
        text="Добро пожаловать! Нажмите кнопку ниже чтобы поделиться контактом:",
        attachments=[keyboard_attachment]
    )


# --- Обработка контактов ---
@dp.message_created()
async def handle_contacts(event: MessageCreated):
    if not event.message.body or not event.message.body.attachments:
        return

    user_id = event.message.sender.user_id
    chat_id = event.message.recipient.chat_id

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

                # Сразу отправляем подтверждение
                await bot.send_message(
                    chat_id=chat_id,
                    text=f"✅ **Отлично! Номер подтвержден!**\n\n"
                         f"📱 **Ваш номер:** `{clean_phone}`\n\n"
                         f"Спасибо! Теперь мы можем продолжить работу."
                )

            else:
                await bot.send_message(
                    chat_id=chat_id,
                    text="❌ Не удалось определить номер телефона. Пожалуйста, попробуйте еще раз."
                )

        except Exception as e:
            await bot.send_message(
                chat_id=chat_id,
                text="❌ Произошла ошибка при обработке контакта. Пожалуйста, попробуйте еще раз."
            )


# --- Настройка вебхука ---
async def setup_webhook():
    X_TUNNEL_URL = "https://2cbadd3b-c52f-47f3-83e3-a4ae9371cf96.tunnel4.com"
    await bot.subscribe_webhook(
        url=X_TUNNEL_URL,
        update_types=["message_created", "bot_started"]
    )


# --- Запуск сервера ---
async def main():
    await setup_webhook()
    await dp.handle_webhook(bot=bot, host="0.0.0.0", port=80, log_level="info")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("Bot stopped manually.")
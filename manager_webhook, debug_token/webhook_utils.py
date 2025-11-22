#!/usr/bin/env python3
"""
Утилита для ручного управления вебхуками
"""

import asyncio
import os
import sys
from dotenv import load_dotenv
from webhook_manager import cleanup_webhooks, setup_webhook, get_current_webhooks, test_api_connection

load_dotenv()


async def check_token():
    """Проверить наличие токена"""
    token = os.getenv("MAXAPI_TOKEN")
    if not token:
        print("❌ ОШИБКА: Токен не найден в .env файле")
        print("💡 Убедитесь, что в файле .env есть строка: MAXAPI_TOKEN=ваш_токен")
        return False

    print(f"✅ Токен найден: {token[:10]}...")
    return True


async def main():
    print("🔧 Утилита управления вебхуками Max Bot API")
    print("=" * 50)

    # Проверяем токен
    if not await check_token():
        sys.exit(1)

    # Тестируем подключение
    print("\n🔄 Тестируем подключение к API...")
    connection_ok = await test_api_connection(os.getenv("MAXAPI_TOKEN"))

    if not connection_ok:
        print("❌ Не удалось подключиться к API. Проверьте токен.")
        return

    print("✅ Подключение к API успешно!")

    while True:
        print("\nВыберите действие:")
        print("1. Показать текущие вебхуки")
        print("2. Очистить все вебхуки")
        print("3. Настроить новый вебхук")
        print("4. Проверить подключение")
        print("5. Выйти")

        choice = input("\nВаш выбор (1-5): ").strip()

        if choice == "1":
            print("\n🔄 Получаю список вебхуков...")
            webhooks = await get_current_webhooks(os.getenv("MAXAPI_TOKEN"))
            if webhooks:
                print(f"✅ Найдено вебхуков: {len(webhooks)}")
                for i, webhook in enumerate(webhooks, 1):
                    print(f"\n{i}. URL: {webhook.get('url')}")
                    print(f"   Время: {webhook.get('time')}")
                    print(f"   Типы событий: {', '.join(webhook.get('update_types', []))}")
            else:
                print("ℹ️ Вебхуки не найдены")

        elif choice == "2":
            print("\n🔄 Очищаю вебхуки...")
            success = await cleanup_webhooks(os.getenv("MAXAPI_TOKEN"))
            if success:
                print("✅ Все вебхуки успешно удалены")
            else:
                print("❌ Ошибка при удалении вебхуков")

        elif choice == "3":
            url = input("\nВведите URL нового вебхука: ").strip()
            if url:
                print(f"🔄 Настраиваю вебхук: {url}")
                success = await setup_webhook(os.getenv("MAXAPI_TOKEN"), url)
                if success:
                    print("✅ Новый вебхук успешно настроен")
                else:
                    print("❌ Ошибка при настройке вебхука")
            else:
                print("❌ URL не может быть пустым")

        elif choice == "4":
            print("\n🔄 Проверяем подключение...")
            await test_api_connection(os.getenv("MAXAPI_TOKEN"))

        elif choice == "5":
            print("👋 До свидания!")
            break
        else:
            print("❌ Неверный выбор")


if __name__ == "__main__":
    asyncio.run(main())
#!/usr/bin/env python3
"""
Тест исправленной авторизации
"""

import os
import asyncio
import aiohttp
from dotenv import load_dotenv

load_dotenv()


async def test_fixed_auth():
    """Тест с исправленным форматом авторизации"""
    token = os.getenv("MAXAPI_TOKEN")

    if not token:
        print("❌ Токен не найден")
        return

    print(f"🔍 Тестируем токен: {token[:15]}...")
    print("=" * 60)

    # Правильные заголовки согласно документации
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Authorization": token  # Без "Bearer "!
    }

    print(f"📋 Заголовки: {headers}")

    try:
        async with aiohttp.ClientSession() as session:
            # Тест 1: Получить информацию о боте
            print("\n🧪 Тест 1: GET /me")
            async with session.get(
                    "https://platform-api.max.ru/me",
                    headers=headers
            ) as response:
                print(f"📊 Статус: {response.status}")
                response_text = await response.text()
                print(f"📄 Тело ответа: {response_text}")

            # Тест 2: Получить подписки
            print("\n🧪 Тест 2: GET /subscriptions")
            async with session.get(
                    "https://platform-api.max.ru/subscriptions",
                    headers=headers
            ) as response:
                print(f"📊 Статус: {response.status}")
                response_text = await response.text()
                print(f"📄 Тело ответа: {response_text}")

    except Exception as e:
        print(f"🚫 Ошибка подключения: {e}")


if __name__ == "__main__":
    asyncio.run(test_fixed_auth())
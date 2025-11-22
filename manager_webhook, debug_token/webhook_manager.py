import asyncio
import aiohttp
import logging
from typing import List, Dict, Any

# Настройка логирования для вебхук менеджера
logger = logging.getLogger(__name__)


class WebhookManager:
    """Менеджер для управления вебхук-подписками Max Bot API"""

    def __init__(self, token: str, base_url: str = "https://platform-api.max.ru"):
        self.token = token
        self.base_url = base_url
        # ВАЖНО: Согласно документации, используем просто токен в Authorization, не Bearer
        self.headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Authorization": token  # Без "Bearer "!
        }
        logger.info(f"WebhookManager initialized with token: {token[:10]}...")

    async def _make_request(self, method: str, url: str, json_data: dict = None):
        """Универсальный метод для выполнения запросов"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.request(
                        method=method,
                        url=url,
                        headers=self.headers,
                        json=json_data
                ) as response:

                    logger.debug(f"Request to {url}, Status: {response.status}")

                    if response.status == 200:
                        data = await response.json()
                        return True, data
                    else:
                        error_text = await response.text()
                        logger.error(f"API Error: {response.status} - {error_text}")
                        return False, error_text

        except Exception as e:
            logger.error(f"Request error: {str(e)}")
            return False, str(e)

    async def get_webhook_subscriptions(self) -> List[Dict[str, Any]]:
        """Получить список всех вебхук-подписок"""
        logger.info("Getting webhook subscriptions...")

        success, result = await self._make_request("GET", f"{self.base_url}/subscriptions")

        if success:
            subscriptions = result.get('subscriptions', [])
            logger.info(f"✅ Получено подписок: {len(subscriptions)}")
            return subscriptions
        else:
            logger.error(f"❌ Ошибка получения подписок: {result}")
            return []

    async def delete_webhook_subscription(self, url: str) -> bool:
        """Удалить конкретную вебхук-подписку"""
        logger.info(f"Deleting webhook: {url}")

        success, result = await self._make_request(
            "DELETE",
            f"{self.base_url}/subscriptions",
            {"url": url}
        )

        if success:
            logger.info(f"✅ Удален вебхук: {url}")
            return True
        else:
            logger.error(f"❌ Ошибка удаления {url}: {result}")
            return False

    async def delete_all_webhook_subscriptions(self) -> bool:
        """Удалить все вебхук-подписки"""
        logger.info("🔄 Начинаю очистку вебхуков...")

        subscriptions = await self.get_webhook_subscriptions()

        if not subscriptions:
            logger.info("✅ Нет подписок для удаления")
            return True

        logger.info(f"🔄 Найдено подписок для удаления: {len(subscriptions)}")

        success_count = 0
        for subscription in subscriptions:
            url = subscription.get('url')
            if url:
                success = await self.delete_webhook_subscription(url)
                if success:
                    success_count += 1
                # Небольшая задержка между запросами
                await asyncio.sleep(0.5)

        result = success_count == len(subscriptions)
        if result:
            logger.info(f"✅ Все подписки удалены: {success_count}/{len(subscriptions)}")
        else:
            logger.warning(f"⚠️ Удалены не все подписки: {success_count}/{len(subscriptions)}")

        return result

    async def setup_new_webhook(self, webhook_url: str, update_types: List[str] = None) -> bool:
        """Настроить новый вебхук"""
        if update_types is None:
            update_types = ["message_created", "message_callback", "bot_started"]

        logger.info(f"Setting up new webhook: {webhook_url}")

        success, result = await self._make_request(
            "POST",
            f"{self.base_url}/subscriptions",
            {
                "url": webhook_url,
                "update_types": update_types
            }
        )

        if success:
            logger.info(f"✅ Новый вебхук настроен: {webhook_url}")
            return True
        else:
            logger.error(f"❌ Ошибка настройки вебхука: {result}")
            return False

    async def cleanup_and_setup_webhook(self, webhook_url: str, update_types: List[str] = None) -> bool:
        """Очистить старые вебхуки и настроить новый"""
        # Сначала очищаем старые вебхуки
        cleanup_success = await self.delete_all_webhook_subscriptions()

        if not cleanup_success:
            logger.warning("⚠️ Очистка завершена с ошибками, но продолжаем настройку нового вебхука")

        # Затем настраиваем новый вебхук
        setup_success = await self.setup_new_webhook(webhook_url, update_types)

        return setup_success

    async def test_connection(self) -> bool:
        """Проверить подключение к API (тестовый запрос)"""
        logger.info("Testing API connection...")

        success, result = await self._make_request("GET", f"{self.base_url}/me")

        if success:
            logger.info(f"✅ Подключение успешно: {result}")
            return True
        else:
            logger.error(f"❌ Ошибка подключения: {result}")
            return False


# Функции для удобного использования
async def cleanup_webhooks(token: str) -> bool:
    """Удалить все вебхуки"""
    try:
        # Сначала получаем текущие вебхуки
        webhooks = await get_current_webhooks(token)
        if not webhooks:
            print("ℹ️ Вебхуки не найдены")
            return True

        print(f"🔄 Найдено вебхуков для удаления: {len(webhooks)}")

        headers = {
            "Authorization": f"{token}",
            "Content-Type": "application/json"
        }

        success_count = 0
        for webhook in webhooks:
            webhook_url = webhook.get('url')
            if not webhook_url:
                continue

            try:
                # Кодируем URL для безопасной передачи в query параметре
                import urllib.parse
                encoded_url = urllib.parse.quote(webhook_url, safe='')

                # Формируем URL с параметром url как query parameter
                delete_url = f"https://platform-api.max.ru/subscriptions?url={encoded_url}"

                async with aiohttp.ClientSession() as session:
                    async with session.delete(delete_url, headers=headers) as response:
                        if response.status == 200:
                            print(f"✅ Вебхук удален: {webhook_url}")
                            success_count += 1
                        else:
                            error_text = await response.text()
                            print(f"❌ Ошибка удаления {webhook_url}: {error_text}")

            except Exception as e:
                print(f"❌ Ошибка при удалении {webhook_url}: {str(e)}")

        print(f"✅ Успешно удалено вебхуков: {success_count}/{len(webhooks)}")
        return success_count == len(webhooks)

    except Exception as e:
        print(f"❌ Ошибка при очистке вебхуков: {str(e)}")
        return False


async def setup_webhook(token: str, webhook_url: str, update_types: List[str] = None):
    """Настроить вебхук с предварительной очисткой (удобная функция)"""
    manager = WebhookManager(token)
    return await manager.cleanup_and_setup_webhook(webhook_url, update_types)


async def get_current_webhooks(token: str):
    """Получить текущие вебхуки (удобная функция)"""
    manager = WebhookManager(token)
    return await manager.get_webhook_subscriptions()


async def test_api_connection(token: str):
    """Проверить подключение к API (удобная функция)"""
    manager = WebhookManager(token)
    return await manager.test_connection()
"""
Telegram Collector - Engine 3 (Social Intelligence)
*** REQUIRES BOT TOKEN ***
Create a bot via @BotFather on Telegram to get the token.
The bot must be added to the target group/channel to read messages.

Set TELEGRAM_BOT_TOKEN in .env to enable.

Note: For public channels, some info can be scraped without a bot,
but the Bot API provides more reliable access.
"""

import structlog

from app.core.config import settings
from app.services.collectors.base import BaseCollector

logger = structlog.get_logger()

BASE_URL = "https://api.telegram.org"


class TelegramCollector(BaseCollector):
    """Collect social data from Telegram.

    REQUIRES: TELEGRAM_BOT_TOKEN environment variable.
    Create a bot via @BotFather: https://t.me/BotFather
    """

    source_name = "telegram"
    rate_limit_name = "telegram"

    def _get_bot_url(self) -> str:
        return f"{BASE_URL}/bot{settings.telegram_bot_token}"

    def is_configured(self) -> bool:
        return bool(settings.telegram_bot_token)

    async def get_chat_info(self, chat_id: str) -> dict | None:
        """Get info about a Telegram chat/channel/group."""
        if not self.is_configured():
            logger.warning("telegram.not_configured")
            return None

        url = f"{self._get_bot_url()}/getChat"
        try:
            data = await self.fetch(url, params={"chat_id": chat_id})
            if data.get("ok"):
                return data.get("result")
            return None
        except Exception as e:
            logger.error("telegram.get_chat_failed", chat_id=chat_id, error=str(e))
            return None

    async def get_chat_member_count(self, chat_id: str) -> int | None:
        """Get the number of members in a chat."""
        if not self.is_configured():
            return None

        url = f"{self._get_bot_url()}/getChatMemberCount"
        try:
            data = await self.fetch(url, params={"chat_id": chat_id})
            if data.get("ok"):
                return data.get("result")
            return None
        except Exception as e:
            logger.error("telegram.member_count_failed", chat_id=chat_id, error=str(e))
            return None

    async def collect(self, **kwargs) -> list[dict]:
        """Collect Telegram social data."""
        if not self.is_configured():
            logger.warning("telegram.skipped", reason="Bot token not configured")
            return []

        chat_id = kwargs.get("chat_id", "")
        if not chat_id:
            return []

        info = await self.get_chat_info(chat_id)
        member_count = await self.get_chat_member_count(chat_id)

        if info:
            info["member_count"] = member_count
            return [info]
        return []

    def normalize_to_social_data(self, chat: dict) -> dict:
        """Normalize Telegram chat data to our SocialData format."""
        return {
            "telegram_members": chat.get("member_count"),
            "telegram_online": None,
            "telegram_messages_24h": None,
            "source": "telegram",
            "extra_data": {
                "chat_id": chat.get("id"),
                "chat_type": chat.get("type"),
                "title": chat.get("title"),
                "username": chat.get("username"),
                "description": chat.get("description"),
            },
        }

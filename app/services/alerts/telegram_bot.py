"""Telegram Bot service for sending alert messages.

Uses Telegram Bot API directly via httpx (no extra dependency needed).
Supports HTML-formatted messages with inline keyboards.
"""

import os

import httpx
import structlog

from app.utils.rate_limiter import rate_limiters

logger = structlog.get_logger()

TELEGRAM_API_BASE = "https://api.telegram.org"
MAX_MESSAGE_LENGTH = 4096


class TelegramBot:
    """Send messages via Telegram Bot API."""

    def __init__(
        self,
        bot_token: str | None = None,
        default_chat_id: str | None = None,
    ):
        self.bot_token = bot_token or os.getenv("TELEGRAM_BOT_TOKEN", "")
        self.default_chat_id = default_chat_id or os.getenv("TELEGRAM_CHAT_ID", "")
        self._client: httpx.AsyncClient | None = None

    def is_configured(self) -> bool:
        return bool(self.bot_token and self.default_chat_id)

    def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=f"{TELEGRAM_API_BASE}/bot{self.bot_token}",
                timeout=30.0,
            )
        return self._client

    async def send_message(
        self,
        text: str,
        chat_id: str | None = None,
        parse_mode: str = "HTML",
        disable_preview: bool = True,
        reply_markup: dict | None = None,
    ) -> dict | None:
        """Send a text message to a Telegram chat."""
        if not self.is_configured():
            logger.warning("telegram.not_configured")
            return None

        target_chat = chat_id or self.default_chat_id
        await rate_limiters.wait_and_acquire("telegram")

        try:
            client = self._get_client()

            if len(text) > MAX_MESSAGE_LENGTH:
                return await self._send_long_message(
                    client, target_chat or "", text, parse_mode, disable_preview
                )

            payload: dict = {
                "chat_id": target_chat,
                "text": text,
                "parse_mode": parse_mode,
                "disable_web_page_preview": disable_preview,
            }
            if reply_markup:
                payload["reply_markup"] = reply_markup

            response = await client.post("/sendMessage", json=payload)
            response.raise_for_status()
            data = response.json()

            if not data.get("ok"):
                logger.error(
                    "telegram.send_failed",
                    error=data.get("description", "Unknown error"),
                )
                return None

            result_data: dict = data["result"]
            logger.info(
                "telegram.message_sent",
                chat_id=target_chat,
                message_id=result_data["message_id"],
            )
            return result_data

        except Exception as e:
            logger.error("telegram.send_error", error=str(e))
            return None

    async def _send_long_message(
        self,
        client: httpx.AsyncClient,
        chat_id: str,
        text: str,
        parse_mode: str,
        disable_preview: bool,
    ) -> dict | None:
        """Split and send messages longer than Telegram's limit."""
        chunks = self._split_message(text)
        last_result = None

        for chunk in chunks:
            await rate_limiters.wait_and_acquire("telegram")
            payload = {
                "chat_id": chat_id,
                "text": chunk,
                "parse_mode": parse_mode,
                "disable_web_page_preview": disable_preview,
            }
            response = await client.post("/sendMessage", json=payload)
            response.raise_for_status()
            data = response.json()
            if data.get("ok"):
                last_result = data["result"]

        return last_result

    @staticmethod
    def _split_message(text: str) -> list[str]:
        """Split text into chunks respecting Telegram's 4096 char limit."""
        if len(text) <= MAX_MESSAGE_LENGTH:
            return [text]

        chunks = []
        while text:
            if len(text) <= MAX_MESSAGE_LENGTH:
                chunks.append(text)
                break

            split_pos = text.rfind("\n", 0, MAX_MESSAGE_LENGTH)
            if split_pos == -1:
                split_pos = MAX_MESSAGE_LENGTH

            chunks.append(text[:split_pos])
            text = text[split_pos:].lstrip("\n")

        return chunks

    async def send_photo(
        self,
        photo_url: str,
        caption: str = "",
        chat_id: str | None = None,
        parse_mode: str = "HTML",
    ) -> dict | None:
        """Send a photo with optional caption."""
        if not self.is_configured():
            return None

        target_chat = chat_id or self.default_chat_id
        await rate_limiters.wait_and_acquire("telegram")

        try:
            client = self._get_client()
            payload = {
                "chat_id": target_chat,
                "photo": photo_url,
                "caption": caption[:1024],
                "parse_mode": parse_mode,
            }
            response = await client.post("/sendPhoto", json=payload)
            response.raise_for_status()
            data = response.json()
            return data.get("result") if data.get("ok") else None

        except Exception as e:
            logger.error("telegram.send_photo_error", error=str(e))
            return None

    async def close(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

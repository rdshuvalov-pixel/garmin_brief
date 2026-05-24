"""Delivery channels for morning briefs."""

from __future__ import annotations

import json
import logging
import os
import urllib.request
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class DeliveryChannel(ABC):
    @abstractmethod
    def send(self, brief_text: str) -> None:
        ...


class StdoutChannel(DeliveryChannel):
    def send(self, brief_text: str) -> None:
        print(brief_text)


class TelegramChannel(DeliveryChannel):
    def __init__(self, bot_token: str, chat_id: str) -> None:
        self.bot_token = bot_token
        self.chat_id = chat_id

    def send(self, brief_text: str) -> None:
        if not self.bot_token or not self.chat_id:
            raise ValueError("TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID are required")

        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        payload = json.dumps(
            {
                "chat_id": self.chat_id,
                "text": brief_text,
                "disable_web_page_preview": False,
            }
        ).encode()

        req = urllib.request.Request(
            url,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            result = json.loads(resp.read())
            if not result.get("ok"):
                raise RuntimeError(f"Telegram API error: {result}")
        logger.info("Telegram message sent to %s", self.chat_id)


def get_delivery_channel() -> DeliveryChannel:
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "")
    chat_id = os.getenv("TELEGRAM_CHAT_ID", "")
    if bot_token and chat_id:
        return TelegramChannel(bot_token, chat_id)
    return StdoutChannel()

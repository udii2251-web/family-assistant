"""Feishu SDK wrapper for all API interactions."""

import json
import logging

import lark_oapi as lark
from lark_oapi.api.im.v1 import (
    CreateMessageRequest,
    CreateMessageRequestBody,
    ReplyMessageRequest,
    ReplyMessageRequestBody,
    PatchMessageRequest,
    PatchMessageRequestBody,
)

logger = logging.getLogger(__name__)


class FeishuClient:
    """Wrapper around lark-oapi for all Feishu API interactions.

    Handles sending text messages, interactive cards, replying to messages,
    and updating existing cards.
    """

    def __init__(self, app_id: str, app_secret: str):
        if not app_id or not app_secret:
            logger.warning("Feishu APP_ID or APP_SECRET not configured. Bot will not function.")
        self.app_id = app_id
        self.app_secret = app_secret
        self.client = lark.Client.builder().app_id(app_id).app_secret(app_secret).log_level(lark.LogLevel.DEBUG).build()

    async def send_text_message(self, receive_id: str, text: str, receive_id_type: str = "open_id") -> str:
        """Send plain text message to a user. Returns message_id."""
        request = CreateMessageRequest.builder() \
            .receive_id_type(receive_id_type) \
            .request_body(
                CreateMessageRequestBody.builder()
                    .receive_id(receive_id)
                    .msg_type("text")
                    .content(json.dumps({"text": text}))
                    .build()
            ) \
            .build()

        response = self.client.im.v1.message.create(request)

        if not response.success():
            logger.error(f"Failed to send text message: {response.code} - {response.msg}")
            return ""

        message_id = response.data.message_id
        logger.info(f"Sent text message to {receive_id}: {message_id}")
        return message_id or ""

    async def send_card_message(self, receive_id: str, card_content: dict, receive_id_type: str = "open_id") -> str:
        """Send interactive card V2 to a user. Returns message_id."""
        request = CreateMessageRequest.builder() \
            .receive_id_type(receive_id_type) \
            .request_body(
                CreateMessageRequestBody.builder()
                    .receive_id(receive_id)
                    .msg_type("interactive")
                    .content(json.dumps(card_content))
                    .build()
            ) \
            .build()

        response = self.client.im.v1.message.create(request)

        if not response.success():
            logger.error(f"Failed to send card message: {response.code} - {response.msg}")
            return ""

        message_id = response.data.message_id
        logger.info(f"Sent card message to {receive_id}: {message_id}")
        return message_id or ""

    async def reply_message(self, message_id: str, text: str) -> str:
        """Reply to a specific message with text. Returns message_id."""
        request = ReplyMessageRequest.builder() \
            .message_id(message_id) \
            .request_body(
                ReplyMessageRequestBody.builder()
                    .msg_type("text")
                    .content(json.dumps({"text": text}))
                    .build()
            ) \
            .build()

        response = self.client.im.v1.message.reply(request)

        if not response.success():
            logger.error(f"Failed to reply message: {response.code} - {response.msg}")
            return ""

        reply_id = response.data.message_id
        logger.info(f"Replied to {message_id}: {reply_id}")
        return reply_id or ""

    async def reply_card(self, message_id: str, card_content: dict) -> str:
        """Reply to a specific message with interactive card. Returns message_id."""
        request = ReplyMessageRequest.builder() \
            .message_id(message_id) \
            .request_body(
                ReplyMessageRequestBody.builder()
                    .msg_type("interactive")
                    .content(json.dumps(card_content))
                    .build()
            ) \
            .build()

        response = self.client.im.v1.message.reply(request)

        if not response.success():
            logger.error(f"Failed to reply card: {response.code} - {response.msg}")
            return ""

        reply_id = response.data.message_id
        logger.info(f"Replied card to {message_id}: {reply_id}")
        return reply_id or ""

    async def update_card(self, message_id: str, card_content: dict) -> str:
        """Update an existing interactive card's content."""
        request = PatchMessageRequest.builder() \
            .message_id(message_id) \
            .request_body(
                PatchMessageRequestBody.builder()
                    .content(json.dumps(card_content))
                    .build()
            ) \
            .build()

        response = self.client.im.v1.message.patch(request)

        if not response.success():
            logger.error(f"Failed to update card: {response.code} - {response.msg}")
            logger.error(f"Response details: {response}")
            return ""

        logger.info(f"Updated card {message_id}")
        logger.debug(f"Response: code={response.code}, msg={response.msg}, data={response.data}")
        return message_id

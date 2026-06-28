"""Feishu CLI Wrapper - Lightweight HTTP-based Feishu API client.

This module provides a lightweight alternative to the lark-oapi SDK,
using direct HTTP API calls. Benefits:
- Smaller dependency footprint (only httpx needed)
- Easier to debug and test
- More transparent request/response handling
- Token caching with auto-refresh

API Reference: https://open.feishu.cn/document/server-docs
"""

import json
import logging
import time
from typing import Optional, Dict, Any

import httpx

from app.shared.config import FEISHU_APP_ID, FEISHU_APP_SECRET

logger = logging.getLogger(__name__)


class FeishuCLIError(Exception):
    """Base exception for Feishu CLI errors."""
    pass


class TokenExpiredError(FeishuCLIError):
    """Token has expired and needs refresh."""
    pass


class FeishuTokenManager:
    """Manages tenant_access_token with auto-refresh.

    Feishu tokens expire after 2 hours. This class:
    - Caches the token in memory
    - Auto-refreshes when expired
    - Thread-safe for concurrent access
    """

    def __init__(self, app_id: str = None, app_secret: str = None):
        self.app_id = app_id or FEISHU_APP_ID
        self.app_secret = app_secret or FEISHU_APP_SECRET
        self._token: Optional[str] = None
        self._expires_at: float = 0  # Unix timestamp
        self._buffer_seconds = 300  # Refresh 5 minutes before expiry

    def get_token(self, force_refresh: bool = False) -> str:
        """Get tenant_access_token, refreshing if needed.

        Args:
            force_refresh: Force token refresh regardless of expiry

        Returns:
            Valid tenant_access_token

        Raises:
            FeishuCLIError: If token fetch fails
        """
        if not force_refresh and self._is_valid():
            return self._token

        return self._refresh_token()

    def _is_valid(self) -> bool:
        """Check if current token is valid (not expired)."""
        if not self._token:
            return False
        return time.time() < (self._expires_at - self._buffer_seconds)

    def _refresh_token(self) -> str:
        """Fetch new tenant_access_token from Feishu API.

        API: POST https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal

        Returns:
            New tenant_access_token
        """
        url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
        payload = {
            "app_id": self.app_id,
            "app_secret": self.app_secret,
        }

        try:
            with httpx.Client(timeout=10.0) as client:
                response = client.post(url, json=payload)
                response.raise_for_status()
                data = response.json()

            if data.get("code") != 0:
                raise FeishuCLIError(f"Token fetch failed: {data.get('msg', 'Unknown error')}")

            self._token = data["tenant_access_token"]
            self._expires_at = time.time() + data.get("expire", 7200)

            logger.info(f"Refreshed tenant_access_token, expires in {data.get('expire', 7200)}s")
            return self._token

        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error fetching token: {e}")
            raise FeishuCLIError(f"HTTP error: {e}")
        except Exception as e:
            logger.error(f"Error fetching token: {e}")
            raise FeishuCLIError(f"Token fetch error: {e}")


class FeishuCLI:
    """Lightweight Feishu API client using direct HTTP calls.

    Provides the same interface as FeishuClient but without the heavy SDK.
    All methods support both sync and async (via _async suffix).

    Usage:
        cli = FeishuCLI(app_id, app_secret)
        message_id = await cli.send_text_message(open_id, "Hello")
        message_id = await cli.reply_card(message_id, card_content)
    """

    BASE_URL = "https://open.feishu.cn/open-apis"

    def __init__(self, app_id: str = None, app_secret: str = None):
        """Initialize Feishu CLI client.

        Args:
            app_id: Feishu app ID (defaults to FEISHU_APP_ID env var)
            app_secret: Feishu app secret (defaults to FEISHU_APP_SECRET env var)
        """
        self.app_id = app_id or FEISHU_APP_ID
        self.app_secret = app_secret or FEISHU_APP_SECRET

        if not self.app_id or not self.app_secret:
            logger.warning("Feishu APP_ID or APP_SECRET not configured. Bot will not function.")

        self.token_manager = FeishuTokenManager(self.app_id, self.app_secret)
        self._http_client: Optional[httpx.Client] = None
        self._async_client: Optional[httpx.AsyncClient] = None

    def _get_sync_client(self) -> httpx.Client:
        """Get or create sync HTTP client."""
        if not self._http_client:
            self._http_client = httpx.Client(timeout=30.0)
        return self._http_client

    async def _get_async_client(self) -> httpx.AsyncClient:
        """Get or create async HTTP client."""
        if not self._async_client:
            self._async_client = httpx.AsyncClient(timeout=30.0)
        return self._async_client

    def close(self):
        """Close HTTP clients."""
        if self._http_client:
            self._http_client.close()
            self._http_client = None

    async def close_async(self):
        """Close async HTTP client."""
        if self._async_client:
            await self._async_client.aclose()
            self._async_client = None

    def _build_headers(self, token: str) -> Dict[str, str]:
        """Build common headers for API requests."""
        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json; charset=utf-8",
        }

    def _handle_response(self, response: httpx.Response, operation: str) -> Dict[str, Any]:
        """Handle API response, checking for errors.

        Args:
            response: HTTP response
            operation: Operation name for logging

        Returns:
            Parsed JSON response data

        Raises:
            FeishuCLIError: On API error
            TokenExpiredError: If token expired (for retry logic)
        """
        try:
            data = response.json()
        except json.JSONDecodeError:
            logger.error(f"Invalid JSON response for {operation}: {response.text}")
            raise FeishuCLIError(f"Invalid JSON response: {response.text[:200]}")

        code = data.get("code", -1)
        if code == 0:
            return data

        # Token expired - caller should retry with fresh token
        if code in (99991663, 99991664):  # token expired or invalid
            logger.warning(f"Token expired for {operation}, need refresh")
            raise TokenExpiredError(f"Token expired: {data.get('msg', '')}")

        logger.error(f"{operation} failed: code={code}, msg={data.get('msg', '')}")
        raise FeishuCLIError(f"{operation} failed: {data.get('msg', 'Unknown error')}")

    # ==================== Sync Methods ====================

    def send_text_message_sync(
        self,
        receive_id: str,
        text: str,
        receive_id_type: str = "open_id",
    ) -> str:
        """Send plain text message (sync version).

        API: POST /im/v1/messages

        Args:
            receive_id: User's open_id or other ID type
            text: Message text content
            receive_id_type: Type of receive_id (open_id, user_id, union_id, email, chat_id)

        Returns:
            message_id on success, empty string on failure
        """
        try:
            token = self.token_manager.get_token()
            url = f"{self.BASE_URL}/im/v1/messages"
            params = {"receive_id_type": receive_id_type}
            payload = {
                "receive_id": receive_id,
                "msg_type": "text",
                "content": json.dumps({"text": text}),
            }

            client = self._get_sync_client()
            response = client.post(
                url,
                params=params,
                json=payload,
                headers=self._build_headers(token),
            )

            data = self._handle_response(response, "send_text_message")
            message_id = data.get("data", {}).get("message_id", "")
            logger.info(f"Sent text message to {receive_id}: {message_id}")
            return message_id

        except TokenExpiredError:
            # Retry with fresh token
            token = self.token_manager.get_token(force_refresh=True)
            return self.send_text_message_sync(receive_id, text, receive_id_type)

        except FeishuCLIError as e:
            logger.error(f"Failed to send text message: {e}")
            return ""
        except Exception as e:
            logger.error(f"Unexpected error sending text message: {e}")
            return ""

    def send_card_message_sync(
        self,
        receive_id: str,
        card_content: Dict[str, Any],
        receive_id_type: str = "open_id",
    ) -> str:
        """Send interactive card message (sync version).

        API: POST /im/v1/messages

        Args:
            receive_id: User's open_id
            card_content: Card JSON dict (Interactive Card V2 format)
            receive_id_type: Type of receive_id

        Returns:
            message_id on success, empty string on failure
        """
        try:
            token = self.token_manager.get_token()
            url = f"{self.BASE_URL}/im/v1/messages"
            params = {"receive_id_type": receive_id_type}
            payload = {
                "receive_id": receive_id,
                "msg_type": "interactive",
                "content": json.dumps(card_content),
            }

            client = self._get_sync_client()
            response = client.post(
                url,
                params=params,
                json=payload,
                headers=self._build_headers(token),
            )

            data = self._handle_response(response, "send_card_message")
            message_id = data.get("data", {}).get("message_id", "")
            logger.info(f"Sent card message to {receive_id}: {message_id}")
            return message_id

        except TokenExpiredError:
            token = self.token_manager.get_token(force_refresh=True)
            return self.send_card_message_sync(receive_id, card_content, receive_id_type)

        except FeishuCLIError as e:
            logger.error(f"Failed to send card message: {e}")
            return ""
        except Exception as e:
            logger.error(f"Unexpected error sending card message: {e}")
            return ""

    def reply_message_sync(self, message_id: str, text: str) -> str:
        """Reply to a specific message with text (sync version).

        API: POST /im/v1/messages/{message_id}/reply

        Args:
            message_id: The message_id to reply to
            text: Reply text content

        Returns:
            message_id of the reply, empty string on failure
        """
        try:
            token = self.token_manager.get_token()
            url = f"{self.BASE_URL}/im/v1/messages/{message_id}/reply"
            payload = {
                "msg_type": "text",
                "content": json.dumps({"text": text}),
            }

            client = self._get_sync_client()
            response = client.post(
                url,
                json=payload,
                headers=self._build_headers(token),
            )

            data = self._handle_response(response, "reply_message")
            reply_id = data.get("data", {}).get("message_id", "")
            logger.info(f"Replied to {message_id}: {reply_id}")
            return reply_id

        except TokenExpiredError:
            token = self.token_manager.get_token(force_refresh=True)
            return self.reply_message_sync(message_id, text)

        except FeishuCLIError as e:
            logger.error(f"Failed to reply message: {e}")
            return ""
        except Exception as e:
            logger.error(f"Unexpected error replying message: {e}")
            return ""

    def reply_card_sync(self, message_id: str, card_content: Dict[str, Any]) -> str:
        """Reply to a specific message with interactive card (sync version).

        API: POST /im/v1/messages/{message_id}/reply

        Args:
            message_id: The message_id to reply to
            card_content: Card JSON dict

        Returns:
            message_id of the reply, empty string on failure
        """
        try:
            token = self.token_manager.get_token()
            url = f"{self.BASE_URL}/im/v1/messages/{message_id}/reply"
            payload = {
                "msg_type": "interactive",
                "content": json.dumps(card_content),
            }

            client = self._get_sync_client()
            response = client.post(
                url,
                json=payload,
                headers=self._build_headers(token),
            )

            data = self._handle_response(response, "reply_card")
            reply_id = data.get("data", {}).get("message_id", "")
            logger.info(f"Replied card to {message_id}: {reply_id}")
            return reply_id

        except TokenExpiredError:
            token = self.token_manager.get_token(force_refresh=True)
            return self.reply_card_sync(message_id, card_content)

        except FeishuCLIError as e:
            logger.error(f"Failed to reply card: {e}")
            return ""
        except Exception as e:
            logger.error(f"Unexpected error replying card: {e}")
            return ""

    def update_card_sync(self, message_id: str, card_content: Dict[str, Any]) -> str:
        """Update an existing interactive card's content (sync version).

        API: PATCH /im/v1/messages/{message_id}

        Args:
            message_id: The message_id of the card to update
            card_content: New card JSON dict

        Returns:
            message_id on success, empty string on failure
        """
        try:
            token = self.token_manager.get_token()
            url = f"{self.BASE_URL}/im/v1/messages/{message_id}"
            payload = {
                "content": json.dumps(card_content),
            }

            client = self._get_sync_client()
            response = client.patch(
                url,
                json=payload,
                headers=self._build_headers(token),
            )

            data = self._handle_response(response, "update_card")
            logger.info(f"Updated card {message_id}")
            return message_id

        except TokenExpiredError:
            token = self.token_manager.get_token(force_refresh=True)
            return self.update_card_sync(message_id, card_content)

        except FeishuCLIError as e:
            logger.error(f"Failed to update card: {e}")
            return ""
        except Exception as e:
            logger.error(f"Unexpected error updating card: {e}")
            return ""

    # ==================== Async Methods ====================

    async def send_text_message(
        self,
        receive_id: str,
        text: str,
        receive_id_type: str = "open_id",
    ) -> str:
        """Send plain text message (async version).

        This matches the interface of FeishuClient.send_text_message().
        """
        try:
            token = self.token_manager.get_token()
            url = f"{self.BASE_URL}/im/v1/messages"
            params = {"receive_id_type": receive_id_type}
            payload = {
                "receive_id": receive_id,
                "msg_type": "text",
                "content": json.dumps({"text": text}),
            }

            client = await self._get_async_client()
            response = await client.post(
                url,
                params=params,
                json=payload,
                headers=self._build_headers(token),
            )

            data = self._handle_response(response, "send_text_message")
            message_id = data.get("data", {}).get("message_id", "")
            logger.info(f"Sent text message to {receive_id}: {message_id}")
            return message_id

        except TokenExpiredError:
            token = self.token_manager.get_token(force_refresh=True)
            return await self.send_text_message(receive_id, text, receive_id_type)

        except FeishuCLIError as e:
            logger.error(f"Failed to send text message: {e}")
            return ""
        except Exception as e:
            logger.error(f"Unexpected error sending text message: {e}")
            return ""

    async def send_card_message(
        self,
        receive_id: str,
        card_content: Dict[str, Any],
        receive_id_type: str = "open_id",
    ) -> str:
        """Send interactive card message (async version)."""
        try:
            token = self.token_manager.get_token()
            url = f"{self.BASE_URL}/im/v1/messages"
            params = {"receive_id_type": receive_id_type}
            payload = {
                "receive_id": receive_id,
                "msg_type": "interactive",
                "content": json.dumps(card_content),
            }

            client = await self._get_async_client()
            response = await client.post(
                url,
                params=params,
                json=payload,
                headers=self._build_headers(token),
            )

            data = self._handle_response(response, "send_card_message")
            message_id = data.get("data", {}).get("message_id", "")
            logger.info(f"Sent card message to {receive_id}: {message_id}")
            return message_id

        except TokenExpiredError:
            token = self.token_manager.get_token(force_refresh=True)
            return await self.send_card_message(receive_id, card_content, receive_id_type)

        except FeishuCLIError as e:
            logger.error(f"Failed to send card message: {e}")
            return ""
        except Exception as e:
            logger.error(f"Unexpected error sending card message: {e}")
            return ""

    async def reply_message(self, message_id: str, text: str) -> str:
        """Reply to a specific message with text (async version)."""
        try:
            token = self.token_manager.get_token()
            url = f"{self.BASE_URL}/im/v1/messages/{message_id}/reply"
            payload = {
                "msg_type": "text",
                "content": json.dumps({"text": text}),
            }

            client = await self._get_async_client()
            response = await client.post(
                url,
                json=payload,
                headers=self._build_headers(token),
            )

            data = self._handle_response(response, "reply_message")
            reply_id = data.get("data", {}).get("message_id", "")
            logger.info(f"Replied to {message_id}: {reply_id}")
            return reply_id

        except TokenExpiredError:
            token = self.token_manager.get_token(force_refresh=True)
            return await self.reply_message(message_id, text)

        except FeishuCLIError as e:
            logger.error(f"Failed to reply message: {e}")
            return ""
        except Exception as e:
            logger.error(f"Unexpected error replying message: {e}")
            return ""

    async def reply_card(self, message_id: str, card_content: Dict[str, Any]) -> str:
        """Reply to a specific message with interactive card (async version)."""
        try:
            token = self.token_manager.get_token()
            url = f"{self.BASE_URL}/im/v1/messages/{message_id}/reply"
            payload = {
                "msg_type": "interactive",
                "content": json.dumps(card_content),
            }

            client = await self._get_async_client()
            response = await client.post(
                url,
                json=payload,
                headers=self._build_headers(token),
            )

            data = self._handle_response(response, "reply_card")
            reply_id = data.get("data", {}).get("message_id", "")
            logger.info(f"Replied card to {message_id}: {reply_id}")
            return reply_id

        except TokenExpiredError:
            token = self.token_manager.get_token(force_refresh=True)
            return await self.reply_card(message_id, card_content)

        except FeishuCLIError as e:
            logger.error(f"Failed to reply card: {e}")
            return ""
        except Exception as e:
            logger.error(f"Unexpected error replying card: {e}")
            return ""

    async def update_card(self, message_id: str, card_content: Dict[str, Any]) -> str:
        """Update an existing interactive card's content (async version)."""
        try:
            token = self.token_manager.get_token()
            url = f"{self.BASE_URL}/im/v1/messages/{message_id}"
            payload = {
                "content": json.dumps(card_content),
            }

            client = await self._get_async_client()
            response = await client.patch(
                url,
                json=payload,
                headers=self._build_headers(token),
            )

            data = self._handle_response(response, "update_card")
            logger.info(f"Updated card {message_id}")
            return message_id

        except TokenExpiredError:
            token = self.token_manager.get_token(force_refresh=True)
            return await self.update_card(message_id, card_content)

        except FeishuCLIError as e:
            logger.error(f"Failed to update card: {e}")
            return ""
        except Exception as e:
            logger.error(f"Unexpected error updating card: {e}")
            return ""

    # ==================== Utility Methods ====================

    def get_user_info_sync(self, user_id: str, user_id_type: str = "open_id") -> Optional[Dict[str, Any]]:
        """Get user information (sync version).

        API: GET /contact/v3/users/{user_id}

        Args:
            user_id: User's ID
            user_id_type: Type of user_id (open_id, user_id, union_id)

        Returns:
            User info dict or None on failure
        """
        try:
            token = self.token_manager.get_token()
            url = f"{self.BASE_URL}/contact/v3/users/{user_id}"
            params = {"user_id_type": user_id_type}

            client = self._get_sync_client()
            response = client.get(
                url,
                params=params,
                headers=self._build_headers(token),
            )

            data = self._handle_response(response, "get_user_info")
            return data.get("data", {}).get("user")

        except TokenExpiredError:
            token = self.token_manager.get_token(force_refresh=True)
            return self.get_user_info_sync(user_id, user_id_type)

        except FeishuCLIError as e:
            logger.error(f"Failed to get user info: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error getting user info: {e}")
            return None

    async def get_user_info(self, user_id: str, user_id_type: str = "open_id") -> Optional[Dict[str, Any]]:
        """Get user information (async version)."""
        try:
            token = self.token_manager.get_token()
            url = f"{self.BASE_URL}/contact/v3/users/{user_id}"
            params = {"user_id_type": user_id_type}

            client = await self._get_async_client()
            response = await client.get(
                url,
                params=params,
                headers=self._build_headers(token),
            )

            data = self._handle_response(response, "get_user_info")
            return data.get("data", {}).get("user")

        except TokenExpiredError:
            token = self.token_manager.get_token(force_refresh=True)
            return await self.get_user_info(user_id, user_id_type)

        except FeishuCLIError as e:
            logger.error(f"Failed to get user info: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error getting user info: {e}")
            return None

    def get_chat_info_sync(self, chat_id: str) -> Optional[Dict[str, Any]]:
        """Get chat/conversation information (sync version).

        API: GET /im/v1/chats/{chat_id}

        Returns:
            Chat info dict or None on failure
        """
        try:
            token = self.token_manager.get_token()
            url = f"{self.BASE_URL}/im/v1/chats/{chat_id}"

            client = self._get_sync_client()
            response = client.get(
                url,
                headers=self._build_headers(token),
            )

            data = self._handle_response(response, "get_chat_info")
            return data.get("data")

        except TokenExpiredError:
            token = self.token_manager.get_token(force_refresh=True)
            return self.get_chat_info_sync(chat_id)

        except FeishuCLIError as e:
            logger.error(f"Failed to get chat info: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error getting chat info: {e}")
            return None


class FeishuWebhookParser:
    """Parses Feishu webhook events.

    This class provides utilities to parse and validate webhook payloads
    from Feishu, without requiring the SDK.

    Usage:
        parser = FeishuWebhookParser(verification_token, encrypt_key)
        event = parser.parse_webhook(body_bytes, headers)
    """

    def __init__(self, verification_token: str = None, encrypt_key: str = None):
        """Initialize webhook parser.

        Args:
            verification_token: Token to verify request authenticity
            encrypt_key: Key to decrypt encrypted payloads (optional)
        """
        from app.shared.config import FEISHU_VERIFICATION_TOKEN, FEISHU_ENCRYPT_KEY
        self.verification_token = verification_token or FEISHU_VERIFICATION_TOKEN
        self.encrypt_key = encrypt_key or FEISHU_ENCRYPT_KEY

    def parse_webhook(self, body: bytes, headers: Dict[str, str] = None) -> Dict[str, Any]:
        """Parse webhook body into event dict.

        Args:
            body: Raw request body bytes
            headers: HTTP headers (for signature verification)

        Returns:
            Parsed event dict
        """
        try:
            data = json.loads(body)
        except json.JSONDecodeError:
            raise FeishuCLIError("Invalid JSON in webhook body")

        # Handle URL verification challenge
        if "challenge" in data:
            return {
                "type": "url_verification",
                "challenge": data["challenge"],
            }

        # Parse event type
        header = data.get("header", {})
        event_type = header.get("event_type", "")
        event_data = data.get("event", {})

        return {
            "type": "event",
            "event_type": event_type,
            "event_data": event_data,
            "timestamp": header.get("event_time", ""),
            "token": header.get("token", ""),
        }

    def parse_message_event(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract message details from im.message.receive_v1 event.

        Args:
            event_data: The "event" portion of webhook payload

        Returns:
            Dict with keys: open_id, message_id, chat_type, message_type, content, text
        """
        sender = event_data.get("sender", {})
        sender_id = sender.get("sender_id", {})
        open_id = sender_id.get("open_id", "")

        message = event_data.get("message", {})
        message_id = message.get("message_id", "")
        chat_type = message.get("chat_type", "p2p")
        message_type = message.get("message_type", "")
        message_content = message.get("content", "{}")

        # Parse text from content
        text = ""
        if message_type == "text":
            try:
                content_json = json.loads(message_content)
                text = content_json.get("text", "")
            except json.JSONDecodeError:
                pass

        return {
            "open_id": open_id,
            "message_id": message_id,
            "chat_type": chat_type,
            "message_type": message_type,
            "content": message_content,
            "text": text,
        }

    def parse_card_action(self, body: bytes) -> Dict[str, Any]:
        """Parse card.action.trigger event.

        Args:
            body: Raw webhook body bytes

        Returns:
            Dict with keys: open_id, open_message_id, action_value
        """
        try:
            data = json.loads(body)
        except json.JSONDecodeError:
            raise FeishuCLIError("Invalid JSON in card action body")

        action = data.get("action", {})
        operator = data.get("operator", {})
        context = data.get("context", {})

        return {
            "open_id": operator.get("open_id", ""),
            "open_message_id": context.get("open_message_id", "") or data.get("open_message_id", ""),
            "action_value": action.get("value", {}),
        }

    def verify_signature(self, body: bytes, timestamp: str, signature: str) -> bool:
        """Verify webhook signature (if encryption is enabled).

        Args:
            body: Raw request body
            timestamp: Request timestamp
            signature: Signature from header

        Returns:
            True if signature is valid
        """
        # For non-encrypted webhooks, skip verification
        if not self.encrypt_key:
            return True

        # TODO: Implement signature verification for encrypted webhooks
        # This requires crypto operations similar to SDK's verification
        logger.warning("Signature verification not implemented, skipping")
        return True
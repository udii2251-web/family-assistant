"""Handler for incoming Feishu events — message received and card action callbacks."""

import json
import logging

from app.feishu.client import FeishuClient
from app.feishu.card_builder import CardBuilder

logger = logging.getLogger(__name__)


class FeishuEventHandler:
    """Processes incoming Feishu events and delegates to the orchestrator.

    Handles two types of events:
    - im.message.receive_v1: user sends a message to the bot
    - card.action.trigger: user clicks a button on an interactive card
    """

    def __init__(self, feishu_client: FeishuClient, orchestrator, session_manager):
        self.client = feishu_client
        self.orchestrator = orchestrator
        self.session_manager = session_manager

    async def handle_message_received(self, event_data: dict) -> None:
        """Parse im.message.receive_v1 event, route to orchestrator, send reply.

        Args:
            event_data: The "event" portion of the Feishu webhook payload.
        """
        # Extract sender and message info
        sender = event_data.get("sender", {})
        sender_id = sender.get("sender_id", {})
        open_id = sender_id.get("open_id", "")
        if not open_id:
            logger.warning("No open_id in message event, skipping")
            return

        message = event_data.get("message", {})
        message_id = message.get("message_id", "")
        message_type = message.get("message_type", "")
        message_content = message.get("content", "{}")
        chat_type = message.get("chat_type", "p2p")

        # Only handle text messages in private chats for MVP
        if chat_type != "p2p":
            logger.debug(f"Skipping group message from {open_id}")
            return

        if message_type != "text":
            logger.debug(f"Skipping non-text message type: {message_type}")
            await self.client.reply_message(message_id, "目前只支持文字消息哦～")
            return

        # Parse text content
        try:
            content_json = json.loads(message_content)
            user_text = content_json.get("text", "")
        except json.JSONDecodeError:
            logger.error(f"Failed to parse message content: {message_content}")
            return

        if not user_text.strip():
            return

        logger.info(f"Received message from {open_id}: {user_text}")

        # Get/create session
        session = self.session_manager.get_or_create(open_id)

        # Add user message to session history
        self.session_manager.add_message(open_id, "user", user_text)

        # Call orchestrator
        try:
            response = await self.orchestrator.handle_message(open_id, user_text, session)
        except Exception as e:
            logger.error(f"Orchestrator failed: {e}")
            await self.client.reply_message(message_id, "抱歉，处理消息时出了点问题，请稍后再试～")
            return

        # Send response based on type
        response_type = response.get("type", "text")
        response_content = response.get("content", "")

        if response_type == "card":
            # response_content is a dict (card JSON)
            msg_id = await self.client.reply_card(message_id, response_content)
        else:
            # response_content is a text string
            msg_id = await self.client.reply_message(message_id, response_content)

        # Add assistant response to session history
        self.session_manager.add_message(open_id, "assistant", str(response_content)[:200])

        logger.info(f"Reply sent to {open_id}: {response_type}")

    async def handle_card_action(self, event_data: dict) -> None:
        """Handle card.action.trigger events (button clicks).

        Args:
            event_data: The full card action event payload.
        """
        # Extract action info
        action = event_data.get("action", {})
        action_value = action.get("value", {})
        operator = event_data.get("operator", {})
        open_id = operator.get("open_id", "")
        open_message_id = event_data.get("open_message_id", "")

        action_type = action_value.get("action", "")
        logger.info(f"Card action from {open_id}: {action_type} with value {action_value}")

        if action_type == "mark_done":
            # Mark the restock alert as done
            alert_id_str = action_value.get("alert_id", "")

            from app.database import SessionLocal
            from app.models.alert import RestockAlert

            db = SessionLocal()
            try:
                # Build the new card to show
                new_card = None

                # Case 1: alert_id is a valid number (from scheduled reminders)
                if alert_id_str and alert_id_str != "0":
                    alert_id = int(alert_id_str)
                    alert = db.query(RestockAlert).filter(RestockAlert.id == alert_id).first()

                    if alert:
                        alert.status = "done"
                        db.commit()
                        logger.info(f"Alert {alert_id} marked as done by {open_id}")
                        new_card = CardBuilder.simple_text_card(
                            "✅ 已补货",
                            f"{alert.message or '补货提醒'}\n\n已由家人确认补货完成。",
                            "green",
                        )
                    else:
                        logger.warning(f"Alert {alert_id} not found")
                        new_card = CardBuilder.simple_text_card(
                            "✅ 已补货",
                            "已由家人确认补货完成。",
                            "green",
                        )

                # Case 2: alert_id is "0" (from manual search in chat)
                else:
                    logger.info(f"Manual purchase confirmation (alert_id=0) from {open_id}")
                    new_card = CardBuilder.simple_text_card(
                        "✅ 已补货",
                        "已由家人确认补货完成。",
                        "green",
                    )

                # Update the card via PATCH API
                if new_card and open_message_id:
                    logger.info(f"Calling PATCH API to update card {open_message_id}")
                    result = await self.client.update_card(open_message_id, new_card)
                    logger.info(f"PATCH API result: {result}")
                else:
                    logger.error(f"Cannot update: new_card={new_card}, open_message_id={open_message_id}")

            finally:
                db.close()
        else:
            logger.warning(f"Unknown card action: {action_type}")

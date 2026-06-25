"""Feishu event dispatcher — supports both webhook and WebSocket long connection modes.

WebSocket mode is recommended for local development (no public IP needed).
Webhook mode is for production deployment with a public HTTPS endpoint.
"""

import json
import asyncio
import logging
import threading

import lark_oapi as lark
from lark_oapi.api.im.v1 import P2ImMessageReceiveV1
from lark_oapi.card.action_handler import CardActionHandlerBuilder
from lark_oapi.card.model import Card

from app.config import (
    FEISHU_APP_ID,
    FEISHU_APP_SECRET,
    FEISHU_VERIFICATION_TOKEN,
    FEISHU_ENCRYPT_KEY,
)

logger = logging.getLogger(__name__)


class FeishuDispatcher:
    """Manages Feishu event subscription using lark-oapi SDK.

    Supports two modes:
    - websocket: Uses SDK's WebSocket client for long connection.
      No public IP needed. Ideal for local development.
    - webhook: Uses HTTP callback endpoint. Requires public HTTPS URL.
      The webhook router in webhook.py handles incoming POST requests.

    In both modes, event handlers are registered via the SDK's
    builder pattern and dispatched to FeishuEventHandler.
    """

    def __init__(self, event_handler, event_loop=None):
        """Initialize dispatcher with the FeishuEventHandler instance.

        Args:
            event_handler: FeishuEventHandler that processes messages and card actions.
            event_loop: The main asyncio event loop (for cross-thread async dispatch).
        """
        self.event_handler = event_handler
        self._event_loop = event_loop
        self._ws_client = None
        self._ws_thread = None

    def _build_event_dispatcher(self) -> lark.EventDispatcherHandler:
        """Build the SDK's event dispatcher with registered handlers.

        Uses lark-oapi SDK's builder pattern to register:
        - P2ImMessageReceiveV1: message received events
        - P2CardActionTrigger: card button click events (for WebSocket mode)
        """
        dispatcher = lark.EventDispatcherHandler.builder(
            FEISHU_ENCRYPT_KEY, FEISHU_VERIFICATION_TOKEN
        )
        dispatcher.register_p2_im_message_receive_v1(self._on_message_received)
        dispatcher.register_p2_card_action_trigger(self._on_card_action_trigger)
        return dispatcher.build()

    def _build_card_action_handler(self) -> lark.CardActionHandler:
        """Build the SDK's card action handler.

        The handler receives a Card object with action.value containing
        the button's value dict, and other metadata.
        """
        builder = CardActionHandlerBuilder(FEISHU_ENCRYPT_KEY, FEISHU_VERIFICATION_TOKEN)
        builder.register(self._on_card_action)
        return builder.build()

    def _on_message_received(self, data: P2ImMessageReceiveV1) -> None:
        """Callback for im.message.receive_v1 events.

        The SDK parses the event and passes a P2ImMessageReceiveV1 object.
        We extract the relevant fields and delegate to FeishuEventHandler.
        """
        try:
            event = data.event
            sender_open_id = event.sender.sender_id.open_id
            message_id = event.message.message_id
            chat_type = event.message.chat_type
            message_type = event.message.message_type
            message_content = event.message.content

            # Build the event_data dict that FeishuEventHandler expects
            event_data = {
                "sender": {
                    "sender_id": {
                        "open_id": sender_open_id,
                    },
                },
                "message": {
                    "message_id": message_id,
                    "chat_type": chat_type,
                    "message_type": message_type,
                    "content": message_content,
                },
            }

            # Run the async handler in the main event loop
            loop = self._get_event_loop()
            asyncio.run_coroutine_threadsafe(
                self.event_handler.handle_message_received(event_data),
                loop,
            )

            logger.info(f"Message event dispatched from {sender_open_id}")

        except Exception as e:
            logger.error(f"Error processing message event: {e}")

    def _on_card_action_trigger(self, data) -> None:
        """Callback for card.action.trigger events via SDK EventDispatcher.

        Used in WebSocket mode. The SDK passes a P2CardActionTrigger object.
        The event payload contains the card action data in a nested structure.

        Args:
            data: P2CardActionTrigger object with event field containing action details.
        """
        try:
            # P2CardActionTrigger.event is a dict-like object
            # The card action event contains: action.value, operator.open_id, context.open_message_id
            event = data.event if data.event else {}
            operator = event.get("operator", {}) if isinstance(event, dict) else {}
            action = event.get("action", {}) if isinstance(event, dict) else {}
            action_value = action.get("value", {}) if isinstance(action, dict) else {}
            operator_open_id = operator.get("open_id", "") if isinstance(operator, dict) else ""

            # IMPORTANT: open_message_id is in event.context.open_message_id, not event.open_message_id
            context = event.get("context", {}) if isinstance(event, dict) else {}
            open_message_id = context.get("open_message_id", "") if isinstance(context, dict) else ""

            # Try to access via object attributes if dict access fails
            if not action_value and hasattr(data, 'event'):
                # The event might be an object, try attribute access
                evt_obj = data.event
                if hasattr(evt_obj, 'action') and evt_obj.action:
                    action_value = evt_obj.action.value if hasattr(evt_obj.action, 'value') else {}
                if hasattr(evt_obj, 'operator') and evt_obj.operator:
                    operator_open_id = evt_obj.operator.open_id if hasattr(evt_obj.operator, 'open_id') else ""
                # Try to get open_message_id from context
                if hasattr(evt_obj, 'context') and evt_obj.context:
                    open_message_id = evt_obj.context.open_message_id if hasattr(evt_obj.context, 'open_message_id') else ""
                elif hasattr(evt_obj, 'open_message_id'):
                    open_message_id = evt_obj.open_message_id or ""

            # Build the event_data dict that FeishuEventHandler expects
            event_data = {
                "action": {"value": action_value},
                "operator": {"open_id": operator_open_id},
                "open_message_id": open_message_id,
            }

            logger.info(f"Card action trigger dispatched from {operator_open_id}: {action_value}")

            # Execute handler synchronously in WebSocket loop
            try:
                loop = asyncio.get_running_loop()
                # Create and execute task immediately
                task = loop.create_task(
                    self.event_handler.handle_card_action(event_data)
                )

                # Add callback to log when done
                def on_task_done(t):
                    try:
                        result = t.result()
                        logger.info(f"Card action handler completed, result: {result}")
                        # Note: We don't return result here because WebSocket callback can't return values
                    except Exception as e:
                        logger.error(f"Card action handler failed: {e}")

                task.add_done_callback(on_task_done)

                logger.info(f"Card action task scheduled in WebSocket loop")

            except RuntimeError as e:
                logger.error(f"No running loop: {e}")

        except Exception as e:
            logger.error(f"Error processing card action trigger: {e}")

    def _on_card_action(self, card: Card) -> dict:
        """Callback for card action via CardActionHandler (webhook HTTP mode).

        The SDK passes a Card object with:
        - card.open_id: the user who clicked
        - card.open_message_id: the message_id of the card
        - card.action.value: the button's value dict
        """
        try:
            operator_open_id = card.open_id or ""
            open_message_id = card.open_message_id or ""
            action_value = card.action.value if card.action else {}

            # Build the event_data dict that FeishuEventHandler expects
            event_data = {
                "action": {"value": action_value},
                "operator": {"open_id": operator_open_id},
                "open_message_id": open_message_id,
            }

            # Run the async handler
            loop = self._get_event_loop()
            asyncio.run_coroutine_threadsafe(
                self.event_handler.handle_card_action(event_data),
                loop,
            )

            logger.info(f"Card action dispatched from {operator_open_id}: {action_value}")

        except Exception as e:
            logger.error(f"Error processing card action: {e}")

        # Return empty response — card updates are done asynchronously via update_card API
        return {}

    def _get_event_loop(self):
        """Get the asyncio event loop for dispatching async handlers.

        When called from the WebSocket's background thread, we need the
        main thread's running loop (stored during lifespan startup).
        """
        if self._event_loop and self._event_loop.is_running():
            return self._event_loop
        try:
            loop = asyncio.get_running_loop()
            return loop
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            return loop

    def _ws_run_standalone(self):
        """Run the entire WebSocket client using asyncio.run() in a fresh thread.

        asyncio.run() creates a brand-new event loop, runs the coroutine,
        then closes the loop. This guarantees that _connect, _receive_message_loop,
        _ping_loop, and _select all use the same loop with no conflicts.

        We patch the module-level `loop` before calling so the SDK uses our loop.
        """
        # Patch the module-level loop to None — asyncio.run() will create
        # a fresh one, and the SDK will pick it up via get_event_loop()
        import lark_oapi.ws.client as ws_client_mod
        ws_client_mod.loop = asyncio.new_event_loop()  # fresh loop

        async def _run_ws():
            """Async wrapper: connect then keep receiving messages."""
            try:
                await self._ws_client._connect()
                logger.info("WebSocket connected via asyncio.run()")
            except Exception as e:
                logger.error(f"WebSocket connect failed: {e}")
                raise

            # Manually start receive + ping loops (same as SDK's start() does)
            import asyncio as aio
            loop = aio.get_running_loop()
            ws_client_mod.loop = loop  # update patch with the actual running loop

            recv_task = loop.create_task(self._ws_client._receive_message_loop())
            ping_task = loop.create_task(self._ws_client._ping_loop())

            logger.info("WebSocket receive and ping loops started")

            # Wait for either task to finish (normally they run forever)
            done, pending = await aio.wait(
                [recv_task, ping_task],
                return_when=aio.FIRST_COMPLETED,
            )

            for task in done:
                if task.exception():
                    logger.error(f"WebSocket loop error: {task.exception()}")

            # Cancel remaining tasks
            for task in pending:
                task.cancel()

        try:
            asyncio.run(_run_ws())
        except Exception as e:
            logger.error(f"WebSocket standalone run error: {e}")

    def start_websocket(self) -> None:
        """Start WebSocket long connection mode.

        This creates a persistent WebSocket connection to Feishu's server.
        No public IP or HTTPS endpoint is required.
        Events are received via the WebSocket and dispatched to registered handlers.
        """
        if not FEISHU_APP_ID or not FEISHU_APP_SECRET:
            logger.error("FEISHU_APP_ID and FEISHU_APP_SECRET must be set for WebSocket mode")
            return

        logger.info(f"Starting Feishu WebSocket connection (app_id: {FEISHU_APP_ID})")

        event_dispatcher = self._build_event_dispatcher()

        self._ws_client = lark.ws.Client(
            app_id=FEISHU_APP_ID,
            app_secret=FEISHU_APP_SECRET,
            log_level=lark.LogLevel.DEBUG,
            event_handler=event_dispatcher,
        )

        # Run WebSocket client in a background thread via asyncio.run()
        # This creates a completely isolated event loop with no conflicts
        self._ws_thread = threading.Thread(target=self._ws_run_standalone, daemon=True)
        self._ws_thread.start()

        logger.info("Feishu WebSocket client started in background thread")

    def stop_websocket(self) -> None:
        """Stop the WebSocket connection."""
        if self._ws_client:
            logger.info("Stopping Feishu WebSocket connection")
            self._ws_client = None
            self._ws_thread = None

"""Scheduled tasks for Taobao module.

Handles:
- Daily login status check
- Weekly order sync
- Login expiry notification
"""

import logging
from datetime import datetime, timedelta
from typing import Optional

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from app.modules.taobao.auth import taobao_auth_manager
from app.modules.taobao.sync import taobao_sync_manager

logger = logging.getLogger(__name__)


class TaobaoScheduler:
    """Manages scheduled tasks for Taobao module.

    Tasks:
    - Daily login status check (every day at 9:00 AM)
    - Weekly order sync (every Monday at 10:00 AM)
    - Login expiry notification (when detected)
    """

    def __init__(self):
        """Initialize scheduler."""
        self.scheduler = AsyncIOScheduler()
        self._notification_callback = None
        self._is_running = False

    def set_notification_callback(self, callback):
        """Set callback function for Feishu notification.

        Args:
            callback: Async function to send notification
                     Signature: async callback(open_id: str, message: str) -> bool
        """
        self._notification_callback = callback
        taobao_auth_manager.set_notification_callback(callback)

    async def start(self):
        """Start scheduled tasks."""
        if self._is_running:
            logger.warning("Taobao scheduler already running")
            return

        try:
            # Schedule daily login check at 9:00 AM
            self.scheduler.add_job(
                self._check_login_status,
                CronTrigger(hour=9, minute=0),
                id='taobao_login_check',
                name='Daily Taobao login status check',
                replace_existing=True
            )

            # Schedule weekly order sync on Monday at 10:00 AM
            self.scheduler.add_job(
                self._sync_orders_weekly,
                CronTrigger(day_of_week='mon', hour=10, minute=0),
                id='taobao_order_sync',
                name='Weekly Taobao order sync',
                replace_existing=True
            )

            # Start scheduler
            self.scheduler.start()
            self._is_running = True

            logger.info("Taobao scheduler started")
            logger.info("  - Daily login check: every day at 9:00 AM")
            logger.info("  - Weekly order sync: every Monday at 10:00 AM")

        except Exception as e:
            logger.error(f"Failed to start Taobao scheduler: {e}")
            raise

    async def stop(self):
        """Stop scheduled tasks."""
        if not self._is_running:
            return

        try:
            self.scheduler.shutdown()
            self._is_running = False
            logger.info("Taobao scheduler stopped")
        except Exception as e:
            logger.error(f"Failed to stop Taobao scheduler: {e}")

    async def _check_login_status(self):
        """Check login status and notify if expired."""
        logger.info("Running scheduled login status check")

        try:
            status = await taobao_auth_manager.check_login_status()

            if status['needs_reauth']:
                logger.warning("Taobao login expired or invalid")

                # Send notification
                if self._notification_callback:
                    # TODO: Get open_id from configuration or database
                    # For now, we'll need to integrate with the main notification system
                    logger.warning("Login expiry detected, notification should be sent")
            else:
                logger.info(f"Taobao login status OK: logged_in={status['is_logged_in']}")

        except Exception as e:
            logger.error(f"Error in scheduled login check: {e}")

    async def _sync_orders_weekly(self):
        """Weekly order sync task."""
        logger.info("Running scheduled weekly order sync")

        try:
            # Check login first
            status = await taobao_auth_manager.check_login_status()

            if not status['is_logged_in'] or status['needs_reauth']:
                logger.warning("Cannot sync orders: Taobao not logged in or login expired")
                return

            # Sync last 7 days
            result = await taobao_sync_manager.sync_orders(days=7)

            if result['success']:
                logger.info(
                    f"Weekly sync completed: "
                    f"{result['total_orders']} orders, "
                    f"{result['new_orders']} new, "
                    f"{result['updated_orders']} updated"
                )
            else:
                logger.error(f"Weekly sync failed: {result['message']}")

        except Exception as e:
            logger.error(f"Error in scheduled order sync: {e}")

    async def run_once(self, task_name: str):
        """Run a scheduled task once immediately.

        Args:
            task_name: 'login_check' or 'order_sync'

        Returns:
            dict: Task result
        """
        if task_name == 'login_check':
            await self._check_login_status()
            return {'task': 'login_check', 'status': 'completed'}
        elif task_name == 'order_sync':
            await self._sync_orders_weekly()
            return {'task': 'order_sync', 'status': 'completed'}
        else:
            return {'task': task_name, 'status': 'unknown'}


# Global instance
taobao_scheduler = TaobaoScheduler()
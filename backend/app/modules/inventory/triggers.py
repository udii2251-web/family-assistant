"""Inventory module triggers.

Migrated from app/services/trigger_engine.py.

Handles:
- Daily restock alert scheduling
- Periodic trigger execution
"""

import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.shared.database import SessionLocal
from app.shared.config import TRIGGER_SCHEDULE_HOUR, TRIGGER_ENABLED

logger = logging.getLogger(__name__)


class TriggerEngine:
    """Framework for scheduling and executing proactive skill triggers.

    Each skill registers triggers via get_triggers().
    The engine schedules these using APScheduler cron triggers.
    When a trigger fires, it calls the skill's handler method with
    a db session and feishu client.
    """

    def __init__(self, feishu_client):
        self.scheduler = AsyncIOScheduler()
        self.feishu_client = feishu_client
        self._registered = False

    def register_all_triggers(self):
        """Iterate all registered skills and register their triggers."""
        from app.skills import get_all_skills

        if self._registered:
            return

        for skill_name, skill in get_all_skills().items():
            for trigger_def in skill.get_triggers():
                if trigger_def["type"] == "periodic":
                    handler_name = trigger_def["handler"]
                    handler = getattr(skill, handler_name)
                    interval = trigger_def.get("interval", "daily")

                    # Map interval to cron triggers
                    if interval == "daily":
                        trigger = CronTrigger(hour=TRIGGER_SCHEDULE_HOUR, minute=0)
                    elif interval == "hourly":
                        trigger = CronTrigger(minute=0)
                    else:
                        trigger = CronTrigger(hour=TRIGGER_SCHEDULE_HOUR, minute=0)

                    job_id = f"{skill_name}_{handler_name}"
                    self.scheduler.add_job(
                        self._execute_trigger,
                        trigger,
                        args=[skill, handler],
                        id=job_id,
                        replace_existing=True,
                    )
                    logger.info(f"Registered trigger: {job_id} ({interval})")

        self._registered = True

    async def _execute_trigger(self, skill, handler_method):
        """Execute a trigger handler with a fresh db session."""
        db = SessionLocal()
        try:
            logger.info(f"Executing trigger for {skill.name}")
            result = await handler_method(db, self.feishu_client)
            logger.info(f"Trigger result for {skill.name}: {result}")
        except Exception as e:
            logger.error(f"Trigger execution failed for {skill.name}: {e}")
        finally:
            db.close()

    def start(self):
        """Start the scheduler."""
        if TRIGGER_ENABLED:
            self.scheduler.start()
            logger.info("Trigger engine started")
        else:
            logger.info("Trigger engine disabled (TRIGGER_ENABLED=false)")

    def shutdown(self):
        """Gracefully shutdown the scheduler."""
        if self.scheduler.running:
            self.scheduler.shutdown()
            logger.info("Trigger engine stopped")

    async def run_all_now(self):
        """Manually trigger all registered jobs immediately (for testing)."""
        from app.skills import get_all_skills

        for skill_name, skill in get_all_skills().items():
            for trigger_def in skill.get_triggers():
                handler_name = trigger_def["handler"]
                handler = getattr(skill, handler_name)
                await self._execute_trigger(skill, handler)
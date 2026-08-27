import logging
import uuid
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from app.core.config import settings
from app.db.session import AsyncSessionLocal
from app.services.notification import NotificationService
from sqlalchemy import text

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler(max_instances=1, coalesce=True)


async def _run_with_advisory_lock(session_factory, coroutine):
    lock_id = 0x5FCEA9D2
    async with session_factory() as db:
        try:
            result = await db.execute(
                text("SELECT pg_try_advisory_xact_lock(:lock_id)"),
                {"lock_id": lock_id},
            )
            acquired = result.scalar()
            if not acquired:
                logger.info("[Scheduler] Skipping tick: another worker holds the re-notify lock")
                return
            await coroutine(db)
        except Exception:
            logger.exception("[Scheduler] Re-notify job failed")
            raise
        finally:
            try:
                await db.close()
            except Exception:
                logger.debug("[Scheduler] Failed to close scheduler session", exc_info=True)


@scheduler.scheduled_job("interval", seconds=settings.NOTIFICATION_SCHEDULER_INTERVAL_SECONDS, max_instances=1, coalesce=True)
async def re_notify_unread():
    print("[Scheduler] Running re_notify_unread job...")
    await _run_with_advisory_lock(AsyncSessionLocal, NotificationService.send_re_notifications)
    print("[Scheduler] re_notify_unread job completed")


def start_scheduler():
    scheduler.start()
    print("[Scheduler] Scheduler started")

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from app.core.config import settings
from app.services.notification import NotificationService
from app.db.session import AsyncSessionLocal


scheduler = AsyncIOScheduler()


@scheduler.scheduled_job(
    "interval",
    seconds=settings.NOTIFICATION_SCHEDULER_INTERVAL_SECONDS,
)
async def re_notify_unread():
    print("[Scheduler] Running re_notify_unread job...")
    async with AsyncSessionLocal() as db:
        await NotificationService.send_re_notifications(db)
    print("[Scheduler] re_notify_unread job completed")


def start_scheduler():
    scheduler.start()
    print("[Scheduler] Scheduler started")

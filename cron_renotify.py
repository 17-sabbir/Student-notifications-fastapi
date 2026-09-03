import asyncio
from sqlalchemy import text
from app.db.session import AsyncSessionLocal
from app.services.notification import NotificationService

LOCK_ID = 0x5FCEA9D2


async def main():
    async with AsyncSessionLocal() as db:
        acquired = (
            await db.execute(
                text("SELECT pg_try_advisory_xact_lock(:lock_id)"),
                {"lock_id": LOCK_ID},
            )
        ).scalar()
        if not acquired:
            print("[Cron] Another re-notify run is in progress, skipping")
            return
        try:
            await NotificationService.send_re_notifications(db)
        except Exception:
            await db.rollback()
            raise


asyncio.run(main())

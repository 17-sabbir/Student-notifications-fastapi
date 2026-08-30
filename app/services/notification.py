from datetime import datetime, timedelta
from typing import Optional
import asyncio
from sqlalchemy import select, and_, or_, func, case
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.notification import NotificationRead, Notification
from app.models.device_token import DeviceToken
from app.models.user import User
from app.core.config import settings
from app.core.timezone import utc_now, to_bd_isoformat
from app.services.fcm import send_fcm_notification


class NotificationService:
    @staticmethod
    async def create_notification(db: AsyncSession, title: str, body: str, created_by_admin_id, is_global=True):
        print(f"[Notification] Creating notification title='{title}' body='{body}' is_global={is_global} created_by={created_by_admin_id}")
        notification = Notification(
            title=title,
            body=body,
            created_by_admin_id=created_by_admin_id,
            is_global=is_global,
        )
        db.add(notification)
        await db.flush()
        print(f"[Notification] Notification flushed id={notification.id}")

        result = await db.execute(select(User.id).where(User.is_active == True, User.role != "admin"))
        user_ids = [row[0] for row in result.fetchall()]
        print(f"[Notification] Found {len(user_ids)} active non-admin users")
        # Stamp last_notified_at at creation: the initial send runs right after
        # this commit, so the rows must not look "never notified" (NULL) to the
        # re-notify scheduler - it treats NULL as eligible and would re-send
        # the brand-new notification during the initial send's window.
        now = utc_now()
        for uid in user_ids:
            db.add(NotificationRead(notification_id=notification.id, user_id=uid, last_notified_at=now))

        await db.commit()
        await db.refresh(notification)
        print(f"[Notification] Committed notification id={notification.id}, title={title}")

        await NotificationService.send_initial_notification(db, notification)
        return notification

    @staticmethod
    async def send_initial_notification(db: AsyncSession, notification: Notification):
        now = utc_now()
        result = await db.execute(
            select(NotificationRead, DeviceToken)
            .join(DeviceToken, DeviceToken.user_id == NotificationRead.user_id)
            .join(User, User.id == NotificationRead.user_id)
            .where(
                NotificationRead.notification_id == notification.id,
                NotificationRead.is_read.is_(False),
                User.is_active.is_(True),
                User.role != "admin",
            )
        )
        rows = result.fetchall()
        print(f"[Notification] Sending initial notification id={notification.id} to {len(rows)} device rows")

        eligible_rows = []
        sent_tokens = set()
        for read, device in rows:
            if device.fcm_token in sent_tokens:
                continue
            sent_tokens.add(device.fcm_token)
            eligible_rows.append((read, device))

        semaphore = asyncio.Semaphore(settings.FCM_SEND_CONCURRENCY)

        async def send_to_device(read, device):
            async with semaphore:
                success, invalid_token = await send_fcm_notification(
                    device.fcm_token,
                    notification.title,
                    notification.body,
                    str(notification.id),
                )
                return read, device, success, invalid_token

        results = await asyncio.gather(
            *(send_to_device(read, device) for read, device in eligible_rows),
            return_exceptions=True,
        )
        successful_sends = 0
        touched = False
        for result in results:
            if isinstance(result, Exception):
                print(f"[Notification] Initial FCM send failed: {result}")
                continue
            read, device, success, invalid_token = result
            if invalid_token:
                print(f"[Notification] Deleting unregistered token={device.fcm_token[:20]}... user_id={device.user_id}")
                await db.delete(device)
                touched = True
                continue
            read.last_notified_at = now
            touched = True
            if success:
                successful_sends += 1

        if touched:
            await db.commit()

        print(f"[Notification] Initially sent notification id={notification.id} to {successful_sends} devices")

    @staticmethod
    async def get_user_notifications(db: AsyncSession, user_id) -> list[dict]:
        print(f"[Notification] Fetching notifications for user_id={user_id}")
        result = await db.execute(
            select(Notification, NotificationRead)
            .join(NotificationRead, Notification.id == NotificationRead.notification_id)
            .where(NotificationRead.user_id == user_id)
            .order_by(Notification.created_at.desc())
        )
        notifications = []
        for notification, read in result.fetchall():
            notifications.append({
                "id": str(notification.id),
                "title": notification.title,
                "body": notification.body,
                "is_global": notification.is_global,
                "created_at": to_bd_isoformat(notification.created_at),
                "is_read": read.is_read,
                "read_at": to_bd_isoformat(read.read_at),
                "last_notified_at": to_bd_isoformat(read.last_notified_at),
            })
        print(f"[Notification] Returning {len(notifications)} notifications for user_id={user_id}")
        return notifications

    @staticmethod
    async def mark_as_read(db: AsyncSession, notification_id, user_id):
        print(f"[Notification] Mark as read notification_id={notification_id} user_id={user_id}")
        result = await db.execute(
            select(NotificationRead).where(
                and_(NotificationRead.notification_id == notification_id, NotificationRead.user_id == user_id)
            )
        )
        read = result.scalar_one_or_none()
        if not read:
            print(f"[Notification] NotificationRead not found for notification_id={notification_id} user_id={user_id}")
            return None
        read.is_read = True
        read.read_at = utc_now()
        await db.commit()
        print(f"[Notification] Marked as read notification_id={notification_id} user_id={user_id}")
        return read

    @staticmethod
    async def list_notifications_with_stats(
        db: AsyncSession, limit: int, offset: int
    ) -> list[dict]:
        read_count_expr = func.coalesce(
            func.sum(case((NotificationRead.is_read.is_(True), 1), else_=0)), 0
        )
        result = await db.execute(
            select(
                Notification,
                func.count(NotificationRead.id).label("total"),
                read_count_expr.label("read_count"),
            )
            .outerjoin(NotificationRead, NotificationRead.notification_id == Notification.id)
            .group_by(Notification.id)
            .order_by(Notification.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        rows = result.all()
        notifications = []
        for notification, total, read_count in rows:
            notifications.append(
                {
                    "id": str(notification.id),
                    "title": notification.title,
                    "body": notification.body,
                    "created_at": to_bd_isoformat(notification.created_at),
                    "total_recipients": total,
                    "read_count": read_count,
                    "unread_count": total - read_count,
                }
            )
        return notifications

    @staticmethod
    async def get_notification_with_stats(db: AsyncSession, notification_id: str) -> Optional[dict]:
        result = await db.execute(select(Notification).where(Notification.id == notification_id))
        notification = result.scalar_one_or_none()
        if not notification:
            return None

        read_count_expr = func.coalesce(
            func.sum(case((NotificationRead.is_read.is_(True), 1), else_=0)), 0
        )
        result = await db.execute(
            select(func.count(NotificationRead.id), read_count_expr).where(
                NotificationRead.notification_id == notification_id
            )
        )
        total, read_count = result.one()
        return {
            "id": str(notification.id),
            "title": notification.title,
            "body": notification.body,
            "created_at": to_bd_isoformat(notification.created_at),
            "total_recipients": total,
            "read_count": read_count,
            "unread_count": total - read_count,
        }

    @staticmethod
    async def get_notification_recipients(
        db: AsyncSession,
        notification_id: str,
        status: Optional[str] = None,
        search: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict]:
        query = (
            select(NotificationRead, User)
            .join(User, User.id == NotificationRead.user_id)
            .where(NotificationRead.notification_id == notification_id)
        )
        if status == "read":
            query = query.where(NotificationRead.is_read.is_(True))
        elif status == "unread":
            query = query.where(NotificationRead.is_read.is_(False))
        if search:
            query = query.where(User.email.ilike(f"%{search}%"))
        query = (
            query.order_by(NotificationRead.read_at.desc().nulls_last(), User.email)
            .limit(limit)
            .offset(offset)
        )
        result = await db.execute(query)
        rows = result.fetchall()
        return [
            {
                "user_id": str(user.id),
                "email": user.email,
                "is_read": read.is_read,
                "read_at": to_bd_isoformat(read.read_at),
            }
            for read, user in rows
        ]

    @staticmethod
    async def send_re_notifications(db: AsyncSession):
        now = utc_now()
        print(f"[Notification] Checking unread notifications for re-notification at {now.isoformat()}")
        result = await db.execute(
            select(NotificationRead, Notification, DeviceToken)
            .join(Notification, Notification.id == NotificationRead.notification_id)
            .join(DeviceToken, DeviceToken.user_id == NotificationRead.user_id)
            .join(User, User.id == NotificationRead.user_id)
            .where(
                NotificationRead.is_read.is_(False),
                User.is_active.is_(True),
                User.role != "admin",
                or_(
                    NotificationRead.last_notified_at.is_(None),
                    NotificationRead.last_notified_at
                    < now - timedelta(minutes=settings.NOTIFICATION_RENOTIFY_INTERVAL_MINUTES),
                ),
            )
        )
        rows = result.fetchall()
        print(f"[Notification] Found {len(rows)} unread notification-device pairs to re-notify")

        count = 0
        touched = False
        semaphore = asyncio.Semaphore(settings.FCM_SEND_CONCURRENCY)

        async def send_and_maybe_cleanup(read, notification, device):
            async with semaphore:
                success, invalid_token = await send_fcm_notification(
                    device.fcm_token,
                    notification.title,
                    notification.body,
                    str(notification.id),
                )
            return read, device, success, invalid_token

        results = await asyncio.gather(
            *(send_and_maybe_cleanup(read, notification, device) for read, notification, device in rows),
            return_exceptions=True,
        )
        for result in results:
            if isinstance(result, Exception):
                print(f"[Notification] Re-notify FCM send failed: {result}")
                continue
            read, device, success, invalid_token = result
            if invalid_token:
                print(f"[Notification] Deleting unregistered token={device.fcm_token[:20]}... user_id={device.user_id}")
                await db.delete(device)
                touched = True
                continue
            read.last_notified_at = now
            touched = True
            if success:
                count += 1
                print(f"[Notification] Successfully re-notified device user_id={device.user_id}")

        if touched:
            await db.commit()

        print(f"[Notification] Re-notified {count} unread notifications")

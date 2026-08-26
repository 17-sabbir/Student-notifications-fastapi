from datetime import datetime, timedelta
from typing import Optional
import asyncio
from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.notification import NotificationRead, Notification
from app.models.device_token import DeviceToken
from app.models.user import User
from app.core.config import settings
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
        for uid in user_ids:
            db.add(NotificationRead(notification_id=notification.id, user_id=uid))

        await db.commit()
        await db.refresh(notification)
        print(f"[Notification] Committed notification id={notification.id}, title={title}")

        await NotificationService.send_initial_notification(db, notification)
        return notification

    @staticmethod
    async def send_initial_notification(db: AsyncSession, notification: Notification):
        now = datetime.utcnow()
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

        candidate_tokens = {device.fcm_token for _, device in rows}
        token_owners = {}
        if candidate_tokens:
            ownership_result = await db.execute(
                select(DeviceToken.fcm_token, DeviceToken.user_id).where(
                    DeviceToken.fcm_token.in_(candidate_tokens)
                )
            )
            for fcm_token, user_id in ownership_result.fetchall():
                token_owners.setdefault(fcm_token, set()).add(user_id)

        eligible_rows = []
        sent_tokens = set()
        for read, device in rows:
            if len(token_owners.get(device.fcm_token, set())) != 1:
                print(f"[Notification] Skipping ambiguous device token={device.fcm_token[:20]}...")
                continue
            if device.fcm_token in sent_tokens:
                continue
            sent_tokens.add(device.fcm_token)
            eligible_rows.append((read, device))

        async def send_to_device(read, device):
            success = await send_fcm_notification(
                device.fcm_token,
                notification.title,
                notification.body,
                str(notification.id),
            )
            return read, success

        results = await asyncio.gather(
            *(send_to_device(read, device) for read, device in eligible_rows),
            return_exceptions=True,
        )
        successful_sends = 0
        attempted_sends = 0
        for result in results:
            if isinstance(result, Exception):
                print(f"[Notification] Initial FCM send failed: {result}")
                continue
            read, success = result
            read.last_notified_at = now
            attempted_sends += 1
            if success:
                successful_sends += 1

        if attempted_sends:
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
                "created_at": notification.created_at.isoformat(),
                "is_read": read.is_read,
                "read_at": read.read_at.isoformat() if read.read_at else None,
                "last_notified_at": read.last_notified_at.isoformat() if read.last_notified_at else None,
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
        read.read_at = datetime.utcnow()
        await db.commit()
        print(f"[Notification] Marked as read notification_id={notification_id} user_id={user_id}")
        return read

    @staticmethod
    async def send_re_notifications(db: AsyncSession):
        now = datetime.utcnow()
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

        candidate_tokens = {device.fcm_token for _, _, device in rows}
        token_owners = {}
        if candidate_tokens:
            ownership_result = await db.execute(
                select(DeviceToken.fcm_token, DeviceToken.user_id).where(
                    DeviceToken.fcm_token.in_(candidate_tokens)
                )
            )
            for fcm_token, user_id in ownership_result.fetchall():
                token_owners.setdefault(fcm_token, set()).add(user_id)

        count = 0
        processed_pairs = set()
        for read, notification, device in rows:
            if len(token_owners.get(device.fcm_token, set())) != 1:
                print(f"[Notification] Skipping ambiguous device token={device.fcm_token[:20]}...")
                continue

            pair = (str(notification.id), device.fcm_token)
            if pair in processed_pairs:
                continue
            processed_pairs.add(pair)

            await db.refresh(read)
            if read.is_read:
                print(f"[Notification] Skipping read notification user_id={read.user_id} notification={notification.id}")
                continue

            print(f"[Notification] Sending FCM to device user_id={device.user_id} token={device.fcm_token[:20]}... notification={notification.id}")
            success = await send_fcm_notification(
                device.fcm_token,
                notification.title,
                notification.body,
                str(notification.id),
            )
            read.last_notified_at = now
            await db.commit()
            if success:
                count += 1
                print(f"[Notification] Successfully re-notified device user_id={device.user_id}")
            else:
                print(f"[Notification] Failed to re-notify device user_id={device.user_id}")
        print(f"[Notification] Re-notified {count} unread notifications")

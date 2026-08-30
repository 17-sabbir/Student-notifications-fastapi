import re
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, insert, update, delete
from app.models.user import User
from app.models.device_token import DeviceToken
from app.core.security import get_password_hash
from app.core.timezone import utc_now


class AuthService:
    @staticmethod
    async def register_device(db: AsyncSession, user: User, fcm_token: str, platform: str, device_id: str):
        print(f"[Device] Registering device user_id={user.id} platform={platform} device_id={device_id} token={fcm_token[:20]}...")

        normalized_token = fcm_token.strip()
        if not normalized_token:
            raise ValueError("fcm_token must not be empty")

        result = await db.execute(
            select(DeviceToken).where(DeviceToken.device_id == device_id)
        )
        existing_by_device = result.scalars().all()
        if existing_by_device:
            for stale in existing_by_device:
                await db.delete(stale)
            await db.commit()
            print(f"[Device] Removed stale device_id={device_id} registration for new owner user_id={user.id}")

        result = await db.execute(
            select(DeviceToken).where(DeviceToken.fcm_token == normalized_token)
        )
        existing_devices = result.scalars().all()
        if existing_devices:
            device = existing_devices[0]
            device.user_id = user.id
            device.platform = platform
            device.device_id = device_id
            device.last_seen_at = utc_now()
            for duplicate in existing_devices[1:]:
                await db.delete(duplicate)
            await db.commit()
            print(f"[Device] Device token assigned to user_id={user.id} token={normalized_token[:20]}...")
            return

        device = DeviceToken(user_id=user.id, fcm_token=normalized_token, platform=platform, device_id=device_id)
        db.add(device)
        await db.commit()
        print(f"[Device] Device registered successfully user_id={user.id} platform={platform}")

    @staticmethod
    async def unregister_device(db: AsyncSession, user: User, device_id: str):
        print(f"[Device] Unregistering device user_id={user.id} device_id={device_id}")
        result = await db.execute(
            select(DeviceToken).where(
                DeviceToken.device_id == device_id,
                DeviceToken.user_id == user.id,
            )
        )
        devices = result.scalars().all()
        if devices:
            for device in devices:
                await db.delete(device)
            await db.commit()
            print(f"[Device] Device unregistered successfully device_id={device_id}")
        else:
            print(f"[Device] Device not found for unregister device_id={device_id}")

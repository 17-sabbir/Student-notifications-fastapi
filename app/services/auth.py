from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.user import User
from app.models.device_token import DeviceToken
from app.core.security import get_password_hash


class AuthService:
    @staticmethod
    async def register_device(db: AsyncSession, user: User, fcm_token: str, platform: str):
        print(f"[Device] Registering device user_id={user.id} platform={platform} token={fcm_token[:20]}...")
        result = await db.execute(
            select(DeviceToken).where(DeviceToken.fcm_token == fcm_token)
        )
        existing_devices = result.scalars().all()
        if existing_devices:
            device = existing_devices[0]
            device.user_id = user.id
            device.platform = platform
            for duplicate in existing_devices[1:]:
                await db.delete(duplicate)
            await db.commit()
            print(f"[Device] Device token assigned to user_id={user.id} token={fcm_token[:20]}...")
            return

        device = DeviceToken(user_id=user.id, fcm_token=fcm_token, platform=platform)
        db.add(device)
        await db.commit()
        print(f"[Device] Device registered successfully user_id={user.id} platform={platform}")

    @staticmethod
    async def unregister_device(db: AsyncSession, fcm_token: str):
        print(f"[Device] Unregistering device token={fcm_token[:20]}...")
        result = await db.execute(
            select(DeviceToken).where(
                DeviceToken.fcm_token == fcm_token,
            )
        )
        devices = result.scalars().all()
        if devices:
            for device in devices:
                await db.delete(device)
            await db.commit()
            print(f"[Device] Device unregistered successfully token={fcm_token[:20]}...")
        else:
            print(f"[Device] Device not found for unregister token={fcm_token[:20]}...")

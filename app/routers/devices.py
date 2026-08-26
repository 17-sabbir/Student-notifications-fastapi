from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.session import get_db
from app.models.user import User
from app.models.device_token import DeviceToken
from app.schemas.notification import DeviceTokenCreate, DeviceTokenUnregister
from app.services.auth import AuthService
from app.core.jwt import get_current_user

router = APIRouter()


@router.post("/register")
async def register_device(
    data: DeviceTokenCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    print(f"[Router] POST /devices/register user_id={current_user.id} platform={data.platform} device_id={data.device_id}")
    await AuthService.register_device(db, current_user, data.fcm_token, data.platform, data.device_id)
    return {"message": "Device registered successfully"}


@router.delete("/unregister")
async def unregister_device(
    data: DeviceTokenUnregister,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    print(f"[Router] DELETE /devices/unregister user_id={current_user.id} device_id={data.device_id}")
    await AuthService.unregister_device(
        db,
        current_user,
        data.device_id,
    )
    return {"message": "Device unregistered successfully"}

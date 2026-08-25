from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.session import get_db
from app.models.notification import Notification, NotificationRead
from app.models.user import User
from app.schemas.notification import NotificationCreate, NotificationResponse
from app.services.notification import NotificationService
from app.core.jwt import get_current_user

router = APIRouter()


@router.get("/", response_model=list[NotificationResponse])
async def get_notifications(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    print(f"[Router] GET /notifications/ user_id={current_user.id}")
    notifications = await NotificationService.get_user_notifications(db, current_user.id)
    print(f"[Router] Returning {len(notifications)} notifications for user_id={current_user.id}")
    return notifications


@router.patch("/{notification_id}/read")
async def mark_as_read(notification_id: str, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    print(f"[Router] PATCH /notifications/{notification_id}/read user_id={current_user.id}")
    read = await NotificationService.mark_as_read(db, notification_id, current_user.id)
    if not read:
        print(f"[Router] Notification not found notification_id={notification_id} user_id={current_user.id}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found")
    print(f"[Router] Marked as read notification_id={notification_id} user_id={current_user.id}")
    return {"message": "Marked as read"}

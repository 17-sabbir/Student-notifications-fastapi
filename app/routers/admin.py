from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from typing import Optional
from app.db.session import get_db
from app.models.user import User
from app.models.notification import Notification, NotificationRead
from app.schemas.notification import (
    AdminNotificationDetail,
    AdminNotificationSummary,
    AdminNotificationUser,
    NotificationCreate,
    NotificationResponse,
)
from app.schemas.user import (
    AdminCreateResponse,
    AdminCreateSchema,
    RoleUpdateResponse,
    UserSearchResponse,
    UserStatusUpdateSchema,
)
from app.services.notification import NotificationService
from app.services.firebase_auth import FirebaseAuthService
from app.core.jwt import get_current_user
from app.core.timezone import to_bd_isoformat

router = APIRouter()


async def require_admin(current_user: User = Depends(get_current_user)):
    if current_user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return current_user


@router.post("/notifications", response_model=NotificationResponse)
async def create_notification(
    data: NotificationCreate,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    print(f"[Admin] Creating notification by admin_id={current_user.id} title='{data.title}' is_global={data.is_global}")
    notification = await NotificationService.create_notification(
        db, data.title, data.body, current_user.id, data.is_global
    )
    print(f"[Admin] Notification created id={notification.id}")
    return NotificationResponse(
        id=str(notification.id),
        title=notification.title,
        body=notification.body,
        is_global=notification.is_global,
        created_at=to_bd_isoformat(notification.created_at),
    )


@router.get("/users", response_model=list[UserSearchResponse])
async def list_users(
    search: Optional[str] = Query(None),
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    print(f"[Admin] Listing users search='{search}' admin_id={current_user.id}")
    query = select(User)
    if search:
        query = query.where(User.email.ilike(f"%{search}%"))
    result = await db.execute(query)
    users = result.scalars().all()
    print(f"[Admin] Found {len(users)} users")
    return [
        UserSearchResponse(
            id=str(u.id),
            email=u.email,
            role=u.role,
            is_verified=u.is_verified,
            is_active=u.is_active,
        )
        for u in users
    ]


@router.patch("/users/{user_id}/status", response_model=RoleUpdateResponse)
async def update_user_status(
    user_id: str,
    data: UserStatusUpdateSchema,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    print(f"[Admin] Updating status user_id={user_id} is_active={data.is_active} by admin_id={current_user.id}")

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    user.is_active = data.is_active
    await db.commit()
    await db.refresh(user)
    print(f"[Admin] Status updated user_id={user.id} email={user.email} is_active={user.is_active}")
    return RoleUpdateResponse(id=str(user.id), email=user.email, role=user.role)


@router.post("/users", response_model=AdminCreateResponse)
async def create_admin(
    data: AdminCreateSchema,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    print(f"[Admin] Creating pending admin email='{data.email}' by admin_id={current_user.id}")
    try:
        user = await FirebaseAuthService.create_pending_admin(db, data.email, data.password)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    print(f"[Admin] Pending admin created user_id={user.id} email={user.email}")
    return AdminCreateResponse(
        id=str(user.id),
        email=user.email,
        role=user.role,
        is_verified=user.is_verified,
        message="Admin created successfully. The admin must be verified before logging in.",
    )


@router.get("/pending-admins", response_model=list[UserSearchResponse])
async def list_pending_admins(
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    print(f"[Admin] Listing pending admins admin_id={current_user.id}")
    result = await db.execute(
        select(User).where(User.role == "admin", User.is_verified == False)
    )
    pending_admins = result.scalars().all()
    print(f"[Admin] Found {len(pending_admins)} pending admins")
    return [
        UserSearchResponse(
            id=str(u.id),
            email=u.email,
            role=u.role,
            is_verified=u.is_verified,
            is_active=u.is_active,
        )
        for u in pending_admins
    ]


@router.patch("/admins/{user_id}/verify", response_model=RoleUpdateResponse)
async def verify_admin(
    user_id: str,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    print(f"[Admin] Verifying admin user_id={user_id} by admin_id={current_user.id}")

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    if user.role != "admin":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User is not an admin")

    user.is_verified = True
    await db.commit()
    await db.refresh(user)
    print(f"[Admin] Admin verified user_id={user.id} email={user.email}")
    return RoleUpdateResponse(id=str(user.id), email=user.email, role=user.role)


@router.get("/notifications", response_model=list[AdminNotificationSummary])
async def list_all_notifications(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    print(f"[Admin] Listing all notifications limit={limit} offset={offset} admin_id={current_user.id}")
    notifications = await NotificationService.list_notifications_with_stats(db, limit, offset)
    print(f"[Admin] Found {len(notifications)} notifications")
    return [AdminNotificationSummary(**n) for n in notifications]


@router.get("/notifications/{notification_id}", response_model=AdminNotificationDetail)
async def get_notification_detail(
    notification_id: str,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    print(f"[Admin] Notification detail notification_id={notification_id} admin_id={current_user.id}")
    notification = await NotificationService.get_notification_with_stats(db, notification_id)
    if not notification:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found")
    return AdminNotificationDetail(**notification)


@router.get("/notifications/{notification_id}/users", response_model=list[AdminNotificationUser])
async def get_notification_recipients(
    notification_id: str,
    status_filter: Optional[str] = Query(None, pattern="^(read|unread|all)$", alias="status"),
    search: Optional[str] = Query(None, min_length=1, max_length=255),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    print(
        f"[Admin] Notification recipients notification_id={notification_id} "
        f"status={status_filter} search='{search}' admin_id={current_user.id}"
    )
    exists = await NotificationService.get_notification_with_stats(db, notification_id)
    if not exists:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found")
    recipients = await NotificationService.get_notification_recipients(
        db,
        notification_id,
        status=status_filter,
        search=search,
        limit=limit,
        offset=offset,
    )
    print(f"[Admin] Returning {len(recipients)} recipients for notification_id={notification_id}")
    return [AdminNotificationUser(**r) for r in recipients]

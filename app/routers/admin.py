from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from sqlalchemy.orm import selectinload
from typing import Optional
from app.db.session import get_db
from app.models.user import User
from app.models.notification import Notification, NotificationRead
from app.schemas.notification import NotificationCreate, NotificationResponse
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
        created_at=notification.created_at.isoformat(),
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


@router.get("/notifications", response_model=list[NotificationResponse])
async def list_all_notifications(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    print(f"[Admin] Listing all notifications limit={limit} offset={offset} admin_id={current_user.id}")
    result = await db.execute(
        select(Notification)
        .order_by(desc(Notification.created_at))
        .limit(limit)
        .offset(offset)
    )
    notifications = result.scalars().all()
    print(f"[Admin] Found {len(notifications)} notifications")
    return [
        NotificationResponse(
            id=str(n.id),
            title=n.title,
            body=n.body,
            is_global=n.is_global,
            created_at=n.created_at.isoformat(),
        )
        for n in notifications
    ]

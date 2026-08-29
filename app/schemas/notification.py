from pydantic import BaseModel, Field
from typing import Optional


class NotificationCreate(BaseModel):
    title: str
    body: str
    is_global: bool = True


class NotificationResponse(BaseModel):
    id: str
    title: str
    body: str
    is_global: bool
    created_at: str
    is_read: bool = False
    read_at: Optional[str] = None
    last_notified_at: Optional[str] = None

    class Config:
        from_attributes = True


class DeviceTokenCreate(BaseModel):
    fcm_token: str = Field(..., min_length=1)
    platform: str = Field(..., pattern="^(android|ios|web)$")
    device_id: str = Field(..., min_length=1, max_length=255)


class DeviceTokenUnregister(BaseModel):
    device_id: str = Field(..., min_length=1, max_length=255)


class AdminNotificationSummary(BaseModel):
    id: str
    title: str
    body: str
    created_at: str
    total_recipients: int
    read_count: int
    unread_count: int


class AdminNotificationDetail(AdminNotificationSummary):
    pass


class AdminNotificationUser(BaseModel):
    user_id: str
    email: str
    is_read: bool
    read_at: Optional[str] = None

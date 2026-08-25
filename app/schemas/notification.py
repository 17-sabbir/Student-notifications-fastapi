from pydantic import BaseModel
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
    fcm_token: str
    platform: str

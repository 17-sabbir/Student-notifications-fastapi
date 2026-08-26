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

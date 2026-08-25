from pydantic import BaseModel, EmailStr
from typing import Optional


class DeviceTokenResponse(BaseModel):
    id: str
    fcm_token: str
    platform: str
    created_at: str

    class Config:
        from_attributes = True


class UserSearchResponse(BaseModel):
    id: str
    email: str
    role: str
    is_verified: bool
    is_active: bool

    class Config:
        from_attributes = True


class UserStatusUpdateSchema(BaseModel):
    is_active: bool


class AdminCreateSchema(BaseModel):
    email: str
    password: str


class AdminCreateResponse(BaseModel):
    id: str
    email: str
    role: str
    is_verified: bool
    message: str


class RoleUpdateResponse(BaseModel):
    id: str
    email: str
    role: str

    class Config:
        from_attributes = True

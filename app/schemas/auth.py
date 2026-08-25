from pydantic import BaseModel, EmailStr, field_validator
from typing import Optional


class SignupSchema(BaseModel):
    email: EmailStr
    password: str

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(c.islower() for c in v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")
        return v


class LoginSchema(BaseModel):
    email: EmailStr
    password: str
    remember_me: bool = False


class OTPVerifySchema(BaseModel):
    email: EmailStr
    otp: str


class ResendOTPSchema(BaseModel):
    email: EmailStr


class TokenSchema(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshTokenSchema(BaseModel):
    refresh_token: str


class UserResponse(BaseModel):
    id: str
    email: str
    is_verified: bool
    role: str

    class Config:
        from_attributes = True

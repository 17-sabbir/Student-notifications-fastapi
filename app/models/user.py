import uuid
from datetime import datetime
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Integer
from sqlalchemy.orm import relationship
from app.db.session import Base


class User(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    is_verified = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    role = Column(String(20), default="user")
    failed_login_count = Column(Integer, default=0)
    locked_until = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    notifications = relationship("Notification", back_populates="created_by_admin", foreign_keys="Notification.created_by_admin_id")
    notification_reads = relationship("NotificationRead", back_populates="user")
    device_tokens = relationship("DeviceToken", back_populates="user")
    refresh_tokens = relationship("RefreshToken", back_populates="user")

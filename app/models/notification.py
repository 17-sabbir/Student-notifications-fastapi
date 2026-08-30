import uuid
from sqlalchemy import Column, String, Text, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.core.timezone import utc_now
from app.db.session import Base


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    title = Column(String(255), nullable=False)
    body = Column(Text, nullable=False)
    created_by_admin_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    is_global = Column(Boolean, default=False)
    created_at = Column(DateTime, default=utc_now)

    created_by_admin = relationship("User", foreign_keys=[created_by_admin_id], back_populates="notifications")
    reads = relationship("NotificationRead", back_populates="notification", cascade="all, delete-orphan")


class NotificationRead(Base):
    __tablename__ = "notification_reads"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    notification_id = Column(String(36), ForeignKey("notifications.id"), nullable=False)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    is_read = Column(Boolean, default=False)
    last_notified_at = Column(DateTime, nullable=True)
    read_at = Column(DateTime, nullable=True)

    notification = relationship("Notification", back_populates="reads")
    user = relationship("User", back_populates="notification_reads")

import uuid
import re
from sqlalchemy import Column, String, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from app.core.timezone import utc_now
from app.db.session import Base


class DeviceToken(Base):
    __tablename__ = "device_tokens"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    device_id = Column(String(255), nullable=False, unique=True, index=True)
    fcm_token = Column(String(255), nullable=False, unique=True, index=True)
    platform = Column(String(20), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)
    last_seen_at = Column(DateTime, default=utc_now)

    user = relationship("User", back_populates="device_tokens")

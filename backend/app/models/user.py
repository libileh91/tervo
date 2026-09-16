"""
Tervo — User model.

Represents a technician or admin who uses the application.
"""

import enum

from sqlalchemy import Boolean, Column, DateTime, Enum, Integer, String, func

from app.models.base import Base


class Role(str, enum.Enum):
    TECHNICIAN = "technician"
    ADMIN = "admin"


class User(Base):
    __tablename__ = "user"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(100), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=True)
    role = Column(Enum(Role), default=Role.TECHNICIAN, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )

    def __repr__(self) -> str:
        return f"<User(id={self.id}, username='{self.username}', role='{self.role.value}')>"

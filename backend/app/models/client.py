"""
ResQ — Client model.

Represents a customer / client site where interventions take place.
"""

from sqlalchemy import Column, DateTime, Integer, String, Text, func

from app.models.base import Base


class Client(Base):
    __tablename__ = "client"

    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String(255), nullable=False, index=True)
    phone = Column(String(50), nullable=False, index=True)
    email = Column(String(255), nullable=True)
    address = Column(String(500), nullable=False)
    postal_code = Column(String(20), nullable=True)
    city = Column(String(255), nullable=True, index=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )

    def __repr__(self) -> str:
        return f"<Client(id={self.id}, name='{self.full_name}')>"

"""Commercial references, independent of installed equipment."""
from sqlalchemy import Boolean, Column, DateTime, Integer, JSON, String, Text, func, true
from sqlalchemy.orm import relationship
from app.models.base import Base


class Product(Base):
    __tablename__ = "product"

    id = Column(Integer, primary_key=True, index=True)
    reference = Column(String(100), nullable=False, unique=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    brand = Column(String(255), nullable=False, index=True)
    model = Column(String(255), nullable=False)
    category = Column(String(100), nullable=False, index=True)
    characteristics = Column(JSON, nullable=True)
    active = Column(Boolean, nullable=False, default=True, server_default=true())
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    equipment = relationship("Equipment", back_populates="product")

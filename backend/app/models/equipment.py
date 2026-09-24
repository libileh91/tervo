"""Physical installed appliances and their preserved replacement chain."""
import enum
from sqlalchemy import Column, Date, DateTime, Enum, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import relationship
from app.models.base import Base


class EquipmentStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    OUT_OF_SERVICE = "OUT_OF_SERVICE"
    REPLACED = "REPLACED"
    RETIRED = "RETIRED"


class Equipment(Base):
    __tablename__ = "equipment"
    id = Column(Integer, primary_key=True, index=True)
    site_id = Column(Integer, ForeignKey("site.id", ondelete="RESTRICT"), nullable=False, index=True)
    product_id = Column(Integer, ForeignKey("product.id", ondelete="RESTRICT"), nullable=True, index=True)
    # Todo later TD-B014 / INT-103: add Installation FK + relationship.
    installation_id = Column(Integer, nullable=True)
    serial_number = Column(String(255), nullable=True, index=True)
    installed_at = Column(Date, nullable=True)
    commissioned_at = Column(Date, nullable=True)
    warranty_start = Column(Date, nullable=True)
    warranty_end = Column(Date, nullable=True)
    lifecycle_status = Column(Enum(EquipmentStatus, native_enum=False, create_constraint=True,
                                   name="equipment_status"), nullable=False, default=EquipmentStatus.ACTIVE,
                              server_default="ACTIVE", index=True)
    replaced_by_id = Column(Integer, ForeignKey("equipment.id", ondelete="RESTRICT"), nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)
    site = relationship("Site", back_populates="equipment")
    product = relationship("Product", back_populates="equipment")
    replaced_by = relationship("Equipment", remote_side=[id])
    interventions = relationship("Intervention", back_populates="equipment")

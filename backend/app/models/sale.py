"""Commercial sale event and its product lines."""
import enum
from sqlalchemy import CheckConstraint, Column, Date, DateTime, Enum, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.orm import relationship
from app.models.base import Base


class SaleStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    CONFIRMED = "CONFIRMED"
    CANCELLED = "CANCELLED"


class Sale(Base):
    __tablename__ = "sale"
    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("client.id", ondelete="RESTRICT"), nullable=False, index=True)
    site_id = Column(Integer, ForeignKey("site.id", ondelete="RESTRICT"), nullable=False, index=True)
    sale_date = Column(Date, nullable=False)
    status = Column(Enum(SaleStatus, native_enum=False, create_constraint=True, name="sale_status"),
                     nullable=False, default=SaleStatus.DRAFT, server_default="DRAFT", index=True)
    notes = Column(Text)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())
    client = relationship("Client", backref="sales")
    site = relationship("Site", backref="sales")
    lines = relationship("SaleLine", back_populates="sale", cascade="all, delete-orphan", order_by="SaleLine.id")


class SaleLine(Base):
    __tablename__ = "sale_line"
    __table_args__ = (
        CheckConstraint("quantity > 0", name="ck_sale_line_quantity_positive"),
        CheckConstraint("unit_price >= 0", name="ck_sale_line_price_nonnegative"),
    )
    id = Column(Integer, primary_key=True, index=True)
    sale_id = Column(Integer, ForeignKey("sale.id", ondelete="CASCADE"), nullable=False, index=True)
    product_id = Column(Integer, ForeignKey("product.id", ondelete="RESTRICT"), nullable=False, index=True)
    quantity = Column(Integer, nullable=False)
    unit_price = Column(Numeric(12, 2), nullable=False)
    description = Column(String(500))
    sale = relationship("Sale", back_populates="lines")
    product = relationship("Product")
    installations = relationship("Installation", back_populates="sale_line", passive_deletes="all")

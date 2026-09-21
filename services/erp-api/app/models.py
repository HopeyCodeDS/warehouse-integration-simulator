from sqlalchemy import Column, String, Integer, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from .database import Base
import uuid

class Product(Base):
    __tablename__ = "products"
    __table_args__ = {'schema': 'erp'}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    sku = Column(String, unique=True, nullable=False)
    name = Column(String, nullable=False)

class Order(Base):
    __tablename__ = "orders"
    __table_args__ = {'schema': 'erp'}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    order_number = Column(String, unique=True, nullable=False)
    correlation_id = Column(String, unique=True, nullable=False, index=True)
    customer = Column(String, nullable=False)
    destination_dock = Column(String, nullable=False)
    status = Column(String, default="PENDING")
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class OrderItem(Base):
    __tablename__ = "order_items"
    __table_args__ = {'schema': 'erp'}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    order_id = Column(UUID(as_uuid=True), ForeignKey("erp.orders.id", ondelete="CASCADE"))
    product_sku = Column(String, nullable=False)
    requested_qty = Column(Integer, nullable=False)

class IntegrationEvent(Base):
    # This maps to the integration schema to simulate the event bus
    __tablename__ = "integration_events"
    __table_args__ = {'schema': 'integration'}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source = Column(String, nullable=False)
    destination = Column(String, nullable=False)
    event_type = Column(String, nullable=False)
    correlation_id = Column(String, index=True)
    payload = Column(String) # Storing JSON as string for simplicity
    status = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
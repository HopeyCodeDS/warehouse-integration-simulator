from sqlalchemy import Column, String, Integer, DateTime
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from .database import Base
import uuid

class Task(Base):
    __tablename__ = "tasks"
    __table_args__ = {'schema': 'wms'} # Bounded Context: WMS only!

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    order_number = Column(String, nullable=False)
    task_type = Column(String, nullable=False)
    status = Column(String, default="PENDING")
    payload = Column(JSONB)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
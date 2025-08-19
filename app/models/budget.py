import uuid
from sqlalchemy import Column, String, Float, ForeignKey

from app.database import Base

class Budget(Base):
    __tablename__ = "budgets"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(100), ForeignKey("users.username", ondelete="CASCADE"), nullable=False, index=True)
    category = Column(String(100), nullable=False)
    limit = Column(Float, nullable=False)

    __table_args__ = (
        # ensure each user has one budget per category
        {"mysql_engine": "InnoDB"},
    ) 
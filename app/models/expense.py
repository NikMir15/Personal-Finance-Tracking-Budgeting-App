from sqlalchemy import Column, String, Float, Date, ForeignKey
import uuid

from app.database import Base

class Expense(Base):
    __tablename__ = "expenses"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(100), ForeignKey("users.username", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    amount = Column(Float, nullable=False)
    currency = Column(String(3), nullable=False, default='USD')  # ISO 4217 currency code
    date = Column(Date, nullable=False)
    category = Column(String(100), nullable=False) 
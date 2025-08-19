from sqlalchemy import Column, String, Float, DateTime, Index
from datetime import datetime
import uuid

from app.database import Base


class CurrencyRate(Base):
    """Store daily exchange rates for currency conversion."""
    __tablename__ = "currency_rates"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    base_currency = Column(String(3), nullable=False)  # ISO 4217 code (e.g., 'USD')
    target_currency = Column(String(3), nullable=False)  # ISO 4217 code (e.g., 'EUR')
    rate = Column(Float, nullable=False)  # Exchange rate from base to target
    date = Column(DateTime, nullable=False, default=datetime.utcnow)
    source = Column(String(50), nullable=False, default="ECB")  # Rate provider
    
    # Create composite index for efficient lookups
    __table_args__ = (
        Index('idx_currency_date', 'base_currency', 'target_currency', 'date'),
        Index('idx_date_currencies', 'date', 'base_currency', 'target_currency'),
    )

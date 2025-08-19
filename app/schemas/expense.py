from datetime import date, datetime
from uuid import uuid4, UUID
from typing import List, Optional

from pydantic import BaseModel, Field, ConfigDict


class ExpenseBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=200, description="Expense title")
    amount: float = Field(..., gt=0, description="Expense amount (must be positive)")
    currency: str = Field(default="USD", min_length=3, max_length=3, description="ISO 4217 currency code")
    date: str = Field(..., description="Expense date")
    category: str = Field(..., min_length=1, max_length=50, description="Expense category")


class ExpenseCreate(ExpenseBase):
    """Schema for creating a new expense."""
    pass


class Expense(BaseModel):
    id: Optional[UUID] = None
    user_id: str
    title: str
    amount: float
    currency: str = "USD"
    date: str
    category: str
    # Optional fields for converted amounts in user's base currency
    base_amount: Optional[float] = None
    base_currency: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)
    
    @classmethod
    def from_db(cls, db_expense, base_amount=None, base_currency=None):
        """Convert database expense object to Pydantic model."""
        return cls(
            id=db_expense.id,
            user_id=db_expense.user_id,
            title=db_expense.title,
            amount=db_expense.amount,
            currency=db_expense.currency,
            date=str(db_expense.date),  # Convert date object to string
            category=db_expense.category,
            base_amount=base_amount,
            base_currency=base_currency
        )


class ExpenseWithAlert(BaseModel):
    expense: Expense
    budget_exceeded: bool = False
    total_spent: Optional[float] = None
    budget_limit: Optional[float] = None


class ExpenseListResponse(BaseModel):
    """Response model for listing expenses with pagination."""
    items: List[Expense]
    total: int
    skip: int
    limit: int
    has_more: bool 
from uuid import UUID, uuid4
from typing import List, Optional

from pydantic import BaseModel, Field, ConfigDict


class BudgetBase(BaseModel):
    category: str = Field(..., min_length=1, max_length=50, description="Budget category")
    limit: float = Field(..., gt=0, description="Budget limit (must be positive)")


class BudgetCreate(BudgetBase):
    pass


class Budget(BudgetBase):
    id: Optional[UUID] = None
    user_id: str

    model_config = ConfigDict(from_attributes=True)


class BudgetListResponse(BaseModel):
    """Response model for listing budgets with pagination."""
    items: List[Budget]
    total: int
    skip: int
    limit: int
    has_more: bool 
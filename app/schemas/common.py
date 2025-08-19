from typing import Generic, TypeVar, Optional
from pydantic import BaseModel, Field

T = TypeVar('T')


class ErrorResponse(BaseModel):
    """Standardized error response format."""
    code: str = Field(..., description="Error code for client handling")
    message: str = Field(..., description="Human-readable error message")


class PaginatedResponse(BaseModel, Generic[T]):
    """Generic paginated response wrapper."""
    items: list[T] = Field(..., description="List of items for current page")
    total: int = Field(..., description="Total number of items")
    skip: int = Field(..., description="Number of items skipped")
    limit: int = Field(..., description="Number of items per page")
    has_more: bool = Field(..., description="Whether there are more items available")


class PaginationParams(BaseModel):
    """Query parameters for pagination."""
    skip: int = Field(default=0, ge=0, description="Number of items to skip")
    limit: int = Field(default=10, ge=1, le=100, description="Number of items to return") 
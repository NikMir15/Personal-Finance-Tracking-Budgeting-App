from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import select, update

from app.dependencies.db import get_db
from app.dependencies.jwt_auth import get_current_user
from app.schemas.budget import BudgetCreate, Budget, BudgetListResponse
from app.schemas.common import ErrorResponse, PaginationParams
from app.models.budget import Budget as BudgetModel

router = APIRouter(prefix="/budgets", tags=["Budgets"])


@router.post(
    "/", 
    response_model=Budget, 
    status_code=status.HTTP_201_CREATED,
    summary="Set or update a budget for a category",
    description="Create a new budget or update existing budget for a category. Validates limit > 0.",
    responses={
        201: {"description": "Budget created successfully"},
        200: {"description": "Budget updated successfully"},
        400: {"model": ErrorResponse, "description": "Validation error"},
        401: {"model": ErrorResponse, "description": "Authentication required"},
        422: {"description": "Request body validation error"}
    }
)
async def set_budget(
    budget_in: BudgetCreate, 
    current_user: str = Depends(get_current_user), 
    db: Session = Depends(get_db)
):
    """Create or update a budget for a category."""
    existing: BudgetModel | None = db.query(BudgetModel).filter(
        BudgetModel.user_id == current_user, 
        BudgetModel.category == budget_in.category
    ).first()
    
    if existing:
        # Update existing budget
        existing.limit = budget_in.limit
        db.commit()
        db.refresh(existing)
        return Budget.model_validate(existing)
    
    # Create new budget
    new_budget = BudgetModel(user_id=current_user, **budget_in.model_dump())
    db.add(new_budget)
    db.commit()
    db.refresh(new_budget)
    return Budget.model_validate(new_budget)


@router.get(
    "/", 
    response_model=BudgetListResponse,
    summary="List budgets of current user",
    description="Get paginated list of budgets for the authenticated user. Supports pagination with skip and limit parameters.",
    responses={
        200: {"description": "Budgets retrieved successfully"},
        401: {"model": ErrorResponse, "description": "Authentication required"},
        422: {"description": "Query parameter validation error"}
    }
)
async def list_budgets(
    pagination: PaginationParams = Depends(),
    current_user: str = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get paginated list of user budgets."""
    # Get total count
    total = db.query(BudgetModel).filter(BudgetModel.user_id == current_user).count()
    
    # Get paginated results
    budgets = (
        db.query(BudgetModel)
        .filter(BudgetModel.user_id == current_user)
        .offset(pagination.skip)
        .limit(pagination.limit)
        .all()
    )
    
    # Calculate if there are more items
    has_more = (pagination.skip + pagination.limit) < total
    
    return BudgetListResponse(
        items=[Budget.model_validate(b) for b in budgets],
        total=total,
        skip=pagination.skip,
        limit=pagination.limit,
        has_more=has_more
    )


@router.delete(
    "/{budget_id}", 
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a budget",
    description="Delete a specific budget by ID. Only the budget owner can delete it.",
    responses={
        204: {"description": "Budget deleted successfully"},
        400: {"model": ErrorResponse, "description": "Invalid budget ID format"},
        401: {"model": ErrorResponse, "description": "Authentication required"},
        404: {"model": ErrorResponse, "description": "Budget not found"}
    }
)
async def delete_budget(
    budget_id: str, 
    current_user: str = Depends(get_current_user), 
    db: Session = Depends(get_db)
):
    """Delete a budget by ID."""
    try:
        budget_uuid = UUID(budget_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "INVALID_UUID", "message": "Invalid budget ID format"}
        )

    budget = db.query(BudgetModel).filter(
        BudgetModel.id == budget_uuid, 
        BudgetModel.user_id == current_user
    ).first()
    
    if not budget:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "BUDGET_NOT_FOUND", "message": "Budget not found"}
        )
    
    db.delete(budget)
    db.commit()
    return 
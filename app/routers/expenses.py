from uuid import uuid4, UUID
from typing import List, cast

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.dependencies.jwt_auth import get_current_user
from app.dependencies.db import get_db
from app.schemas.expense import ExpenseCreate, Expense, ExpenseWithAlert, ExpenseListResponse
from app.schemas.common import ErrorResponse, PaginationParams
from app.models.expense import Expense as ExpenseModel
from app.models.budget import Budget as BudgetModel
from app.models.user import User as UserModel
from app.services.currency_service import CurrencyService

router = APIRouter(prefix="/expenses", tags=["Expenses"])


@router.post(
    "/", 
    response_model=ExpenseWithAlert, 
    status_code=status.HTTP_201_CREATED,
    summary="Create a new expense",
    description="Create a new expense for the authenticated user. Validates amount > 0 and date not in future.",
    responses={
        201: {"description": "Expense created successfully"},
        400: {"model": ErrorResponse, "description": "Validation error"},
        401: {"model": ErrorResponse, "description": "Authentication required"},
        422: {"description": "Request body validation error"}
    }
)
async def create_expense(
    expense: ExpenseCreate, 
    current_user: str = Depends(get_current_user), 
    db: Session = Depends(get_db)
):
    """Create a new expense with budget validation and currency conversion."""
    from datetime import datetime
    
    # Ensure exchange rates are up to date (but don't fail if it doesn't work)
    try:
        await CurrencyService.ensure_rates_updated(db)
    except Exception as e:
        print(f"Warning: Exchange rate update failed: {e}")
    
    # Parse date string to date object
    expense_data = expense.model_dump()
    expense_data['date'] = datetime.strptime(expense_data['date'], '%Y-%m-%d').date()
    
    new_expense = ExpenseModel(user_id=current_user, **expense_data)
    db.add(new_expense)
    db.commit()
    db.refresh(new_expense)

    # Get user's base currency for conversions
    user = db.query(UserModel).filter(UserModel.username == current_user).first()
    user_base_currency = user.base_currency if user and user.base_currency else "USD"

    # Check budget limits - convert all expenses to user's base currency for comparison
    budget: BudgetModel | None = db.query(BudgetModel).filter(
        BudgetModel.user_id == current_user, 
        BudgetModel.category == expense.category
    ).first()
    
    # Calculate total spent in base currency
    category_expenses = db.query(ExpenseModel).filter(
        ExpenseModel.user_id == current_user, 
        ExpenseModel.category == expense.category
    ).all()
    
    total_spent = 0.0
    for exp in category_expenses:
        converted_amount = CurrencyService.convert_amount(
            db, exp.amount, exp.currency, user_base_currency
        )
        if converted_amount is not None:
            total_spent += converted_amount
        else:
            # Fallback to original amount if conversion fails
            total_spent += exp.amount

    exceeded = False
    limit_val = None
    if budget:
        limit_val = cast(float, budget.limit)
        exceeded = total_spent > limit_val

    # Convert expense to base currency for response
    base_amount = CurrencyService.convert_amount(
        db, new_expense.amount, new_expense.currency, user_base_currency
    )

    return ExpenseWithAlert(
        expense=Expense.from_db(new_expense, base_amount, user_base_currency),
        budget_exceeded=exceeded,
        total_spent=total_spent,
        budget_limit=limit_val,
    )


@router.get(
    "/", 
    response_model=ExpenseListResponse,
    summary="List user expenses",
    description="Get paginated list of expenses for the authenticated user. Supports pagination with skip and limit parameters.",
    responses={
        200: {"description": "Expenses retrieved successfully"},
        401: {"model": ErrorResponse, "description": "Authentication required"},
        422: {"description": "Query parameter validation error"}
    }
)
async def list_expenses(
    pagination: PaginationParams = Depends(),
    current_user: str = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get paginated list of user expenses with currency conversions."""
    # Ensure exchange rates are up to date (but don't fail if it doesn't work)
    try:
        await CurrencyService.ensure_rates_updated(db)
    except Exception as e:
        print(f"Warning: Exchange rate update failed: {e}")
    
    # Get user's base currency
    user = db.query(UserModel).filter(UserModel.username == current_user).first()
    user_base_currency = user.base_currency if user and user.base_currency else "USD"
    
    # Get total count
    total = db.query(ExpenseModel).filter(ExpenseModel.user_id == current_user).count()
    
    # Get paginated results
    expenses = (
        db.query(ExpenseModel)
        .filter(ExpenseModel.user_id == current_user)
        .offset(pagination.skip)
        .limit(pagination.limit)
        .all()
    )
    
    # Calculate if there are more items
    has_more = (pagination.skip + pagination.limit) < total
    
    # Convert expenses to include base currency amounts
    expense_items = []
    for expense in expenses:
        base_amount = CurrencyService.convert_amount(
            db, expense.amount, expense.currency, user_base_currency
        )
        expense_items.append(
            Expense.from_db(expense, base_amount, user_base_currency)
        )
    
    return ExpenseListResponse(
        items=expense_items,
        total=total,
        skip=pagination.skip,
        limit=pagination.limit,
        has_more=has_more
    )


@router.delete(
    "/{expense_id}", 
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete an expense",
    description="Delete a specific expense by ID. Only the expense owner can delete it.",
    responses={
        204: {"description": "Expense deleted successfully"},
        400: {"model": ErrorResponse, "description": "Invalid expense ID format"},
        401: {"model": ErrorResponse, "description": "Authentication required"},
        404: {"model": ErrorResponse, "description": "Expense not found"}
    }
)
async def delete_expense(
    expense_id: str, 
    current_user: str = Depends(get_current_user), 
    db: Session = Depends(get_db)
):
    """Delete an expense by ID."""
    # Since ID is stored as string in database, we can use it directly
    expense = db.query(ExpenseModel).filter(
        ExpenseModel.id == expense_id, 
        ExpenseModel.user_id == current_user
    ).first()
    
    if not expense:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "EXPENSE_NOT_FOUND", "message": "Expense not found"}
        )
    
    db.delete(expense)
    db.commit()
    return 
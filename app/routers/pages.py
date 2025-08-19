from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

# Locate the templates directory relative to this file (../templates)
templates_dir = Path(__file__).resolve().parent.parent / "templates"

templates = Jinja2Templates(directory=str(templates_dir))

router = APIRouter(include_in_schema=False)


@router.get(
    "/login", 
    response_class=HTMLResponse,
    summary="Login page",
    description="Serve the login HTML page for user authentication.",
    responses={
        200: {"description": "Login page HTML content"}
    }
)
async def login_page(request: Request):
    """Serve the login HTML page."""
    return templates.TemplateResponse("login.html", {"request": request})


@router.get(
    "/signup", 
    response_class=HTMLResponse,
    summary="Signup page",
    description="Serve the signup HTML page for user registration.",
    responses={
        200: {"description": "Signup page HTML content"}
    }
)
async def signup_page(request: Request):
    """Serve the signup HTML page."""
    return templates.TemplateResponse("signup.html", {"request": request})


@router.get(
    "/me", 
    response_class=HTMLResponse,
    summary="User profile page",
    description="Serve the user profile (me) page showing current user information.",
    responses={
        200: {"description": "Profile page HTML content"}
    }
)
async def me_page(request: Request):
    """Serve the profile (me) page."""
    return templates.TemplateResponse("me.html", {"request": request})


@router.get(
    "/expenses", 
    response_class=HTMLResponse,
    summary="Expenses management page",
    description="Serve the expenses management page for viewing and managing user expenses.",
    responses={
        200: {"description": "Expenses page HTML content"}
    }
)
async def expenses_page(request: Request):
    """Serve the expenses management page."""
    return templates.TemplateResponse("expenses.html", {"request": request})


@router.get(
    "/analytics", 
    response_class=HTMLResponse,
    summary="Analytics dashboard page",
    description="Serve the analytics dashboard page with spending insights and data visualization.",
    responses={
        200: {"description": "Analytics page HTML content"}
    }
)
async def analytics_page(request: Request):
    """Serve the analytics dashboard page."""
    return templates.TemplateResponse("analytics.html", {"request": request})


@router.get(
    "/receipt", 
    response_class=HTMLResponse,
    summary="Receipt scanner page",
    description="Serve the receipt scanner page for OCR-based expense extraction.",
    responses={
        200: {"description": "Receipt scanner page HTML content"}
    }
)
async def receipt_page(request: Request):
    """Serve the receipt scanner page."""
    return templates.TemplateResponse("receipt.html", {"request": request})


@router.get(
    "/upload", 
    response_class=HTMLResponse,
    summary="File upload test page",
    description="Serve a simple page to test image uploads functionality.",
    responses={
        200: {"description": "Upload test page HTML content"}
    }
)
async def upload_test_page(request: Request):
    """Serve a simple page to test image uploads."""
    return templates.TemplateResponse("upload.html", {"request": request}) 
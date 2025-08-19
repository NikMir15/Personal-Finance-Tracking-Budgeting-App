from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.exceptions import RequestValidationError
from app.routers import auth as auth_router
from app.routers import pages as pages_router
from app.routers import expenses as expenses_router
from app.routers import budgets as budgets_router
from app.routers import uploads as uploads_router
from app.routers import currencies as currencies_router
from app.routers import analytics as analytics_router
from app.routers import receipt as receipt_router
from app.routers import health as health_router
from app.routers import data_management as data_management_router
from app.routers import metrics as metrics_router
from app.database import Base, engine

app = FastAPI(
    title="Expense Tracker API",
    description="A comprehensive API for tracking personal expenses and budgets with user authentication and file upload capabilities.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# Import security middleware
from app.middleware.security import (
    security_headers_middleware,
    https_redirect_middleware,
    rate_limit_middleware,
    security_validation_middleware
)
from app.config.security import security_utils

# Import observability components
from app.observability.logging_config import setup_logging, RequestContextMiddleware
from app.observability.metrics import MetricsMiddleware, initialize_app_metrics
from app.observability.error_tracking import initialize_error_tracking, setup_custom_error_handlers
import os

# Initialize observability
setup_logging(
    log_level=os.getenv("LOG_LEVEL", "INFO"),
    json_logs=os.getenv("JSON_LOGS", "true").lower() == "true"
)

initialize_error_tracking(
    environment=os.getenv("ENVIRONMENT", "development"),
    sample_rate=float(os.getenv("SENTRY_SAMPLE_RATE", "1.0")),
    traces_sample_rate=float(os.getenv("SENTRY_TRACES_SAMPLE_RATE", "0.1"))
)

initialize_app_metrics()

# Add observability middleware (order matters!)
app.add_middleware(RequestContextMiddleware)
app.add_middleware(MetricsMiddleware)

# Add security middleware (order matters!)
app.add_middleware(security_validation_middleware)
app.add_middleware(rate_limit_middleware)
app.add_middleware(security_headers_middleware)
app.add_middleware(https_redirect_middleware)

# Add CORS middleware with restricted origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=security_utils.get_cors_origins(),  # Restricted origins based on environment
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "HEAD", "PATCH"],
    allow_headers=[
        "Accept",
        "Accept-Language", 
        "Content-Language",
        "Content-Type",
        "Authorization",
        "X-Requested-With",
        "X-CSRF-Token",
        "Cache-Control"
    ],
    expose_headers=[
        "X-RateLimit-Limit",
        "X-RateLimit-Remaining", 
        "X-RateLimit-Reset",
        "X-RateLimit-Window"
    ]
)

# Global exception handler for standardized error responses
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """Standardize HTTP exception responses."""
    if isinstance(exc.detail, dict) and "code" in exc.detail:
        # Already in standardized format
        return JSONResponse(
            status_code=exc.status_code,
            content=exc.detail
        )
    else:
        # Convert to standardized format
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "code": f"HTTP_{exc.status_code}",
                "message": str(exc.detail) if exc.detail else "An error occurred"
            }
        )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={
            "code": "VALIDATION_ERROR",
            "message": "Request validation failed",
        },
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={
            "code": "INTERNAL_SERVER_ERROR",
            "message": "An unexpected error occurred",
        },
    )

@app.get(
    "/", 
    summary="API Root",
    description="Root endpoint returning API information and status."
)
async def read_root():
    return {
        "message": "Expense Tracker API",
        "version": "1.0.0",
        "docs": "/docs",
        "status": "running"
    }

Base.metadata.create_all(bind=engine)

# Mount static files
app.mount("/static", StaticFiles(directory="app/static"), name="static")

app.include_router(auth_router.router, prefix="/auth", tags=["Auth"])
app.include_router(pages_router.router)
app.include_router(expenses_router.router)
app.include_router(budgets_router.router)
app.include_router(uploads_router.router)
app.include_router(currencies_router.router)
app.include_router(analytics_router.router)
app.include_router(receipt_router.router)
app.include_router(health_router.router)
app.include_router(data_management_router.router)
app.include_router(metrics_router.router)

# Setup custom error handlers for better error tracking
setup_custom_error_handlers(app)

# Add a simple /metrics endpoint at root level for easier Prometheus discovery
@app.get("/metrics", include_in_schema=False)
async def root_metrics():
    """Root level metrics endpoint for Prometheus."""
    from app.observability.metrics import get_metrics_response
    return get_metrics_response()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
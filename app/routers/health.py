"""
Health check and monitoring endpoints for the Expense Tracker application.

Provides endpoints for:
- Health checks (/healthz)
- Readiness checks (/readyz)
- Metrics and monitoring (/metrics)
"""

import time
import psutil
from typing import Dict, Any, List
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.database import get_db
from app.schemas.health import HealthResponse, ReadinessResponse, MetricsResponse, SLOStatus, PerformanceMetrics
from app.monitoring.slo import slo_tracker


router = APIRouter(tags=["Health & Monitoring"])


@router.get("/healthz", response_model=HealthResponse, status_code=200)
async def health_check() -> HealthResponse:
    """
    Basic health check endpoint.
    
    Returns:
        HealthResponse: Application health status
        
    This endpoint checks if the application is alive and responsive.
    Used by load balancers and orchestrators for basic health monitoring.
    """
    return HealthResponse(
        status="healthy",
        timestamp=datetime.utcnow(),
        version="1.0.0",
        uptime=time.time()  # Simple uptime tracking
    )


@router.get("/readyz", response_model=ReadinessResponse, status_code=200)
async def readiness_check(db: Session = Depends(get_db)) -> ReadinessResponse:
    """
    Readiness check endpoint.
    
    Args:
        db: Database session dependency
        
    Returns:
        ReadinessResponse: Application readiness status
        
    Raises:
        HTTPException: 503 if application is not ready
        
    This endpoint checks if the application is ready to serve traffic:
    - Database connectivity
    - Critical dependencies availability
    """
    checks = {}
    overall_status = "ready"
    
    # Database connectivity check
    try:
        db_start = time.time()
        result = db.execute(text("SELECT 1"))
        db_end = time.time()
        
        checks["database"] = {
            "status": "ready",
            "latency_ms": round((db_end - db_start) * 1000, 2),
            "details": "Connection successful"
        }
    except Exception as e:
        checks["database"] = {
            "status": "not_ready",
            "error": str(e),
            "details": "Database connection failed"
        }
        overall_status = "not_ready"
    
    # Memory usage check (warn if > 80%, fail if > 95%)
    try:
        memory_percent = psutil.virtual_memory().percent
        if memory_percent > 95:
            checks["memory"] = {
                "status": "not_ready",
                "usage_percent": memory_percent,
                "details": "Memory usage critical"
            }
            overall_status = "not_ready"
        elif memory_percent > 80:
            checks["memory"] = {
                "status": "degraded",
                "usage_percent": memory_percent,
                "details": "Memory usage high"
            }
        else:
            checks["memory"] = {
                "status": "ready",
                "usage_percent": memory_percent,
                "details": "Memory usage normal"
            }
    except Exception as e:
        checks["memory"] = {
            "status": "unknown",
            "error": str(e),
            "details": "Memory check failed"
        }
    
    # Disk usage check
    try:
        disk_usage = psutil.disk_usage('/')
        disk_percent = (disk_usage.used / disk_usage.total) * 100
        
        if disk_percent > 90:
            checks["disk"] = {
                "status": "not_ready",
                "usage_percent": round(disk_percent, 2),
                "details": "Disk usage critical"
            }
            overall_status = "not_ready"
        elif disk_percent > 75:
            checks["disk"] = {
                "status": "degraded",
                "usage_percent": round(disk_percent, 2),
                "details": "Disk usage high"
            }
        else:
            checks["disk"] = {
                "status": "ready",
                "usage_percent": round(disk_percent, 2),
                "details": "Disk usage normal"
            }
    except Exception as e:
        checks["disk"] = {
            "status": "unknown",
            "error": str(e),
            "details": "Disk check failed"
        }
    
    response = ReadinessResponse(
        status=overall_status,
        timestamp=datetime.utcnow(),
        checks=checks
    )
    
    # Return 503 if not ready
    if overall_status == "not_ready":
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=response.dict()
        )
    
    return response


@router.get("/metrics", response_model=MetricsResponse, status_code=200)
async def metrics_endpoint(db: Session = Depends(get_db)) -> MetricsResponse:
    """
    Metrics endpoint for monitoring and observability.
    
    Args:
        db: Database session dependency
        
    Returns:
        MetricsResponse: Application metrics
        
    Provides detailed metrics for:
    - System resources (CPU, memory, disk)
    - Database performance
    - Application statistics
    """
    # System metrics
    cpu_percent = psutil.cpu_percent(interval=1)
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage('/')
    
    # Database metrics
    db_metrics = {}
    try:
        # Database connection test with timing
        db_start = time.time()
        db.execute(text("SELECT 1"))
        db_latency = (time.time() - db_start) * 1000
        
        # Get basic database stats
        result = db.execute(text("""
            SELECT 
                schemaname,
                tablename,
                n_tup_ins as inserts,
                n_tup_upd as updates,
                n_tup_del as deletes
            FROM pg_stat_user_tables 
            WHERE schemaname = 'public'
            LIMIT 5
        """))
        
        db_metrics = {
            "connection_latency_ms": round(db_latency, 2),
            "status": "connected",
            "pool_info": {
                "pool_size": db.get_bind().pool.size(),
                "checked_in": db.get_bind().pool.checkedin(),
                "checked_out": db.get_bind().pool.checkedout(),
                "overflow": db.get_bind().pool.overflow(),
                "invalid": db.get_bind().pool.invalid()
            } if hasattr(db.get_bind(), 'pool') else {}
        }
        
    except Exception as e:
        db_metrics = {
            "status": "error",
            "error": str(e)
        }
    
    return MetricsResponse(
        timestamp=datetime.utcnow(),
        system={
            "cpu_percent": cpu_percent,
            "memory": {
                "total_gb": round(memory.total / (1024**3), 2),
                "available_gb": round(memory.available / (1024**3), 2),
                "percent": memory.percent,
                "used_gb": round(memory.used / (1024**3), 2)
            },
            "disk": {
                "total_gb": round(disk.total / (1024**3), 2),
                "free_gb": round(disk.free / (1024**3), 2),
                "used_gb": round(disk.used / (1024**3), 2),
                "percent": round((disk.used / disk.total) * 100, 2)
            }
        },
        database=db_metrics,
        application={
            "version": "1.0.0",
            "uptime_seconds": time.time()
        }
    )


@router.get("/livez", status_code=200)
async def liveness_check() -> Dict[str, Any]:
    """
    Kubernetes liveness probe endpoint.
    
    Returns:
        dict: Simple liveness status
        
    This is a minimal endpoint for Kubernetes liveness probes.
    Should only fail if the application process is completely dead.
    """
    return {
        "status": "alive",
        "timestamp": datetime.utcnow().isoformat()
    }


@router.get("/slo", response_model=List[SLOStatus], status_code=200)
async def get_slo_status() -> List[SLOStatus]:
    """
    Get Service Level Objectives (SLO) status.
    
    Returns:
        List[SLOStatus]: Current status of all defined SLOs
        
    This endpoint provides the current status of all SLOs including:
    - Response time targets (p95 < 300ms for GET /expenses)
    - Availability targets (99.9% uptime)
    - Error rate targets (< 1% error rate)
    - Database performance targets
    """
    return slo_tracker.get_all_slo_status()


@router.get("/performance", response_model=List[PerformanceMetrics], status_code=200)
async def get_performance_metrics(endpoint: str = None) -> List[PerformanceMetrics]:
    """
    Get performance metrics for endpoints.
    
    Args:
        endpoint: Optional endpoint filter
        
    Returns:
        List[PerformanceMetrics]: Performance metrics for endpoints
        
    Provides detailed performance metrics including:
    - Response time percentiles (p50, p95, p99)
    - Success rates
    - Request counts
    - Error rates
    """
    return slo_tracker.get_performance_metrics(endpoint)


@router.get("/slo/{slo_name}", response_model=SLOStatus, status_code=200)
async def get_specific_slo(slo_name: str) -> SLOStatus:
    """
    Get status of a specific SLO.
    
    Args:
        slo_name: Name of the SLO to check
        
    Returns:
        SLOStatus: Status of the specified SLO
        
    Available SLOs:
    - response_time_p95: 95th percentile response time
    - response_time_p99: 99th percentile response time  
    - availability: Service uptime percentage
    - error_rate: Error rate percentage
    - db_connection_time: Database connection time
    """
    return slo_tracker.get_slo_status(slo_name)

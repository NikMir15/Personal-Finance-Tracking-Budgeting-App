"""
Pydantic schemas for health check and monitoring endpoints.
"""

from datetime import datetime
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    """Response model for basic health check."""
    
    status: str = Field(..., description="Health status: healthy, unhealthy")
    timestamp: datetime = Field(..., description="Timestamp of the health check")
    version: str = Field(..., description="Application version")
    uptime: float = Field(..., description="Application uptime in seconds")


class ReadinessResponse(BaseModel):
    """Response model for readiness check."""
    
    status: str = Field(..., description="Readiness status: ready, not_ready, degraded")
    timestamp: datetime = Field(..., description="Timestamp of the readiness check")
    checks: Dict[str, Dict[str, Any]] = Field(..., description="Individual component checks")


class MetricsResponse(BaseModel):
    """Response model for metrics endpoint."""
    
    timestamp: datetime = Field(..., description="Timestamp of the metrics collection")
    system: Dict[str, Any] = Field(..., description="System resource metrics")
    database: Dict[str, Any] = Field(..., description="Database performance metrics")
    application: Dict[str, Any] = Field(..., description="Application-specific metrics")


class SLOStatus(BaseModel):
    """Service Level Objective status."""
    
    name: str = Field(..., description="SLO name")
    target: float = Field(..., description="Target value (e.g., 99.9 for 99.9% uptime)")
    current: float = Field(..., description="Current measured value")
    status: str = Field(..., description="SLO status: ok, warning, critical")
    window: str = Field(..., description="Time window for measurement")
    details: Optional[str] = Field(None, description="Additional details")


class PerformanceMetrics(BaseModel):
    """Performance metrics for SLO tracking."""
    
    endpoint: str = Field(..., description="API endpoint")
    method: str = Field(..., description="HTTP method")
    p50_ms: float = Field(..., description="50th percentile response time (ms)")
    p95_ms: float = Field(..., description="95th percentile response time (ms)")
    p99_ms: float = Field(..., description="99th percentile response time (ms)")
    success_rate: float = Field(..., description="Success rate percentage")
    total_requests: int = Field(..., description="Total number of requests")
    error_count: int = Field(..., description="Number of error responses")
    avg_rps: float = Field(..., description="Average requests per second")

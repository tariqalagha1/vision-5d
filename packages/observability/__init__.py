"""
Vision 5D — Production Observability Middleware
Structured logging, request ID, Prometheus metrics, audit logging, health endpoint.
"""
import time, structlog
from fastapi import Request, Response
from prometheus_client import Counter, Histogram, Gauge, generate_latest, REGISTRY
from contextlib import asynccontextmanager

logger = structlog.get_logger()

# ── Prometheus Metrics ──
http_requests_total = Counter(
    "v5d_http_requests_total", "Total HTTP requests",
    ["method", "endpoint", "status"]
)
http_request_duration_seconds = Histogram(
    "v5d_http_request_duration_seconds", "HTTP request duration",
    ["method", "endpoint"], buckets=[0.01, 0.05, 0.1, 0.5, 1, 2, 5, 10, 30]
)
http_requests_in_flight = Gauge(
    "v5d_http_requests_in_flight", "HTTP requests in flight"
)
active_users = Gauge("v5d_active_users", "Currently active user sessions")
jobs_total = Counter(
    "v5d_jobs_total", "Total durable jobs",
    ["job_type", "state"]
)
ai_requests_total = Counter(
    "v5d_ai_requests_total", "Total AI provider calls",
    ["provider", "model", "status"]
)
ai_tokens_total = Counter(
    "v5d_ai_tokens_total", "Total AI tokens consumed",
    ["provider", "type"]  # type: input, output
)
storage_operations = Counter(
    "v5d_storage_operations_total", "Storage operations",
    ["operation", "status"]  # operation: write, read, verify
)
exports_total = Counter(
    "v5d_exports_total", "Total scene exports",
    ["format", "status"]
)
validation_issues = Counter(
    "v5d_validation_issues_total", "Validation issues detected",
    ["severity", "type"]
)
worker_queue_depth = Gauge("v5d_worker_queue_depth", "Jobs waiting in queue")
worker_active = Gauge("v5d_worker_active", "Currently executing jobs")
db_connections = Gauge("v5d_db_connections", "Active database connections")


# ── Middleware ──

class ObservabilityMiddleware:
    """FastAPI middleware for structured logging, metrics, and request IDs."""

    async def __call__(self, request: Request, call_next):
        # Request ID
        request_id = request.headers.get("X-Request-ID", request.headers.get("X-Correlation-ID", ""))
        if not request_id:
            import uuid
            request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        request.state.start_time = time.time()

        # Track in-flight
        http_requests_in_flight.inc()

        # Structured log context
        log_ctx = logger.bind(
            request_id=request_id,
            method=request.method,
            path=request.url.path,
            client_ip=request.client.host if request.client else "",
        )

        try:
            response = await call_next(request)
            duration = time.time() - request.state.start_time

            # Record metrics
            endpoint = _clean_endpoint(request.url.path)
            http_requests_total.labels(
                method=request.method, endpoint=endpoint,
                status=str(response.status_code)
            ).inc()
            http_request_duration_seconds.labels(
                method=request.method, endpoint=endpoint
            ).observe(duration)

            # Log
            log_ctx.info(
                "http_request",
                status=response.status_code,
                duration_ms=round(duration * 1000, 2),
            )

            # Add headers
            response.headers["X-Request-ID"] = request_id
            response.headers["X-Response-Time"] = f"{duration*1000:.0f}ms"

            return response

        except Exception as e:
            duration = time.time() - request.state.start_time
            log_ctx.error("http_error", error=str(e), duration_ms=round(duration*1000, 2))
            http_requests_total.labels(
                method=request.method, endpoint=_clean_endpoint(request.url.path), status="500"
            ).inc()
            raise
        finally:
            http_requests_in_flight.dec()


def _clean_endpoint(path: str) -> str:
    """Normalize endpoint paths by removing UUIDs and IDs."""
    import re
    path = re.sub(r'/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}', '/{id}', path)
    path = re.sub(r'/\d+', '/{id}', path)
    return path


# ── Auditing ──

def log_audit_event(event_code: str, actor_user_id: str, resource_type: str,
                    resource_id: str, details: dict = None, tenant_id: str = None):
    """Persist an audit event with structured fields."""
    logger.info(
        "audit_event",
        event_code=event_code,
        actor_user_id=actor_user_id,
        resource_type=resource_type,
        resource_id=resource_id,
        tenant_id=tenant_id or "",
        details=details or {},
    )


def record_ai_usage(provider: str, model: str, status: str, input_tokens: int, output_tokens: int):
    ai_requests_total.labels(provider=provider, model=model, status=status).inc()
    if input_tokens > 0:
        ai_tokens_total.labels(provider=provider, type="input").inc(input_tokens)
    if output_tokens > 0:
        ai_tokens_total.labels(provider=provider, type="output").inc(output_tokens)


def record_job_metric(job_type: str, state: str):
    jobs_total.labels(job_type=job_type, state=state).inc()


def record_export(format: str, status: str):
    exports_total.labels(format=format, status=status).inc()


def record_validation(severity: str, issue_type: str):
    validation_issues.labels(severity=severity, issue_type=issue_type).inc()


def record_storage_op(operation: str, status: str):
    storage_operations.labels(operation=operation, status=status).inc()

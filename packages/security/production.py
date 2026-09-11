"""
Vision 5D — Production Security Middleware
Rate limiting, brute-force protection, CSP headers, input sanitization.
"""
import time, structlog
from fastapi import Request, HTTPException
from collections import defaultdict

logger = structlog.get_logger()

# ── Rate Limiter ──

class RateLimiter:
    """Simple in-memory rate limiter (use Redis in production)."""

    def __init__(self):
        self._buckets: dict[str, list[float]] = defaultdict(list)
        self._blocked: dict[str, float] = {}  # key → block_until timestamp
        self._cleanup_at = time.time()

    def check(self, key: str, max_requests: int, window_seconds: int) -> bool:
        """Returns True if request is allowed, False if rate-limited."""
        now = time.time()

        # Check if key is blocked
        if key in self._blocked:
            if now < self._blocked[key]:
                return False
            del self._blocked[key]

        # Clean old entries
        bucket = self._buckets[key]
        cutoff = now - window_seconds
        self._buckets[key] = [t for t in bucket if t > cutoff]

        if len(self._buckets[key]) >= max_requests:
            self._blocked[key] = now + window_seconds
            self._buckets[key] = []
            logger.warn("rate_limit_blocked", key=key[:20], max=max_requests, window=window_seconds)
            return False

        self._buckets[key].append(now)

        # Periodic cleanup
        if now - self._cleanup_at > 300:
            self._cleanup(now)

        return True

    def _cleanup(self, now: float):
        stale = [k for k, v in self._buckets.items() if not v]
        for k in stale:
            del self._buckets[k]
        self._cleanup_at = now


rate_limiter = RateLimiter()

# ── Rate limits by endpoint category ──

RATE_LIMITS = {
    "auth": {"max": 10, "window": 60},          # 10 auth requests/min
    "api_read": {"max": 200, "window": 60},      # 200 reads/min
    "api_write": {"max": 50, "window": 60},      # 50 writes/min
    "export": {"max": 10, "window": 60},         # 10 exports/min
    "ai": {"max": 5, "window": 60},              # 5 AI requests/min
}

ENDPOINT_LIMITS = {
    "/api/v1/auth/login": "auth",
    "/api/v1/auth/refresh": "auth",
    "POST:/api/v": "api_write",
    "GET:/api/v": "api_read",
    "/api/v4/projects/": "export",
    "/api/v5/studio/": "export",
    "/api/v6/ai/projects/": "ai",
    "/export/glb": "export",
}


def get_rate_limit_category(method: str, path: str) -> str:
    """Determine rate limit category from method + path."""
    for pattern, category in ENDPOINT_LIMITS.items():
        if pattern.startswith("POST:") or pattern.startswith("GET:"):
            pm, pp = pattern.split(":", 1)
            if method == pm and pp in path:
                return category
        elif pattern in path:
            return category
    return "api_read"


def check_rate_limit(request: Request) -> None:
    """Check rate limits and raise 429 if exceeded."""
    client_ip = request.client.host if request.client else "unknown"
    category = get_rate_limit_category(request.method, request.url.path)
    limit = RATE_LIMITS.get(category, RATE_LIMITS["api_read"])

    key = f"{client_ip}:{category}"
    allowed = rate_limiter.check(key, limit["max"], limit["window"])

    if not allowed:
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded. {limit['max']} requests per {limit['window']}s allowed for {category}.",
            headers={"Retry-After": str(limit["window"])},
        )


# ── Brute Force Protection ──

class BruteForceProtector:
    """Tracks failed login attempts and blocks after threshold."""

    def __init__(self, max_attempts: int = 5, block_seconds: int = 900):
        self.failures: dict[str, list[float]] = defaultdict(list)
        self.max_attempts = max_attempts
        self.block_seconds = block_seconds

    def record_failure(self, key: str):
        now = time.time()
        self.failures[key] = [t for t in self.failures[key] if now - t < self.block_seconds]
        self.failures[key].append(now)

    def is_blocked(self, key: str) -> bool:
        now = time.time()
        attempts = [t for t in self.failures[key] if now - t < self.block_seconds]
        self.failures[key] = attempts
        return len(attempts) >= self.max_attempts

    def reset(self, key: str):
        self.failures.pop(key, None)


brute_force = BruteForceProtector()


# ── Input Sanitization ──

def sanitize_input(value: str) -> str:
    """Strip dangerous characters from user input."""
    if not isinstance(value, str):
        return value
    # Remove null bytes, control characters except common whitespace
    cleaned = value.replace("\x00", "")
    cleaned = "".join(c for c in cleaned if ord(c) >= 32 or c in "\n\r\t")
    return cleaned[:10000]  # Max 10K chars


# ── CSP Headers ──

CSP_HEADER = (
    "default-src 'self'; "
    "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
    "style-src 'self' 'unsafe-inline'; "
    "img-src 'self' data: blob:; "
    "connect-src 'self' http://localhost:* ws://localhost:*; "
    "frame-src 'self'; "
    "object-src 'none'; "
    "base-uri 'self'; "
    "form-action 'self'; "
    "frame-ancestors 'none'; "
    "upgrade-insecure-requests; "
)

SECURITY_HEADERS = {
    "Content-Security-Policy": CSP_HEADER,
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "X-XSS-Protection": "1; mode=block",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
}

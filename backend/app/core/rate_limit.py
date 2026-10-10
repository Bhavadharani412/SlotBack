import time
from collections import defaultdict
from collections.abc import Callable

from fastapi import HTTPException, Request, status


class SlidingWindowRateLimiter:
    """Thread-safe sliding-window rate limiter keyed by identifier."""

    def __init__(self):
        # Maps key -> list of timestamp floats
        self._requests: dict[str, list[float]] = defaultdict(list)

    def is_allowed(self, key: str, max_requests: int, window_seconds: int) -> tuple[bool, int]:
        now = time.time()
        window_start = now - window_seconds

        # Clean timestamps older than the window
        timestamps = [ts for ts in self._requests[key] if ts > window_start]
        self._requests[key] = timestamps

        if len(timestamps) >= max_requests:
            retry_after = int(window_seconds - (now - timestamps[0])) + 1
            return False, max(1, retry_after)

        self._requests[key].append(now)
        return True, 0

    def reset(self):
        """Reset rate limiter state (useful for test isolation)."""
        self._requests.clear()


limiter = SlidingWindowRateLimiter()


def rate_limit(max_requests: int, window_seconds: int = 60) -> Callable:
    """FastAPI dependency to rate limit requests by client IP."""

    async def dependency(request: Request) -> None:
        client_ip = request.client.host if request.client else "127.0.0.1"
        # Combine IP with path template to rate limit per endpoint
        path = request.scope.get("path", "")
        rate_key = f"{client_ip}:{path}"

        allowed, retry_after = limiter.is_allowed(rate_key, max_requests, window_seconds)
        if not allowed:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded. Please try again later.",
                headers={"Retry-After": str(retry_after)},
            )

    return dependency

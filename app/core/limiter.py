from slowapi import Limiter
from slowapi.util import get_remote_address
from app.core.config import settings

storage_uri = settings.REDIS_URL if (settings.REDIS_URL and not settings.REDIS_URL.startswith("redis://localhost")) else "memory://"

limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[settings.RATE_LIMIT_DEFAULT],
    storage_uri=storage_uri,
)

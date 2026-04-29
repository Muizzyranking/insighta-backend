from fastapi import Request
from slowapi import Limiter
from slowapi.util import get_remote_address


def _get_user_or_ip(request: Request) -> str:
    """
    Use authenticated user ID as key if available,
    fall back to IP for unauthenticated requests.
    """
    user = getattr(request.state, "user", None)
    if user and hasattr(user, "id"):
        return user.id
    return get_remote_address(request)


limiter = Limiter(key_func=_get_user_or_ip)

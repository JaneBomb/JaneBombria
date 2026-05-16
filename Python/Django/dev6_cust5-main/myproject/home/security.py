from __future__ import annotations

import hashlib
import time
from functools import wraps
from typing import Callable, Optional

from django.conf import settings
from django.core.cache import cache
from django.http import HttpResponse

# How long (in seconds) the email-2FA one-time code stays valid.
# Used by both the setup flow and the login challenge flow.
EMAIL_OTP_TTL_SECONDS = 5 * 60  # 5 minutes


def _client_ip(request) -> str:
    xff = request.META.get("HTTP_X_FORWARDED_FOR", "")
    if xff:
        # First entry is the original client.
        return xff.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "0.0.0.0")


def _cache_key(scope: str, request, extra: str = "") -> str:
    ip = _client_ip(request)
    raw = f"ratelimit:{scope}:{ip}:{extra}"
    # Hash so we never put untrusted bytes into the cache key.
    return "rl:" + hashlib.sha256(raw.encode("utf-8")).hexdigest()[:32]


def rate_limit(
    scope: str,
    *,
    limit: int,
    window_seconds: int,
    methods: tuple = ("POST",),
    only_on_failure: bool = False,
    key_extra: Optional[Callable] = None,
):
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            # Allow opting out entirely
            if getattr(settings, "RATE_LIMIT_DISABLED", False):
                return view_func(request, *args, **kwargs)

            if request.method not in methods:
                return view_func(request, *args, **kwargs)

            extra = key_extra(request) if key_extra else ""
            key = _cache_key(scope, request, extra=extra)

            # Read current counter + first-hit timestamp.
            entry = cache.get(key)
            now = time.time()
            if entry and now - entry["start"] < window_seconds:
                count = entry["count"]
                start = entry["start"]
            else:
                count = 0
                start = now

            if count >= limit:
                retry_after = int(window_seconds - (now - start))
                resp = HttpResponse(
                    "Too many attempts. Please slow down and try again " f"in {max(retry_after, 1)} seconds.",
                    status=429,
                )
                resp["Retry-After"] = str(max(retry_after, 1))
                return resp

            # Run the view. For only_on_failure, we need to know
            # whether to charge this attempt.
            response = view_func(request, *args, **kwargs)

            should_count = True
            if only_on_failure:
                should_count = bool(getattr(request, "_ratelimit_failure", False))

            if should_count:
                cache.set(
                    key,
                    {"count": count + 1, "start": start},
                    timeout=window_seconds,
                )

            return response

        return wrapper

    return decorator

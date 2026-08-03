"""In-memory cache for built 402 PAYMENT-REQUIRED challenges.

Building a challenge costs a facilitator round-trip, and the unpaid path is the
one every discovery crawler in the ecosystem hammers — indexers probe endpoints
continuously and never pay, so an uncached challenge means a facilitator call
per probe and a hard dependency on the facilitator being up just to answer 402.

Two rules learned the hard way in the sibling seller repo:

1. The fingerprint MUST cover every input that gets baked into the cached
   header. A fingerprint that misses (say) the description lets a rewritten
   catalog description change the code, pass its tests, deploy cleanly, and
   never reach a single buyer — the box keeps serving the old header. That is
   permanent damage, not a delay, because a discovery catalog indexes the
   description once, at the settle that first catalogs the resource.
2. A stale challenge beats no challenge. If the facilitator is down, serving the
   last known good header keeps the endpoint answering 402 instead of 500 —
   indexers record a non-402 response as non-compliant.
"""

from __future__ import annotations

import hashlib
import json
import logging
import time
from typing import Any, Awaitable, Callable

log = logging.getLogger(__name__)

DEFAULT_TTL_SECONDS = 300

# fingerprint -> (built_value, expires_at_monotonic)
_CACHE: dict[str, tuple[Any, float]] = {}


def fingerprint(**parts: Any) -> str:
    """Hash every builder input. Pass ALL of them — see rule 1 in the module doc."""
    blob = json.dumps(parts, sort_keys=True, default=str)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def clear() -> None:
    """Drop every cached challenge (tests, and config reloads)."""
    _CACHE.clear()


async def get_or_build(
    key: str,
    builder: Callable[[], Awaitable[Any]],
    *,
    ttl_seconds: int = DEFAULT_TTL_SECONDS,
) -> Any:
    """Return a cached challenge, else build one.

    On a builder failure, fall back to an expired-but-known-good entry rather
    than propagating — an outage should degrade to a slightly stale 402, never
    to a 500. Raises only when there is nothing cached at all (cold start).
    """
    now = time.monotonic()
    hit = _CACHE.get(key)
    if hit is not None and hit[1] > now:
        return hit[0]

    try:
        built = await builder()
    except Exception:
        if hit is not None:
            log.warning(
                "challenge build failed; serving stale cached challenge", exc_info=True
            )
            return hit[0]
        raise

    _CACHE[key] = (built, now + ttl_seconds)
    return built

from __future__ import annotations

from flask import current_app, request
from redis import Redis

RATE_LIMIT_INCREMENT_SCRIPT = """
local count = redis.call("INCR", KEYS[1])
if redis.call("TTL", KEYS[1]) < 0 then
    redis.call("EXPIRE", KEYS[1], tonumber(ARGV[1]))
end
return count
"""


def increment_rate_limit(
    key: str,
    window_seconds: int,
    *,
    store_config_key: str,
    extension_key: str,
) -> int:
    store = current_app.config.get(store_config_key)
    if store is None:
        if extension_key not in current_app.extensions:
            current_app.extensions[extension_key] = Redis.from_url(
                current_app.config["REDIS_URL"],
                decode_responses=True,
            )
        store = current_app.extensions[extension_key]
    return int(store.eval(RATE_LIMIT_INCREMENT_SCRIPT, 1, key, window_seconds))


def request_source(*, trust_proxy_headers: bool = False) -> str:
    forwarded_for = request.headers.get("X-Forwarded-For", "")
    if trust_proxy_headers and forwarded_for:
        return forwarded_for.split(",", 1)[0].strip()
    return request.remote_addr or "unknown"

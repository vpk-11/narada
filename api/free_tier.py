"""
api/free_tier.py

Daily quota for requests that spend the server's own API keys.

Two caps: per client IP, and server-wide (backstop so one day cannot exhaust
the month's Tavily/Groq allowance). State is in memory and resets on restart
or redeploy; acceptable for a demo, and the global cap bounds the damage.
"""

from datetime import datetime, timezone

from fastapi import HTTPException, Request
from slowapi.util import get_remote_address

from config import Settings, get_settings


def client_ip(request: Request) -> str:
    """
    Client IP behind a reverse proxy. Takes the X-Forwarded-For entry appended
    by the Nth trusted proxy from the right (the left side is client-controlled
    and spoofable), N = TRUSTED_PROXY_HOPS. Falls back to the socket address
    when there is no header. Also the rate limiter's key, so both agree.
    """
    trusted_hops = get_settings().trusted_proxy_hops
    parts = [p.strip() for p in request.headers.get("x-forwarded-for", "").split(",") if p.strip()]
    if len(parts) >= trusted_hops:
        return parts[-trusted_hops]
    return get_remote_address(request)


def _today() -> str:
    return datetime.now(timezone.utc).date().isoformat()


class FreeTierQuota:
    def __init__(self) -> None:
        self._day = _today()
        self._per_ip: dict[str, int] = {}
        self._total = 0

    def _roll(self) -> None:
        today = _today()
        if today != self._day:
            self._day, self._per_ip, self._total = today, {}, 0

    def remaining(self, ip: str, settings: Settings) -> int:
        self._roll()
        return max(
            0,
            min(
                settings.free_tier_per_ip_daily - self._per_ip.get(ip, 0),
                settings.free_tier_global_daily - self._total,
            ),
        )

    def consume(self, ip: str, settings: Settings) -> None:
        """Count one free search or raise 429 with a message naming which cap was hit."""
        self._roll()
        per_ip = settings.free_tier_per_ip_daily
        if self._total >= settings.free_tier_global_daily:
            raise HTTPException(
                status_code=429,
                detail=(
                    "The shared demo has reached today's capacity. "
                    "Add your own API keys in the sidebar, or try again tomorrow."
                ),
            )
        if self._per_ip.get(ip, 0) >= per_ip:
            raise HTTPException(
                status_code=429,
                detail=(
                    f"You have used your {per_ip} free searches for today. "
                    "Come back tomorrow, or add your own API keys in the sidebar."
                ),
            )
        self._per_ip[ip] = self._per_ip.get(ip, 0) + 1
        self._total += 1

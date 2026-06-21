"""
api/limiter.py

Shared rate limiter instance.
Imported by main.py (to register on app) and routes.py (to decorate endpoints).
Avoids circular imports between main and routes.
"""

from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

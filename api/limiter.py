"""
api/limiter.py

Shared rate limiter instance.
Imported by main.py (to register on app) and routes.py (to decorate endpoints).
Avoids circular imports between main and routes.
"""

from slowapi import Limiter

from api.free_tier import client_ip

limiter = Limiter(key_func=client_ip)

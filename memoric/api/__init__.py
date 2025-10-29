"""
Memoric API module.

This module provides the FastAPI web server with authentication, audit logging,
and health check endpoints.
"""

from .server import create_app

__all__ = ["create_app"]

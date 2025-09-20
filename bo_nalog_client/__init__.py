"""
bo-nalog-client: Async client for bo.nalog.gov.ru BFO endpoints

A Python client for accessing financial reports (BFO) from the Russian tax service.
"""

from .client import NalogClient

__version__ = "0.0.1"
__author__ = "Timur"
__email__ = "me@example.com"

__all__ = [
    "NalogClient",
]

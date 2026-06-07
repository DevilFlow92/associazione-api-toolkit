"""
associazione-api-toolkit
~~~~~~~~~~~~~~~~~~~~~~~~

Shared Python toolkit for the associazione-api ecosystem.

Modules:
    - logging    → structured JSON logging with request-id propagation
    - decorators → @retry, @timed, @validate_env
    - pagination → offset and cursor-based pagination helpers
    - http       → resilient async HTTP client
    - health     → health check client and aggregator
"""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("associazione-api-toolkit")
except PackageNotFoundError:
    __version__ = "unknown"

__all__ = ["__version__"]

"""Dynamic loader for pytryfi - allows using external or embedded version."""
import os
import sys
import logging

_LOGGER = logging.getLogger(__name__)

# Check for development mode environment variable
USE_EXTERNAL_PYTRYFI = os.environ.get("TRYFI_USE_EXTERNAL_PYTRYFI", "false").lower() == "true"

if USE_EXTERNAL_PYTRYFI:
    try:
        # Try to import external pytryfi
        import pytryfi
        from pytryfi import PyTryFi
        _LOGGER.info("Using external pytryfi library")
        PYTRYFI_MODE = "external"
    except ImportError:
        _LOGGER.warning("External pytryfi not found, falling back to embedded version")
        from .pytryfi import PyTryFi
        PYTRYFI_MODE = "embedded"
else:
    # Use embedded pytryfi
    from .pytryfi import PyTryFi
    PYTRYFI_MODE = "embedded"
    _LOGGER.debug("Using embedded pytryfi library")

__all__ = ["PyTryFi", "PYTRYFI_MODE"]
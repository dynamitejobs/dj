"""Re-export the public surface from the single-file dj.py."""
from .dj import DJ, DJError, VERSION, main

__all__ = ["DJ", "DJError", "VERSION", "main"]
__version__ = VERSION

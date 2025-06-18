"""
massphotometry v0.1.0: A Python package for mass photometry data analysis.

This package provides tools for reading and processing mass photometry data.
"""

from .read import read_mp
from .metadata import convert_metadata, empty_metadata

__version__ = "0.1.0"
__all__ = ["read_mp", "convert_metadata", "empty_metadata"]

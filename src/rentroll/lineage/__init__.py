"""Lineage: every model row traces to its source file, line and job run."""

from .lookup import property_lineage

__all__ = ["property_lineage"]

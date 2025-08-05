"""Bangladeshi Parcel Tracker Package.

A Python package for tracking parcels from various Bangladeshi courier services.
"""

from .base import BaseTracker, TrackingEvent, TrackingStatus, TrackingError
from .providers import RedxTracker, SteadfastTracker, PathaoTracker, RokomariTracker, SundarbanTracker
from . import cli

__all__ = [
    "BaseTracker",
    "TrackingEvent",
    "TrackingStatus",
    "TrackingError",
    "RedxTracker",
    "SteadfastTracker",
    "PathaoTracker",
    "RokomariTracker",
    "SundarbanTracker",
    "cli",
]

__version__ = "0.1.0"

"""Base classes for parcel tracking."""

from abc import ABC, abstractmethod
from datetime import datetime
from enum import Enum
from typing import List, Optional
from dataclasses import dataclass


class TrackingStatus(Enum):
    """Enumeration of possible tracking statuses."""

    PENDING = "pending"
    PICKED_UP = "picked_up"
    IN_TRANSIT = "in_transit"
    OUT_FOR_DELIVERY = "out_for_delivery"
    DELIVERED = "delivered"
    RETURNED = "returned"
    CANCELLED = "cancelled"
    FAILED_DELIVERY = "failed_delivery"
    UNKNOWN = "unknown"


@dataclass
class TrackingEvent:
    """Represents a single tracking event in the parcel's journey."""

    timestamp: datetime
    status: TrackingStatus
    location: Optional[str] = None
    description: Optional[str] = None
    details: Optional[str] = None

    def __str__(self) -> str:
        """Return a human-readable string representation of the event."""
        date_str = self.timestamp.strftime("%Y-%m-%d %H:%M:%S")
        location_str = f" at {self.location}" if self.location else ""
        desc = self.description or ""
        return f"[{date_str}] {self.status.value.title()}{location_str}: {desc}"


class BaseTracker(ABC):
    """Abstract base class for all parcel tracking providers."""

    def __init__(self, tracking_number: str):
        """Initialize the tracker with a tracking number.

        Args:
            tracking_number: The tracking/consignment number for the parcel
        """
        self.tracking_number = tracking_number.strip()
        self._events: Optional[List[TrackingEvent]] = None

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Return the name of the tracking provider."""
        pass

    @abstractmethod
    def track(self) -> List[TrackingEvent]:
        """Fetch and return the tracking events for the parcel.

        Returns:
            A list of TrackingEvent objects representing the parcel's journey

        Raises:
            TrackingError: If tracking fails or tracking number is invalid
        """
        pass

    def is_delivered(self) -> bool:
        """Check if the parcel has been delivered.

        Returns:
            True if the parcel is delivered, False otherwise
        """
        if self._events is None:
            self._events = self.track()

        return any(event.status == TrackingStatus.DELIVERED for event in self._events)

    def get_current_status(self) -> TrackingStatus:
        """Get the current status of the parcel.

        Returns:
            The most recent tracking status
        """
        if self._events is None:
            self._events = self.track()

        if not self._events:
            return TrackingStatus.UNKNOWN

        # Return the status of the most recent event
        return self._events[-1].status

    def get_last_update(self) -> Optional[datetime]:
        """Get the timestamp of the last tracking update.

        Returns:
            The timestamp of the most recent event, or None if no events
        """
        if self._events is None:
            self._events = self.track()

        if not self._events:
            return None

        return self._events[-1].timestamp

    def refresh(self) -> List[TrackingEvent]:
        """Force refresh the tracking data.

        Returns:
            Updated list of tracking events
        """
        self._events = None
        return self.track()

    def __str__(self) -> str:
        """Return a string representation of the tracker."""
        return f"{self.provider_name} Tracker - {self.tracking_number}"


class TrackingError(Exception):
    """Exception raised when tracking fails."""

    def __init__(self, message: str, provider: str = "", tracking_number: str = ""):
        """Initialize the tracking error.

        Args:
            message: The error message
            provider: The name of the tracking provider
            tracking_number: The tracking number that failed
        """
        self.provider = provider
        self.tracking_number = tracking_number
        super().__init__(message)

    def __str__(self) -> str:
        """Return a detailed error message."""
        parts = [super().__str__()]
        if self.provider:
            parts.append(f"Provider: {self.provider}")
        if self.tracking_number:
            parts.append(f"Tracking Number: {self.tracking_number}")
        return " | ".join(parts)

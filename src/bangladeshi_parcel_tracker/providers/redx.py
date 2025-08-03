"""Redx courier tracking implementation."""

import requests
import json
from datetime import datetime
from typing import List, Dict, Any, Optional
from bs4 import BeautifulSoup

from ..base import BaseTracker, TrackingEvent, TrackingStatus, TrackingError


class RedxTracker(BaseTracker):
    """Tracker implementation for Redx courier service."""

    @property
    def provider_name(self) -> str:
        """Return the provider name."""
        return "Redx"

    def track(self) -> List[TrackingEvent]:
        """Track parcel using Redx tracking system.

        Returns:
            List of tracking events

        Raises:
            TrackingError: If tracking fails
        """
        try:
            # Make request to Redx API endpoint
            tracking_data = self._make_request(self.tracking_number)
            
            # Parse the JSON response
            events = self._parse_tracking_data(tracking_data)
            
            if not events:
                raise TrackingError(
                    "No tracking information found. Please check your tracking number.",
                    provider=self.provider_name,
                    tracking_number=self.tracking_number,
                )
            
            self._events = events
            return events

        except requests.exceptions.RequestException as e:
            raise TrackingError(
                f"Failed to connect to Redx tracking service: {str(e)}",
                provider=self.provider_name,
                tracking_number=self.tracking_number,
            )
        except Exception as e:
            raise TrackingError(
                f"Failed to track parcel: {str(e)}",
                provider=self.provider_name,
                tracking_number=self.tracking_number,
            )

    def _make_request(self, tracking_number: str) -> Dict[str, Any]:
        """Make HTTP request to Redx API endpoint.

        Args:
            tracking_number: The tracking number

        Returns:
            JSON response data as dictionary
        """
        url = f"https://api.redx.com.bd/v1/logistics/global-tracking/{tracking_number}"
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "en-US,en;q=0.9",
            "Content-Type": "application/json",
            "Origin": "https://redx.com.bd",
            "Referer": "https://redx.com.bd/",
            "sec-ch-ua": '"Not)A;Brand";v="8", "Chromium";v="138", "Google Chrome";v="138"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"macOS"',
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-site",
        }

        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        
        return response.json()

    def _parse_tracking_data(self, data: Dict[str, Any]) -> List[TrackingEvent]:
        """Parse tracking data from JSON response.

        Args:
            data: JSON response data from Redx API

        Returns:
            List of parsed tracking events
        """
        events = []
        
        # Check if the response has error
        if data.get('isError', True):
            return events
        
        # Extract tracking information from the response
        tracking_list = data.get('tracking', [])
        if not tracking_list:
            return events
        
        for event_data in tracking_list:
            try:
                # Extract event information (prefer English message)
                description = event_data.get('messageEn', '') or event_data.get('messageBn', '') or event_data.get('message', '')
                if not description:
                    continue
                
                # Extract timestamp
                timestamp_str = event_data.get('time', '') or event_data.get('created_at', '') or event_data.get('timestamp', '')
                if not timestamp_str:
                    continue
                
                timestamp = self._parse_timestamp(timestamp_str)
                if not timestamp:
                    continue
                
                # Determine status from status field or description
                status_text = event_data.get('status', '') or event_data.get('action', '') or description
                status = self._determine_status(status_text)
                
                # Extract location if available
                location = event_data.get('location', '') or event_data.get('hub', '') or self._extract_location(description)
                
                event = TrackingEvent(
                    timestamp=timestamp,
                    status=status,
                    location=location if location else None,
                    description=description,
                )
                
                events.append(event)
                
            except Exception as e:
                # Skip malformed events but continue parsing
                continue
        
        # Sort events by timestamp (oldest first)
        events.sort(key=lambda x: x.timestamp)
        return events

    def _parse_timestamp(self, time_text: str) -> Optional[datetime]:
        """Parse timestamp from various formats used in Redx API.
        
        Args:
            time_text: Time text in various formats
            
        Returns:
            Parsed datetime object or None if parsing fails
        """
        if not time_text:
            return None
            
        time_text = time_text.strip()
        
        # List of possible timestamp formats
        formats = [
            "%Y-%m-%d %H:%M:%S",  # 2025-07-19 13:10:00
            "%Y-%m-%dT%H:%M:%S",  # 2025-07-19T13:10:00
            "%Y-%m-%dT%H:%M:%SZ", # 2025-07-19T13:10:00Z
            "%Y-%m-%dT%H:%M:%S.%fZ", # 2025-07-19T13:10:00.123Z
            "%Y-%m-%dT%H:%M:%S.%f", # 2025-07-19T13:10:00.123
            "%d/%m/%Y %H:%M:%S",  # 19/07/2025 13:10:00
            "%d-%m-%Y %H:%M:%S",  # 19-07-2025 13:10:00
            "%d %b %Y %H:%M",     # 19 Jul 2025 13:10
            "%b %d, %Y %I:%M %p", # Jul 19, 2025 1:10 PM
            "%d %B %Y, %I:%M %p", # 19 July 2025, 1:10 PM
        ]
        
        for fmt in formats:
            try:
                return datetime.strptime(time_text, fmt)
            except ValueError:
                continue
        
        return None

    def _determine_status(self, status_text: str) -> TrackingStatus:
        """Determine tracking status from status text.
        
        Args:
            status_text: Status text from API response
            
        Returns:
            Appropriate TrackingStatus
        """
        if not status_text:
            return TrackingStatus.UNKNOWN
            
        status_lower = status_text.lower()
        
        # Redx-specific status codes from API
        if status_lower in ["delivery-payment-collected", "delivered"]:
            return TrackingStatus.DELIVERED
        elif status_lower in ["delivery-in-progress"]:
            return TrackingStatus.OUT_FOR_DELIVERY
        elif status_lower in ["ready-for-delivery"]:
            return TrackingStatus.PICKED_UP  # Ready for delivery means it's in the system
        elif status_lower in ["pickup-pending"]:
            return TrackingStatus.PENDING
        elif status_lower in ["line-haul-in-progress", "line-haul-trip-started", "line-haul-bulk-dropped", "bulk-transfer-received"]:
            return TrackingStatus.IN_TRANSIT
        elif status_lower in ["received-from-seller", "received-from-hub", "received-transfer"]:
            return TrackingStatus.IN_TRANSIT
        elif status_lower in ["dispatched-to-line-haul", "trip-started", "bulk-dropped", "dispatched-to-agent"]:
            return TrackingStatus.IN_TRANSIT
        elif status_lower in ["delivery-failed", "failed-delivery"]:
            return TrackingStatus.FAILED_DELIVERY
        elif status_lower in ["returned", "return-completed"]:
            return TrackingStatus.RETURNED
        elif status_lower in ["cancelled", "cancel"]:
            return TrackingStatus.CANCELLED
        
        # Fallback to message-based determination
        elif "delivered successfully" in status_lower or "delivery completed" in status_lower:
            return TrackingStatus.DELIVERED
        elif "on the way to delivery" in status_lower or "out for delivery" in status_lower:
            return TrackingStatus.OUT_FOR_DELIVERY
        elif "picked up" in status_lower or "pickup" in status_lower:
            return TrackingStatus.PICKED_UP
        elif "created successfully" in status_lower or "parcel is created" in status_lower:
            return TrackingStatus.PENDING
        elif "ready for transfer" in status_lower or "vehicle has left" in status_lower or "carrying vehicle" in status_lower:
            return TrackingStatus.IN_TRANSIT
        elif "received in" in status_lower or "unloaded" in status_lower or "has reached" in status_lower:
            return TrackingStatus.IN_TRANSIT
        elif any(keyword in status_lower for keyword in ["transit", "transfer", "hub", "vehicle", "carrying", "left", "reached"]):
            return TrackingStatus.IN_TRANSIT
        elif any(keyword in status_lower for keyword in ["assigned", "assigned for delivery"]):
            return TrackingStatus.OUT_FOR_DELIVERY
        elif any(keyword in status_lower for keyword in ["requested", "new order", "received order", "confirmed", "booked"]):
            return TrackingStatus.PENDING
        elif any(keyword in status_lower for keyword in ["cancelled", "cancel"]):
            return TrackingStatus.CANCELLED
        elif any(keyword in status_lower for keyword in ["failed", "unsuccessful", "attempt failed", "delivery failed"]):
            return TrackingStatus.FAILED_DELIVERY
        elif any(keyword in status_lower for keyword in ["returned", "return"]):
            return TrackingStatus.RETURNED
        else:
            return TrackingStatus.UNKNOWN

    def _extract_location(self, description: str) -> Optional[str]:
        """Extract location information from description.
        
        Args:
            description: Event description
            
        Returns:
            Extracted location or None
        """
        import re
        
        # Look for location patterns in description
        location_patterns = [
            r"at\s+([^,\n]+)",
            r"from\s+([^,\n]+)",
            r"to\s+([^,\n]+)",
            r"in\s+([^,\n]+)",
            r"hub:\s*([^,\n]+)",
            r"location:\s*([^,\n]+)",
        ]
        
        for pattern in location_patterns:
            match = re.search(pattern, description, re.IGNORECASE)
            if match:
                location = match.group(1).strip()
                if location and len(location) > 2:  # Avoid single characters
                    return location
        
        return None

"""Pathao courier tracking implementation."""

import requests
import json
from datetime import datetime
from typing import List, Optional, Dict, Any
import re
from bs4 import BeautifulSoup

from ..base import BaseTracker, TrackingEvent, TrackingStatus, TrackingError


class PathaoTracker(BaseTracker):
    """Tracker implementation for Pathao courier service."""

    def __init__(self, tracking_number: str, phone: str = ""):
        """Initialize Pathao tracker with tracking number and phone.
        
        Args:
            tracking_number: The tracking/consignment number
            phone: Phone number associated with the order (required for Pathao)
        """
        super().__init__(tracking_number)
        self.phone = phone.strip()
        if not self.phone:
            raise ValueError("Phone number is required for Pathao tracking")

    @property
    def provider_name(self) -> str:
        """Return the provider name."""
        return "Pathao"

    def track(self) -> List[TrackingEvent]:
        """Track parcel using Pathao tracking system.

        Returns:
            List of tracking events

        Raises:
            TrackingError: If tracking fails
        """
        try:
            # Make request to Pathao API endpoint
            tracking_data = self._make_request(self.tracking_number, self.phone)
            
            # Parse the JSON response
            events = self._parse_tracking_data(tracking_data)
            
            if not events:
                raise TrackingError(
                    "No tracking information found. Please check your tracking number and phone number.",
                    provider=self.provider_name,
                    tracking_number=self.tracking_number,
                )
            
            self._events = events
            return events

        except requests.exceptions.RequestException as e:
            raise TrackingError(
                f"Failed to connect to Pathao tracking service: {str(e)}",
                provider=self.provider_name,
                tracking_number=self.tracking_number,
            )
        except Exception as e:
            raise TrackingError(
                f"Failed to track parcel: {str(e)}",
                provider=self.provider_name,
                tracking_number=self.tracking_number,
            )

    def _make_request(self, tracking_number: str, phone: str) -> Dict[str, Any]:
        """Make HTTP request to Pathao API endpoint.

        Args:
            tracking_number: The tracking number
            phone: Phone number associated with the order

        Returns:
            JSON response data as dictionary
        """
        url = "https://merchant.pathao.com/api/v1/user/tracking"
        
        headers = {
            'accept': 'application/json, text/plain, */*',
            'accept-language': 'en-US,en-GB;q=0.9,en;q=0.8,bn;q=0.7',
            'content-type': 'application/json',
            'dnt': '1',
            'origin': 'https://merchant.pathao.com',
            'priority': 'u=1, i',
            'referer': f'https://merchant.pathao.com/tracking?consignment_id={tracking_number}&phone={phone}',
            'sec-ch-ua': '"Not)A;Brand";v="8", "Chromium";v="138", "Google Chrome";v="138"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"macOS"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-origin',
            'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36'
        }
        
        payload = {
            "phone_no": phone,
            "consignment_id": tracking_number
        }
        
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        
        return response.json()

    def _parse_tracking_data(self, data: Dict[str, Any]) -> List[TrackingEvent]:
        """Parse tracking data from JSON response.

        Args:
            data: JSON response data from Pathao API

        Returns:
            List of parsed tracking events
        """
        events = []
        
        # Check if the response indicates success
        if data.get('type') != 'success' and not data.get('success', False):
            return events
        
        # Extract tracking information from the response
        tracking_info = data.get('data', {})
        if not tracking_info:
            return events
        
        # Get the order information
        order = tracking_info.get('order', {})
        logs = tracking_info.get('log', [])
        
        # Parse logs/events from the response
        for log_entry in logs:
            try:
                description = log_entry.get('desc', '') or log_entry.get('message', '') or log_entry.get('description', '')
                if not description:
                    continue
                
                timestamp_str = log_entry.get('created_at', '') or log_entry.get('timestamp', '')
                if not timestamp_str:
                    continue
                
                timestamp = self._parse_timestamp(timestamp_str)
                if not timestamp:
                    continue
                
                # Determine status from description
                status = self._determine_status_from_text(description)
                
                # Extract location from notes or description
                location = log_entry.get('location', '') or log_entry.get('notes', '') or self._extract_location(description)
                if location and location.strip():
                    location = location.strip()
                else:
                    location = None
                
                event = TrackingEvent(
                    timestamp=timestamp,
                    status=status,
                    location=location,
                    description=description,
                )
                
                events.append(event)
                
            except Exception as e:
                continue
        
        # Add final delivery status event if delivered
        if order:
            transfer_status = order.get('transfer_status', '')
            transfer_updated_at = order.get('transfer_status_updated_at', '')
            
            if transfer_status and transfer_updated_at and transfer_status.lower() == 'delivered':
                timestamp = self._parse_timestamp(transfer_updated_at)
                if timestamp:
                    # Check if we already have a delivered event at this time
                    has_delivered = any(
                        event.timestamp == timestamp and event.status == TrackingStatus.DELIVERED 
                        for event in events
                    )
                    
                    if not has_delivered:
                        events.append(TrackingEvent(
                            timestamp=timestamp,
                            status=TrackingStatus.DELIVERED,
                            location=None,
                            description="Package delivered successfully"
                        ))
        
        # Sort events by timestamp (oldest first)
        events.sort(key=lambda x: x.timestamp)
        return events

    def _parse_timestamp(self, time_text: str) -> Optional[datetime]:
        """Parse timestamp from various formats used in Pathao API.
        
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
            "%b %d, %Y %I:%M %p", # Jul 19, 2025 1:10 PM
            "%b %d, %Y %H:%M",    # Jul 19, 2025 13:10
            "%d/%m/%Y %H:%M:%S",  # 19/07/2025 13:10:00
            "%d-%m-%Y %H:%M:%S",  # 19-07-2025 13:10:00
        ]
        
        for fmt in formats:
            try:
                return datetime.strptime(time_text, fmt)
            except ValueError:
                continue
        
        return None

    def _determine_status_from_text(self, status_text: str) -> TrackingStatus:
        """Determine tracking status from status text.
        
        Args:
            status_text: Status text from API response
            
        Returns:
            Appropriate TrackingStatus
        """
        if not status_text:
            return TrackingStatus.UNKNOWN
            
        status_lower = status_text.lower()
        
        # Status determination based on keywords
        if any(keyword in status_lower for keyword in ["delivered", "delivery completed", "delivered successfully"]):
            return TrackingStatus.DELIVERED
        elif any(keyword in status_lower for keyword in ["assigned", "out for delivery", "on the way"]):
            return TrackingStatus.OUT_FOR_DELIVERY
        elif any(keyword in status_lower for keyword in ["reached", "arrived", "hub", "transit", "in transit"]):
            return TrackingStatus.IN_TRANSIT
        elif any(keyword in status_lower for keyword in ["pickup", "collected", "picked up", "picked"]):
            return TrackingStatus.PICKED_UP
        elif any(keyword in status_lower for keyword in ["requested", "new order", "received", "pending", "confirmed"]):
            return TrackingStatus.PENDING
        elif any(keyword in status_lower for keyword in ["cancelled", "cancel"]):
            return TrackingStatus.CANCELLED
        elif any(keyword in status_lower for keyword in ["failed", "unsuccessful", "attempt failed", "delivery failed"]):
            return TrackingStatus.FAILED_DELIVERY
        elif any(keyword in status_lower for keyword in ["returned", "return"]):
            return TrackingStatus.RETURNED
        else:
            return TrackingStatus.UNKNOWN

    def _determine_status(self, description: str, border_div=None) -> TrackingStatus:
        """Determine tracking status from description (legacy method for backward compatibility).
        
        Args:
            description: Event description text
            border_div: BeautifulSoup element with border styling (unused in API version)
            
        Returns:
            Appropriate TrackingStatus
        """
        return self._determine_status_from_text(description)

    def _extract_location(self, description: str) -> Optional[str]:
        """Extract location information from description.
        
        Args:
            description: Event description
            
        Returns:
            Extracted location or None
        """
        # Look for location patterns in parentheses or after "at"
        location_patterns = [
            r"at\s+([^,]+)",
            r"from\s+([^,]+)",
            r"to\s+([^,]+)",
            r"in\s+([^,]+)"
        ]
        
        for pattern in location_patterns:
            match = re.search(pattern, description, re.IGNORECASE)
            if match:
                location = match.group(1).strip()
                if location and len(location) > 2:  # Avoid single characters
                    return location
        
        return None

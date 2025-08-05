"""Sundarban courier tracking implementation."""

import requests
from datetime import datetime
from typing import List, Dict, Any, Optional

from ..base import BaseTracker, TrackingEvent, TrackingStatus, TrackingError


class SundarbanTracker(BaseTracker):
    """Tracker implementation for Sundarban courier service."""

    @property
    def provider_name(self) -> str:
        """Return the provider name."""
        return "Sundarban"

    def track(self) -> List[TrackingEvent]:
        """Track parcel using Sundarban tracking system.

        Returns:
            List of tracking events

        Raises:
            TrackingError: If tracking fails
        """
        try:
            # Make request to Sundarban API endpoint
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
                f"Failed to connect to Sundarban tracking service: {str(e)}",
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
        """Make HTTP request to Sundarban API endpoint.

        Args:
            tracking_number: The tracking number

        Returns:
            JSON response data as dictionary
        """
        url = "https://tracking.sundarbancourierltd.com/Home/getDatabyCN"
        
        headers = {
            "accept": "application/json, text/javascript, */*; q=0.01",
            "content-type": "application/json;charset=UTF-8",
            "key": "CzbZcWnwf7TNTzluD9rxyXCUqzN4xOhs",
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36",
            "Accept-Language": "en-US,en;q=0.9",
            "Origin": "https://tracking.sundarbancourierltd.com",
            "Referer": "https://tracking.sundarbancourierltd.com/",
            "sec-ch-ua": '"Not)A;Brand";v="8", "Chromium";v="138", "Google Chrome";v="138"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"macOS"',
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-origin",
            "X-Requested-With": "XMLHttpRequest",
        }

        payload = {
            "selectedtypes": "cnno",
            "selectedtimes": "7",
            "inputvalue": tracking_number
        }

        response = requests.post(url, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        
        return response.json()

    def _parse_tracking_data(self, data: Dict[str, Any]) -> List[TrackingEvent]:
        """Parse tracking data from JSON response.

        Args:
            data: JSON response data from Sundarban API

        Returns:
            List of parsed tracking events
        """
        events = []
        
        # Check if the response contains tracking data
        if not isinstance(data, dict):
            return events
        
        # Look for tracking information in various possible response formats
        # The exact structure may vary, so we'll check common patterns
        tracking_data = []
        
        if "data" in data:
            tracking_data = data["data"] if isinstance(data["data"], list) else [data["data"]]
        elif "trackingInfo" in data:
            tracking_data = data["trackingInfo"] if isinstance(data["trackingInfo"], list) else [data["trackingInfo"]]
        elif "tracking" in data:
            tracking_data = data["tracking"] if isinstance(data["tracking"], list) else [data["tracking"]]
        elif isinstance(data, list):
            tracking_data = data
        else:
            # If it's a single object with tracking details
            tracking_data = [data]
        
        for item in tracking_data:
            if not isinstance(item, dict):
                continue
            
            # Extract tracking events from the item
            events_data = []
            
            # Check for various possible event array names
            for key in ["events", "trackingEvents", "history", "tracking_history", "statusHistory"]:
                if key in item and isinstance(item[key], list):
                    events_data = item[key]
                    break
            
            # If no events array found, treat the item itself as an event
            if not events_data and any(key in item for key in ["status", "time", "date", "timestamp", "description", "location"]):
                events_data = [item]
            
            for event_data in events_data:
                if not isinstance(event_data, dict):
                    continue
                
                try:
                    # Extract timestamp
                    timestamp = self._extract_timestamp(event_data)
                    if not timestamp:
                        continue
                    
                    # Extract description and status
                    description = self._extract_description(event_data)
                    if not description:
                        continue
                    
                    # Determine status from status field or description
                    status = self._determine_status(event_data, description)
                    
                    # Extract location if available
                    location = self._extract_location(event_data, description)
                    
                    event = TrackingEvent(
                        timestamp=timestamp,
                        status=status,
                        location=location,
                        description=description,
                    )
                    
                    events.append(event)
                    
                except Exception as e:
                    # Skip malformed events but continue parsing
                    continue
        
        # Sort events by timestamp (oldest first)
        events.sort(key=lambda x: x.timestamp)
        return events

    def _extract_timestamp(self, event_data: Dict[str, Any]) -> Optional[datetime]:
        """Extract timestamp from event data.
        
        Args:
            event_data: Event data dictionary
            
        Returns:
            Parsed datetime object or None
        """
        # Try various timestamp field names
        timestamp_fields = ["timestamp", "time", "date", "dateTime", "created_at", "updated_at", "eventTime"]
        
        for field in timestamp_fields:
            if field in event_data and event_data[field]:
                timestamp_str = str(event_data[field]).strip()
                parsed_time = self._parse_timestamp(timestamp_str)
                if parsed_time:
                    return parsed_time
        
        return None

    def _extract_description(self, event_data: Dict[str, Any]) -> Optional[str]:
        """Extract description from event data.
        
        Args:
            event_data: Event data dictionary
            
        Returns:
            Description string or None
        """
        # Try various description field names
        description_fields = ["description", "message", "status", "statusText", "remarks", "details", "note"]
        
        for field in description_fields:
            if field in event_data and event_data[field]:
                description = str(event_data[field]).strip()
                if description:
                    return description
        
        return None

    def _extract_location(self, event_data: Dict[str, Any], description: str = "") -> Optional[str]:
        """Extract location from event data or description.
        
        Args:
            event_data: Event data dictionary
            description: Event description
            
        Returns:
            Location string or None
        """
        # Try various location field names
        location_fields = ["location", "hub", "office", "branch", "area", "city", "place"]
        
        for field in location_fields:
            if field in event_data and event_data[field]:
                location = str(event_data[field]).strip()
                if location:
                    return location
        
        # Try to extract location from description
        if description:
            import re
            location_patterns = [
                r"at\s+([^,\n]+)",
                r"from\s+([^,\n]+)",
                r"to\s+([^,\n]+)",
                r"in\s+([^,\n]+)", 
                r"hub:\s*([^,\n]+)",
                r"office:\s*([^,\n]+)",
                r"branch:\s*([^,\n]+)",
            ]
            
            for pattern in location_patterns:
                match = re.search(pattern, description, re.IGNORECASE)
                if match:
                    location = match.group(1).strip()
                    if location and len(location) > 2:
                        return location
        
        return None

    def _parse_timestamp(self, time_text: str) -> Optional[datetime]:
        """Parse timestamp from various formats.
        
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
            "%d-%b-%Y %H:%M:%S",  # 19-Jul-2025 13:10:00
            "%d/%b/%Y %H:%M:%S",  # 19/Jul/2025 13:10:00
            "%Y/%m/%d %H:%M:%S",  # 2025/07/19 13:10:00
            "%d.%m.%Y %H:%M:%S",  # 19.07.2025 13:10:00
        ]
        
        for fmt in formats:
            try:
                return datetime.strptime(time_text, fmt)
            except ValueError:
                continue
        
        return None

    def _determine_status(self, event_data: Dict[str, Any], description: str) -> TrackingStatus:
        """Determine tracking status from event data and description.
        
        Args:
            event_data: Event data dictionary
            description: Event description
            
        Returns:
            Appropriate TrackingStatus
        """
        # Check if there's a specific status field
        status_text = ""
        if "status" in event_data:
            status_text = str(event_data["status"]).lower()
        elif "statusCode" in event_data:
            status_text = str(event_data["statusCode"]).lower()
        
        # Combine status text with description for analysis
        combined_text = f"{status_text} {description}".lower()
        
        # Sundarban-specific status determination
        if any(keyword in combined_text for keyword in ["delivered", "delivery completed", "successfully delivered", "delivered successfully"]):
            return TrackingStatus.DELIVERED
        elif any(keyword in combined_text for keyword in ["out for delivery", "on the way", "assigned for delivery", "delivery in progress"]):
            return TrackingStatus.OUT_FOR_DELIVERY
        elif any(keyword in combined_text for keyword in ["picked up", "pickup completed", "collected", "received from sender"]):
            return TrackingStatus.PICKED_UP
        elif any(keyword in combined_text for keyword in ["created", "booked", "order placed", "parcel received", "pending pickup", "pickup pending"]):
            return TrackingStatus.PENDING
        elif any(keyword in combined_text for keyword in ["in transit", "on the way", "transferred", "dispatched", "loaded", "unloaded", "reached hub", "left hub"]):
            return TrackingStatus.IN_TRANSIT
        elif any(keyword in combined_text for keyword in ["failed delivery", "delivery failed", "unsuccessful delivery", "customer not available", "address not found"]):
            return TrackingStatus.FAILED_DELIVERY
        elif any(keyword in combined_text for keyword in ["returned", "return completed", "returned to sender"]):
            return TrackingStatus.RETURNED
        elif any(keyword in combined_text for keyword in ["cancelled", "canceled", "cancel"]):
            return TrackingStatus.CANCELLED
        else:
            return TrackingStatus.UNKNOWN

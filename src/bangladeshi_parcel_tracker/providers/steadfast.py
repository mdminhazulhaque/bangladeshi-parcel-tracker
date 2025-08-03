"""Steadfast courier tracking implementation."""

import requests
import json
from datetime import datetime
from typing import List, Dict, Any, Optional
from bs4 import BeautifulSoup

from ..base import BaseTracker, TrackingEvent, TrackingStatus, TrackingError


class SteadfastTracker(BaseTracker):
    """Tracker implementation for Steadfast courier service."""

    @property
    def provider_name(self) -> str:
        """Return the provider name."""
        return "Steadfast"

    def track(self) -> List[TrackingEvent]:
        """Track parcel using Steadfast tracking system.

        Returns:
            List of tracking events

        Raises:
            TrackingError: If tracking fails
        """
        try:
            # Make request to Steadfast API endpoint
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
                f"Failed to connect to Steadfast tracking service: {str(e)}",
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
        """Make HTTP request to Steadfast tracking endpoint.

        Args:
            tracking_number: The tracking number

        Returns:
            JSON response data
        """
        url = f"https://steadfast.com.bd/track/consignment/{tracking_number}"
        
        headers = {
            'accept': 'application/json, text/plain, */*',
            'accept-language': 'en-US,en;q=0.9,bn;q=0.8',
            'cache-control': 'no-cache',
            'dnt': '1',
            'pragma': 'no-cache',
            'sec-ch-ua': '"Not)A;Brand";v="8", "Chromium";v="138", "Google Chrome";v="138"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"macOS"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-origin',
            'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36'
        }

        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        
        return response.json()

    def _parse_tracking_data(self, data: List[Any]) -> List[TrackingEvent]:
        """Parse tracking data from JSON response.

        Args:
            data: JSON response data from Steadfast API

        Returns:
            List of parsed tracking events
        """
        events = []
        
        if not data or len(data) < 2:
            return events
        
        # First element contains consignment info
        consignment_info = data[0]
        
        # Second element contains tracking events array
        tracking_events = data[1] if len(data) > 1 else []
        
        for event_data in tracking_events:
            try:
                # Extract event information
                description = event_data.get('text', '')
                if not description:
                    continue
                
                # Extract timestamp
                timestamp_str = event_data.get('created_at', '')
                if not timestamp_str:
                    continue
                
                timestamp = self._parse_timestamp(timestamp_str)
                if not timestamp:
                    continue
                
                # Determine status from tracking_type and description
                tracking_type = event_data.get('tracking_type', 0)
                status = self._determine_status(tracking_type, description)
                
                # Extract location from description or deliveryman info
                location = self._extract_location(event_data, description)
                
                event = TrackingEvent(
                    timestamp=timestamp,
                    status=status,
                    location=location,
                    description=description,
                )
                
                events.append(event)
                
            except Exception as e:
                # Skip this event if parsing fails
                continue
        
        # Reverse the list to get chronological order (oldest first)
        events.reverse()
        
        return events

    def _parse_timestamp(self, timestamp_str: str) -> Optional[datetime]:
        """Parse timestamp from ISO format.
        
        Args:
            timestamp_str: Timestamp string in ISO format
            
        Returns:
            Parsed datetime object or None if parsing fails
        """
        if not timestamp_str:
            return None
            
        try:
            # Parse ISO format: 2025-07-25T10:52:11.000000Z
            return datetime.fromisoformat(timestamp_str.replace('Z', '+00:00')).replace(tzinfo=None)
        except ValueError:
            return None

    def _determine_status(self, tracking_type: int, description: str) -> TrackingStatus:
        """Determine tracking status from tracking type and description.
        
        Args:
            tracking_type: Numeric tracking type from API
            description: Event description text
            
        Returns:
            Appropriate TrackingStatus
        """
        description_lower = description.lower()
        
        # Map tracking types to status (based on observed data)
        if tracking_type == 18 or 'marked as delivered' in description_lower or 'delivered' in description_lower:
            return TrackingStatus.DELIVERED
        elif tracking_type == 11 or 'assigned to rider' in description_lower:
            return TrackingStatus.OUT_FOR_DELIVERY
        elif tracking_type == 3:
            if 'received at' in description_lower:
                return TrackingStatus.IN_TRANSIT
            elif 'sent to' in description_lower:
                return TrackingStatus.IN_TRANSIT
        elif tracking_type == 10 or 'pending' in description_lower:
            return TrackingStatus.PENDING
        
        # General status determination based on keywords
        if any(keyword in description_lower for keyword in ['delivered', 'delivery completed']):
            return TrackingStatus.DELIVERED
        elif any(keyword in description_lower for keyword in ['assigned', 'rider', 'out for delivery']):
            return TrackingStatus.OUT_FOR_DELIVERY
        elif any(keyword in description_lower for keyword in ['received', 'sent', 'dispatch', 'transit', 'warehouse', 'hub']):
            return TrackingStatus.IN_TRANSIT
        elif any(keyword in description_lower for keyword in ['pending', 'created', 'booked']):
            return TrackingStatus.PENDING
        elif any(keyword in description_lower for keyword in ['cancelled', 'cancel']):
            return TrackingStatus.CANCELLED
        elif any(keyword in description_lower for keyword in ['failed', 'unsuccessful', 'attempt failed']):
            return TrackingStatus.FAILED_DELIVERY
        elif any(keyword in description_lower for keyword in ['returned', 'return']):
            return TrackingStatus.RETURNED
        else:
            return TrackingStatus.UNKNOWN

    def _extract_location(self, event_data: Dict[str, Any], description: str) -> Optional[str]:
        """Extract location information from event data and description.
        
        Args:
            event_data: Full event data from API
            description: Event description text
            
        Returns:
            Extracted location or None
        """
        # Try to get deliveryman info
        deliveryman = event_data.get('deliveryman')
        if deliveryman and deliveryman.get('name'):
            return f"Rider: {deliveryman['name']}"
        
        # Extract location from description
        if 'received at' in description.lower():
            # Extract hub/warehouse name
            parts = description.split('received at')
            if len(parts) > 1:
                location = parts[1].strip().rstrip('.')
                return location
        elif 'sent to' in description.lower():
            # Extract destination hub/warehouse name
            parts = description.split('sent to')
            if len(parts) > 1:
                # Remove dispatch ID part if present
                location = parts[1].split('.')[0].strip()
                return location
        
        return None

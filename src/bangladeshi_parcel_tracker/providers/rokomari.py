"""Rokomari courier tracking implementation."""

import requests
import base64
import urllib.parse
from datetime import datetime
from typing import List, Dict, Any, Optional
from bs4 import BeautifulSoup
import re

from ..base import BaseTracker, TrackingEvent, TrackingStatus, TrackingError


class RokomariTracker(BaseTracker):
    """Tracker implementation for Rokomari courier service."""

    def __init__(self, tracking_number: str, phone: str = ""):
        """Initialize Rokomari tracker with tracking number and phone.
        
        Args:
            tracking_number: The order/tracking number
            phone: Phone number associated with the order (required for Rokomari)
        """
        super().__init__(tracking_number)
        self.phone = phone.strip()
        if not self.phone:
            raise ValueError("Phone number is required for Rokomari tracking")

    @property
    def provider_name(self) -> str:
        """Return the provider name."""
        return "Rokomari"

    def track(self) -> List[TrackingEvent]:
        """Track parcel using Rokomari tracking system.

        Returns:
            List of tracking events

        Raises:
            TrackingError: If tracking fails
        """
        try:
            # Make request to Rokomari tracking page
            html_content = self._make_request(self.tracking_number, self.phone)
            
            # Parse the HTML response
            events = self._parse_tracking_data(html_content)
            
            if not events:
                raise TrackingError(
                    "No tracking information found. Please check your order ID and phone number.",
                    provider=self.provider_name,
                    tracking_number=self.tracking_number,
                )
            
            self._events = events
            return events

        except requests.exceptions.RequestException as e:
            raise TrackingError(
                f"Failed to connect to Rokomari tracking service: {str(e)}",
                provider=self.provider_name,
                tracking_number=self.tracking_number,
            )
        except Exception as e:
            raise TrackingError(
                f"Failed to track parcel: {str(e)}",
                provider=self.provider_name,
                tracking_number=self.tracking_number,
            )

    def _encode_phone(self, phone: str) -> str:
        """Encode phone number to base64 format expected by Rokomari.
        
        Args:
            phone: Phone number (with or without leading zero)
            
        Returns:
            Base64 encoded phone number without leading zero and country code
        """
        # Remove leading zero and country code (88) if present
        clean_phone = phone.lstrip('0')
        if clean_phone.startswith('88'):
            clean_phone = clean_phone[2:]
        
        # Remove any remaining leading zeros
        clean_phone = clean_phone.lstrip('0')
        
        # Encode to base64
        encoded_bytes = base64.b64encode(clean_phone.encode('utf-8'))
        encoded_phone = encoded_bytes.decode('utf-8')
        
        # URL encode the base64 string
        return urllib.parse.quote(encoded_phone)

    def _make_request(self, tracking_number: str, phone: str) -> str:
        """Make HTTP request to Rokomari tracking endpoint.

        Args:
            tracking_number: The order/tracking number
            phone: Phone number associated with the order

        Returns:
            HTML content as string
        """
        # Encode the phone number
        encoded_phone = self._encode_phone(phone)
        
        url = f"https://www.rokomari.com/ordertrack?orderId={tracking_number}&countryISOCode=BD&phn={encoded_phone}"
        
        headers = {
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'accept-language': 'en-US,en;q=0.9,bn;q=0.8',
            'cache-control': 'no-cache',
            'dnt': '1',
            'pragma': 'no-cache',
            'sec-ch-ua': '"Not)A;Brand";v="8", "Chromium";v="138", "Google Chrome";v="138"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"macOS"',
            'sec-fetch-dest': 'document',
            'sec-fetch-mode': 'navigate',
            'sec-fetch-site': 'none',
            'sec-fetch-user': '?1',
            'upgrade-insecure-requests': '1',
            'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36'
        }

        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        
        return response.text

    def _parse_tracking_data(self, html_content: str) -> List[TrackingEvent]:
        """Parse tracking data from HTML response.

        Args:
            html_content: HTML content from tracking page

        Returns:
            List of parsed tracking events
        """
        soup = BeautifulSoup(html_content, 'html.parser')
        events = []

        # Find all step items (tracking events)
        step_items = soup.find_all('div', class_='step-item')
        
        for step_item in step_items:
            try:
                # Extract title
                title_elem = step_item.find('h5', class_='step-item__content-title')
                if not title_elem:
                    continue
                title = title_elem.get_text(strip=True)
                
                # Extract hidden date input
                date_input = step_item.find('input', type='hidden', id=lambda x: x and 'js--date-' in x)
                if not date_input:
                    continue
                    
                date_value = date_input.get('value', '')
                if not date_value:
                    continue
                
                # Parse timestamp
                timestamp = self._parse_timestamp(date_value)
                if not timestamp:
                    continue
                
                # Extract description from message content
                message_elem = step_item.find('div', class_='step-item__content-message')
                description = title
                if message_elem:
                    # Get the first paragraph text
                    first_p = message_elem.find('p')
                    if first_p:
                        desc_text = first_p.get_text(strip=True)
                        if desc_text:
                            description = desc_text
                
                # Extract location from description or other elements
                location = self._extract_location(description)
                
                # Find the status input that precedes this step item
                status_input = None
                prev_sibling = step_item.find_previous_sibling()
                while prev_sibling:
                    if prev_sibling.name == 'input' and prev_sibling.get('class') == ['js--order-status']:
                        status_input = prev_sibling
                        break
                    prev_sibling = prev_sibling.find_previous_sibling()
                
                status_code = status_input.get('value', '') if status_input else ''
                status = self._determine_status(title, status_code)
                
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
        """Parse timestamp from various formats.
        
        Args:
            timestamp_str: Timestamp string
            
        Returns:
            Parsed datetime object or None if parsing fails
        """
        if not timestamp_str:
            return None
            
        # Common timestamp formats from Rokomari
        formats = [
            '%Y-%m-%dT%H:%M:%S',           # 2025-07-21T15:54:57
            '%Y-%m-%dT%H:%M:%S.%f',        # 2025-07-13T13:16:24.000000001
            '%Y-%m-%d %H:%M:%S',           # 2025-07-21 15:54:57
        ]
        
        for fmt in formats:
            try:
                return datetime.strptime(timestamp_str, fmt)
            except ValueError:
                continue
        
        return None

    def _determine_status(self, title: str, status_code: str) -> TrackingStatus:
        """Determine tracking status from title and status code.
        
        Args:
            title: Event title
            status_code: Hidden status code from HTML
            
        Returns:
            Appropriate TrackingStatus enum value
        """
        title_lower = title.lower()
        status_code_upper = status_code.upper()
        
        # Map status codes to tracking status
        if status_code_upper == 'COMPLETED' or 'delivered' in title_lower:
            return TrackingStatus.DELIVERED
        elif status_code_upper == 'SHIPPED' or 'handover to courier' in title_lower:
            return TrackingStatus.OUT_FOR_DELIVERY
        elif status_code_upper == 'ON_SHIPPING' or 'ready to ship' in title_lower:
            return TrackingStatus.PICKED_UP
        elif status_code_upper == 'NORMAL' or 'processing' in title_lower:
            return TrackingStatus.IN_TRANSIT
        elif status_code_upper == 'HALTED' or 'halt' in title_lower:
            return TrackingStatus.PENDING
        elif status_code_upper == 'APPROVED' or 'approved' in title_lower:
            return TrackingStatus.PENDING
        elif status_code_upper == 'PROCESSING' or 'placed' in title_lower:
            return TrackingStatus.PENDING
        
        return TrackingStatus.UNKNOWN

    def _extract_location(self, description: str) -> Optional[str]:
        """Extract location information from description.
        
        Args:
            description: Event description text
            
        Returns:
            Extracted location or None
        """
        if not description:
            return None
            
        # Look for courier/delivery person information
        courier_match = re.search(r'(.*?)\s*\(\d{11}\)', description)
        if courier_match:
            courier_name = courier_match.group(1).strip()
            if courier_name and not courier_name.startswith('আপনার'):
                return f"Courier: {courier_name}"
        
        # Look for general location patterns
        location_patterns = [
            r'(ঢাকা|চট্টগ্রাম|সিলেট|রাজশাহী|খুলনা|বরিশাল|রংপুর|ময়মনসিংহ)',
            r'(Dhaka|Chittagong|Sylhet|Rajshahi|Khulna|Barisal|Rangpur|Mymensingh)',
        ]
        
        for pattern in location_patterns:
            match = re.search(pattern, description, re.IGNORECASE)
            if match:
                return match.group(1)
        
        return None

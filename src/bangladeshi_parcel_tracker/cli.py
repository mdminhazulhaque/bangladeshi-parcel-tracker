"""Command Line Interface for Bangladeshi Parcel Tracker."""

import argparse
import sys
from typing import Optional

from .providers import RedxTracker, SteadfastTracker, PathaoTracker, RokomariTracker, SundarbanTracker
from .base import TrackingError


def create_parser() -> argparse.ArgumentParser:
    """Create the argument parser for the CLI."""
    parser = argparse.ArgumentParser(
        prog="bangladeshi-parcel-tracker",
        description="Track parcels from Bangladeshi courier services",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Track with Redx
  bangladeshi-parcel-tracker redx RDX123456789
  
  # Track with Steadfast
  bangladeshi-parcel-tracker steadfast SF987654321
  
  # Track with Pathao (requires phone number)
  bangladeshi-parcel-tracker pathao PA456789123 --phone 01707170321
  
  # Track with Rokomari
  bangladeshi-parcel-tracker rokomari RK789123456
  
  # Track with Sundarban
  bangladeshi-parcel-tracker sundarban 70003000778899
  
  # Show only delivery status
  bangladeshi-parcel-tracker redx RDX123456789 --status-only
  
  # Show detailed timeline
  bangladeshi-parcel-tracker steadfast SF987654321 --detailed
        """,
    )

    parser.add_argument(
        "provider",
        choices=["redx", "steadfast", "pathao", "rokomari", "sundarban"],
        help="Courier service provider",
    )

    parser.add_argument(
        "tracking_number", help="Tracking/consignment number for the parcel"
    )

    parser.add_argument(
        "--phone",
        "-p",
        help="Phone number (required for Pathao and Rokomari tracking)",
    )

    parser.add_argument(
        "--status-only",
        "-s",
        action="store_true",
        help="Show only the current delivery status",
    )

    parser.add_argument(
        "--detailed",
        "-d",
        action="store_true",
        help="Show detailed timeline with all events",
    )

    parser.add_argument(
        "--json",
        "-j",
        action="store_true",
        help="Output results in JSON format",
    )

    parser.add_argument(
        "--version", "-v", action="version", version="%(prog)s 0.1.0"
    )

    return parser


def get_tracker(provider: str, tracking_number: str, phone: str = ""):
    """Get the appropriate tracker instance for the provider."""
    trackers = {
        "redx": RedxTracker,
        "steadfast": SteadfastTracker,
        "pathao": PathaoTracker,
        "rokomari": RokomariTracker,
        "sundarban": SundarbanTracker,
    }

    tracker_class = trackers.get(provider.lower())
    if not tracker_class:
        raise ValueError(f"Unsupported provider: {provider}")

    # Pathao and Rokomari require phone number
    if provider.lower() == "pathao":
        if not phone:
            raise ValueError("Phone number is required for Pathao tracking. Use --phone option.")
        return tracker_class(tracking_number, phone)
    elif provider.lower() == "rokomari":
        if not phone:
            raise ValueError("Phone number is required for Rokomari tracking. Use --phone option.")
        return tracker_class(tracking_number, phone)
    else:
        return tracker_class(tracking_number)


def format_status_icon(status: str) -> str:
    """Get an appropriate icon for the status."""
    status_icons = {
        "pending": "⏳",
        "picked_up": "📦",
        "in_transit": "🚚",
        "out_for_delivery": "🚛",
        "delivered": "✅",
        "returned": "↩️",
        "cancelled": "❌",
        "failed_delivery": "⚠️",
        "unknown": "❓",
    }
    return status_icons.get(status, "📋")


def print_status_only(tracker):
    """Print only the delivery status."""
    try:
        current_status = tracker.get_current_status()
        is_delivered = tracker.is_delivered()
        last_update = tracker.get_last_update()

        status_icon = format_status_icon(current_status.value)
        delivery_icon = "✅" if is_delivered else "❌"

        print(f"\n📊 Tracking Status for {tracker.tracking_number}")
        print("=" * 50)
        print(f"Provider: {tracker.provider_name}")
        print(f"Status: {status_icon} {current_status.value.title()}")
        print(f"Delivered: {delivery_icon} {'Yes' if is_delivered else 'No'}")
        if last_update:
            print(f"Last Update: {last_update.strftime('%Y-%m-%d %H:%M:%S')}")

    except TrackingError as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        return 1

    return 0


def print_detailed_timeline(tracker):
    """Print detailed timeline with all events."""
    try:
        events = tracker.track()
        current_status = tracker.get_current_status()
        is_delivered = tracker.is_delivered()

        status_icon = format_status_icon(current_status.value)
        delivery_icon = "✅" if is_delivered else "❌"

        print(f"\n📦 Detailed Tracking for {tracker.tracking_number}")
        print("=" * 60)
        print(f"Provider: {tracker.provider_name}")
        print(f"Current Status: {status_icon} {current_status.value.title()}")
        print(f"Delivered: {delivery_icon} {'Yes' if is_delivered else 'No'}")
        print(f"Total Events: {len(events)}")

        if events:
            print("\n📅 Timeline:")
            print("-" * 60)
            for i, event in enumerate(events, 1):
                event_icon = format_status_icon(event.status.value)
                timestamp = event.timestamp.strftime("%Y-%m-%d %H:%M:%S")
                location = f" at {event.location}" if event.location else ""
                description = event.description or "No description"

                print(f"{i:2}. {event_icon} [{timestamp}] {event.status.value.title()}")
                if location:
                    print(f"    📍 Location: {event.location}")
                print(f"    📝 {description}")
                if i < len(events):
                    print()
        else:
            print("\n❓ No tracking events found.")

    except TrackingError as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        return 1

    return 0


def print_json_output(tracker):
    """Print results in JSON format."""
    import json
    from datetime import datetime

    try:
        events = tracker.track()
        current_status = tracker.get_current_status()
        is_delivered = tracker.is_delivered()
        last_update = tracker.get_last_update()

        # Convert events to JSON-serializable format
        events_data = []
        for event in events:
            events_data.append({
                "timestamp": event.timestamp.isoformat(),
                "status": event.status.value,
                "location": event.location,
                "description": event.description,
                "details": event.details,
            })

        result = {
            "tracking_number": tracker.tracking_number,
            "provider": tracker.provider_name,
            "current_status": current_status.value,
            "is_delivered": is_delivered,
            "last_update": last_update.isoformat() if last_update else None,
            "total_events": len(events),
            "events": events_data,
        }

        print(json.dumps(result, indent=2, ensure_ascii=False))

    except TrackingError as e:
        error_result = {
            "error": str(e),
            "provider": getattr(e, "provider", ""),
            "tracking_number": getattr(e, "tracking_number", ""),
        }
        print(json.dumps(error_result, indent=2), file=sys.stderr)
        return 1

    return 0


def main(args: Optional[list] = None) -> int:
    """Main CLI entry point."""
    parser = create_parser()
    parsed_args = parser.parse_args(args)

    try:
        # Get the tracker instance
        tracker = get_tracker(parsed_args.provider, parsed_args.tracking_number, parsed_args.phone or "")

        # Handle different output formats
        if parsed_args.json:
            return print_json_output(tracker)
        elif parsed_args.status_only:
            return print_status_only(tracker)
        else:
            return print_detailed_timeline(tracker)

    except ValueError as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\n\n⚠️ Operation cancelled by user.", file=sys.stderr)
        return 130
    except Exception as e:
        print(f"❌ Unexpected error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())

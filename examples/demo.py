"""Example usage of the Bangladeshi Parcel Tracker package."""

from bangladeshi_parcel_tracker import (
    RedxTracker, 
    SteadfastTracker, 
    PathaoTracker, 
    RokomariTracker,
    TrackingError
)

def demo_single_provider():
    """Demonstrate tracking with a single provider."""
    print("=== Single Provider Demo ===")
    
    # Track with Redx
    tracker = RedxTracker("RDX123456789")
    
    try:
        print(f"Tracking with {tracker.provider_name}")
        print(f"Tracking Number: {tracker.tracking_number}")
        print("-" * 40)
        
        # Get tracking events
        events = tracker.track()
        
        # Display current status
        print(f"Current Status: {tracker.get_current_status().value}")
        print(f"Is Delivered: {tracker.is_delivered()}")
        print(f"Last Update: {tracker.get_last_update()}")
        print()
        
        # Display timeline
        print("Timeline:")
        for event in events:
            print(f"  {event}")
            
    except TrackingError as e:
        print(f"Tracking Error: {e}")


def demo_multiple_providers():
    """Demonstrate tracking with multiple providers."""
    print("\\n=== Multiple Provider Demo ===")
    
    # Sample tracking numbers for each provider
    tracking_data = {
        'Redx': "RDX123456789",
        'Steadfast': "SF987654321", 
        'Pathao': "PA456789123",
        'Rokomari': "RK789123456"
    }
    
    providers = {
        'Redx': RedxTracker,
        'Steadfast': SteadfastTracker,
        'Pathao': PathaoTracker,
        'Rokomari': RokomariTracker
    }
    
    for provider_name, tracker_class in providers.items():
        tracking_number = tracking_data[provider_name]
        tracker = tracker_class(tracking_number)
        
        try:
            print(f"\\n{provider_name} Tracking ({tracking_number}):")
            print("-" * 50)
            
            events = tracker.track()
            
            print(f"Status: {tracker.get_current_status().value}")
            print(f"Delivered: {'✅' if tracker.is_delivered() else '❌'}")
            print(f"Events: {len(events)}")
            
            # Show last 2 events
            print("Recent Events:")
            for event in events[-2:]:
                print(f"  📍 {event}")
                
        except TrackingError as e:
            print(f"❌ Error: {e}")


def demo_refresh_functionality():
    """Demonstrate refresh functionality."""
    print("\\n=== Refresh Demo ===")
    
    tracker = SteadfastTracker("SF987654321")
    
    # Initial tracking
    print("Initial tracking...")
    events1 = tracker.track()
    print(f"Found {len(events1)} events")
    
    # Refresh
    print("\\nRefreshing...")
    events2 = tracker.refresh()
    print(f"After refresh: {len(events2)} events")
    
    print(f"Is delivered: {tracker.is_delivered()}")


def demo_error_handling():
    """Demonstrate error handling."""
    print("\\n=== Error Handling Demo ===")
    
    # This would typically fail with an invalid tracking number
    invalid_tracker = RedxTracker("INVALID123")
    
    try:
        events = invalid_tracker.track()
        print("Tracking successful!")
    except TrackingError as e:
        print(f"Expected error occurred:")
        print(f"  Message: {e}")
        print(f"  Provider: {e.provider}")
        print(f"  Tracking Number: {e.tracking_number}")


if __name__ == "__main__":
    print("Bangladeshi Parcel Tracker - Demo")
    print("=" * 40)
    
    # Run all demos
    demo_single_provider()
    demo_multiple_providers() 
    demo_refresh_functionality()
    demo_error_handling()
    
    print("\\n" + "=" * 40)
    print("Demo completed!")
    print("\\nNote: This demo uses mock data.")
    print("Real implementations would fetch live tracking data.")

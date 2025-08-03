# Bangladeshi Parcel Tracker

A Python package for tracking parcels from various Bangladeshi courier services including Redx, Steadfast, Pathao, and Rokomari.

[![CI](https://github.com/yourusername/bangladeshi-parcel-tracker/workflows/CI/badge.svg)](https://github.com/yo# Install in development mode
pip install -e ".[dev]"

# Format code
black src/

# Lint code
flake8 src/

# Type checking
mypy src/
```eshi-parcel-tracker/actions/workflows/ci.yml)
[![PyPI version](https://badge.fury.io/py/bangladeshi-parcel-tracker.svg)](https://badge.fury.io/py/bangladeshi-parcel-tracker)
[![Python versions](https://img.shields.io/pypi/pyversions/bangladeshi-parcel-tracker.svg)](https://pypi.org/project/bangladeshi-parcel-tracker/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## Features

- 🚚 Support for major Bangladeshi courier services
- 📦 Unified tracking interface across all providers
- ⏱️ Detailed timeline of parcel journey
- 🎯 Easy-to-use delivery status checking
- 🔄 Automatic status updates and refresh
- 📊 Comprehensive tracking event data
- 🐍 Python 3.8+ support
- ✅ Fully typed with comprehensive test coverage

## Supported Courier Services

- **Redx** - Leading courier service in Bangladesh
- **Steadfast** - Reliable delivery solutions
- **Pathao** - Fast and efficient courier service  
- **Rokomari** - Book and product delivery specialist

## Installation

Install the package using pip:

```bash
pip install bangladeshi-parcel-tracker
```

For development installation:

```bash
git clone https://github.com/yourusername/bangladeshi-parcel-tracker.git
cd bangladeshi-parcel-tracker
pip install -e ".[dev]"
```

## Quick Start

### Basic Usage

```python
from bangladeshi_parcel_tracker import RedxTracker, SteadfastTracker

# Track a Redx parcel
tracker = RedxTracker("RDX123456789")
events = tracker.track()

# Check if delivered
if tracker.is_delivered():
    print("Package has been delivered!")
else:
    print(f"Current status: {tracker.get_current_status().value}")

# Print timeline
for event in events:
    print(event)
```

### Using Different Providers

```python
from bangladeshi_parcel_tracker import (
    RedxTracker, SteadfastTracker, 
    PathaoTracker, RokomariTracker
)

tracking_number = "YOUR_TRACKING_NUMBER"

# Choose your provider
providers = {
    'redx': RedxTracker(tracking_number),
    'steadfast': SteadfastTracker(tracking_number),
    'pathao': PathaoTracker(tracking_number),
    'rokomari': RokomariTracker(tracking_number)
}

for name, tracker in providers.items():
    try:
        events = tracker.track()
        print(f"\\n{tracker.provider_name} Tracking:")
        print(f"Status: {tracker.get_current_status().value}")
        print(f"Delivered: {tracker.is_delivered()}")
        print(f"Last Update: {tracker.get_last_update()}")
        
        for event in events:
            print(f"  {event}")
            
    except Exception as e:
        print(f"Error tracking with {name}: {e}")
```

## Command Line Interface

The package includes a powerful CLI for tracking parcels from the terminal:

### Installation & Usage

After installing the package, you can use the `bangladeshi-parcel-tracker` command:

```bash
# Basic usage
bangladeshi-parcel-tracker <provider> <tracking_number>

# Show help
bangladeshi-parcel-tracker --help

# Show version
bangladeshi-parcel-tracker --version
```

### CLI Examples

```bash
# Track with Redx (detailed timeline)
bangladeshi-parcel-tracker redx RDX123456789

# Track with Steadfast (status only)
bangladeshi-parcel-tracker steadfast SF987654321 --status-only

# Track with Pathao (JSON output)
bangladeshi-parcel-tracker pathao PA456789123 --json

# Track with Rokomari (detailed timeline)
bangladeshi-parcel-tracker rokomari RK789123456 --detailed
```

### CLI Options

- `--status-only`, `-s`: Show only the current delivery status
- `--detailed`, `-d`: Show detailed timeline with all events (default)
- `--json`, `-j`: Output results in JSON format
- `--version`, `-v`: Show version information
- `--help`, `-h`: Show help message

### CLI Output Examples

**Status Only Output:**
```
📊 Tracking Status for RDX123456789
==================================================
Provider: Redx
Status: 🚛 Out For Delivery
Delivered: ❌ No
Last Update: 2025-01-15 15:45:00
```

**Detailed Timeline:**
```
📦 Detailed Tracking for SF987654321
============================================================
Provider: Steadfast
Current Status: ✅ Delivered
Delivered: ✅ Yes
Total Events: 4

📅 Timeline:
------------------------------------------------------------
 1. ⏳ [2025-01-15 08:00:00] Pending
    📍 Location: Steadfast Hub
    📝 Order received and processing

 2. 📦 [2025-01-15 10:30:00] Picked Up
    📍 Location: Pickup Point
    📝 Package collected from merchant

 3. 🚚 [2025-01-15 14:15:00] In Transit
    📍 Location: Transit Hub
    📝 Package in transit to destination

 4. ✅ [2025-01-15 16:00:00] Delivered
    📍 Location: Customer Address
    📝 Package delivered successfully
```

**JSON Output:**
```json
{
  "tracking_number": "PA456789123",
  "provider": "Pathao",
  "current_status": "in_transit",
  "is_delivered": false,
  "last_update": "2025-01-15T13:20:00",
  "total_events": 3,
  "events": [
    {
      "timestamp": "2025-01-15T09:15:00",
      "status": "pending",
      "location": "Pathao Warehouse",
      "description": "Parcel received at warehouse",
      "details": null
    }
  ]
}
```

## API Reference

### BaseTracker

All provider classes inherit from `BaseTracker` and implement these methods:

#### Properties
- `provider_name: str` - Name of the courier service
- `tracking_number: str` - The tracking/consignment number

#### Methods
- `track() -> List[TrackingEvent]` - Fetch tracking events
- `is_delivered() -> bool` - Check if parcel is delivered
- `get_current_status() -> TrackingStatus` - Get current tracking status
- `get_last_update() -> Optional[datetime]` - Get timestamp of last update
- `refresh() -> List[TrackingEvent]` - Force refresh tracking data

### TrackingEvent

Represents a single tracking event:

```python
@dataclass
class TrackingEvent:
    timestamp: datetime
    status: TrackingStatus
    location: Optional[str] = None
    description: Optional[str] = None
    details: Optional[str] = None
```

### TrackingStatus

Enumeration of possible tracking statuses:

- `PENDING` - Order received/processing
- `PICKED_UP` - Package picked up
- `IN_TRANSIT` - Package in transit
- `OUT_FOR_DELIVERY` - Out for delivery
- `DELIVERED` - Successfully delivered
- `RETURNED` - Returned to sender
- `CANCELLED` - Order cancelled
- `FAILED_DELIVERY` - Delivery attempt failed
- `UNKNOWN` - Status unknown

## Error Handling

The package provides a custom `TrackingError` exception:

```python
from bangladeshi_parcel_tracker import TrackingError

try:
    tracker = RedxTracker("INVALID123")
    events = tracker.track()
except TrackingError as e:
    print(f"Tracking failed: {e}")
    print(f"Provider: {e.provider}")
    print(f"Tracking Number: {e.tracking_number}")
```

## Development

### Setting up Development Environment

```bash
# Clone the repository
git clone https://github.com/yourusername/bangladeshi-parcel-tracker.git
cd bangladeshi-parcel-tracker

# Install in development mode
pip install -e ".[dev]"

# Run tests
pytest

# Run tests with coverage
pytest --cov=bangladeshi_parcel_tracker --cov-report=html

# Format code
black src/ tests/

# Lint code
flake8 src/ tests/

# Type checking
mypy src/
```

### Format code
black src/

# Lint code
flake8 src/

# Type checking
mypy src/
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request. For major changes, please open an issue first to discuss what you would like to change.

### Guidelines

1. Follow the existing code style (Black formatting)
2. Update documentation as needed
3. Ensure code passes linting and type checking

### Provider Implementation

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request. For major changes, please open an issue first to discuss what you would like to change.

### Guidelines

1. Follow the existing code style (Black formatting)
2. Add tests for any new functionality
3. Update documentation as needed
4. Ensure all tests pass

### Provider Implementation

To add a new courier service provider:

1. Create a new file in `src/bangladeshi_parcel_tracker/providers/`
2. Inherit from `BaseTracker`
3. Implement the `track()` method
4. Add provider to `__init__.py`

Example:

```python
from ..base import BaseTracker, TrackingEvent, TrackingStatus

class NewProviderTracker(BaseTracker):
    @property
    def provider_name(self) -> str:
        return "New Provider"
    
    def track(self) -> List[TrackingEvent]:
        # Implementation here
        pass
```

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Changelog

### v0.1.0
- Initial release
- Support for Redx, Steadfast, Pathao, and Rokomari
- Base tracking functionality
- Command Line Interface (CLI)
- GitHub Actions CI/CD

## Acknowledgments

- Thanks to all Bangladeshi courier services for their tracking systems
- Built with ❤️ for the Bangladeshi developer community

## Disclaimer

This package is not officially affiliated with any of the courier services. It's an independent tool created to help developers integrate parcel tracking functionality into their applications.

**Note**: The current implementation includes placeholder/mock data for demonstration purposes. Real implementations would require proper HTTP requests and HTML/API parsing specific to each courier service's tracking system.

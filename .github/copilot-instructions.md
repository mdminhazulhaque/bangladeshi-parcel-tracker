<!-- Use this file to provide workspace-specific custom instructions to Copilot. For more details, visit https://code.visualstudio.com/docs/copilot/copilot-customization#_use-a-githubcopilotinstructionsmd-file -->

# Bangladeshi Parcel Tracker Project Instructions

This is a Python package for tracking parcels from various Bangladeshi courier services including Redx, Steadfast, Pathao, and Rokomari.

## Key Guidelines:

1. **Architecture**: Follow the abstract base class pattern with `BaseTracker` as the parent class
2. **Provider Implementation**: Each courier service should inherit from `BaseTracker` and implement the `track()` method
3. **Data Models**: Use the `TrackingEvent` dataclass and `TrackingStatus` enum for consistent data representation
4. **Error Handling**: Use the custom `TrackingError` exception for tracking-related errors
5. **Type Hints**: Always include proper type hints for better code quality
6. **Documentation**: Follow Google-style docstrings for all public methods and classes
7. **Real Implementation**: Current providers contain mock data - replace with actual HTTP requests and HTML/API parsing
8. **Rate Limiting**: Implement proper rate limiting when making requests to courier websites
9. **Caching**: Consider implementing caching mechanisms for repeated tracking requests
10. **CLI**: Maintain the command-line interface for easy package usage

## Code Style:
- Use Black for code formatting (line length: 88)
- Follow PEP 8 conventions
- Use meaningful variable and method names
- Keep methods focused and single-purpose

## When implementing real tracking:
- Use `requests` library for HTTP requests
- Use `BeautifulSoup` for HTML parsing
- Handle network timeouts and retries gracefully
- Respect robots.txt and implement appropriate delays between requests
- Consider using session objects for persistent connections

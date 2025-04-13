"""
Platform-specific connectors for social media APIs

This module provides interfaces for interacting with different
social media platforms in a consistent way.
"""

# Map platform names to their implementation classes
# from .instagram import InstagramPlatform
# Note: Uncomment this line once you create instagram.py

# Dictionary mapping platform names to their classes for easy instantiation
PLATFORM_MAP = {
    'instagram': 'InstagramPlatform',  # Replace with actual class once implemented
    # Add more platforms as they're implemented
}

def get_platform(platform_name):
    """
    Get the appropriate platform class for a given platform name
    
    Parameters:
    -----------
    platform_name : str
        Name of the platform (e.g., 'instagram')
        
    Returns:
    --------
    instance of SocialMediaPlatform
        An initialized platform connector
        
    Raises:
    -------
    ValueError
        If the platform isn't supported
    """
    if platform_name not in PLATFORM_MAP:
        raise ValueError(f"Unsupported platform: {platform_name}. "
                         f"Supported platforms: {', '.join(PLATFORM_MAP.keys())}")
    
    # This will be updated later when class implementations are available
    raise NotImplementedError("Platform support not yet implemented")

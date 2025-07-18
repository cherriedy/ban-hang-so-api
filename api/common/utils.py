"""
Common utility functions shared across the application.
"""

import urllib.parse


def generate_default_thumbnail(name: str) -> str:
    """
    Generate a default thumbnail URL using the given name.
    
    Args:
        name: The name to use for generating the thumbnail
        
    Returns:
        str: Default thumbnail URL
    """
    encoded_name = urllib.parse.quote(name)
    encoded_colors = urllib.parse.quote("b6e3f4,c0aede,d1d4f9")
    return f"https://api.dicebear.com/9.x/initials/png?seed={encoded_name}&backgroundColor={encoded_colors}"

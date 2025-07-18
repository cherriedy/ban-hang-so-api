"""
Constants for transaction operations.
"""

# Default customer information for retail transactions
DEFAULT_RETAIL_CUSTOMER = {
    "id": None,
    "name": "Khách lẻ",  # Retail customer in Vietnamese
    "phone": None,
    "email": ""
}

# Alternative names for different locales (if needed in the future)
RETAIL_CUSTOMER_NAMES = {
    "vi": "Khách lẻ",
    "en": "Walk-in Customer",
    "default": "Khách lẻ"
}

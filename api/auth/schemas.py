"""
This module defines the Pydantic models used for user authentication.
These models are used for request and response validation and serialization.
"""

from typing import Optional, List

from pydantic import BaseModel, EmailStr

from api.common.schemas import StoreInUser, TimestampMixin


class UserSignup(BaseModel):
    """
    Represents the data required for a new user to sign up.
    This model is used to validate the request body when a new user signs up.
    """

    email: EmailStr  # The email address of the user. Must be a valid email format.
    phone: Optional[str] = None  # An optional phone number for the user.
    password: str  # The password for the new user account.
    displayName: str  # The display name for the new user.
    imageUrl: Optional[str] = None  # An optional URL to the user\'s profile picture.


class UserResponse(TimestampMixin):
    """
    Represents the response sent after a successful user operation.
    This model is used to serialize the response data according to the new structure.
    """

    email: EmailStr  # Kept EmailStr, assuming email from DB is valid
    contactName: str  # Changed from displayName
    phone: Optional[str] = None  # Added phone
    imageUrl: Optional[str] = None  # Added imageUrl
    stores: List[StoreInUser]  # Using common StoreInUser model

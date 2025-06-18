"""
This module defines the Pydantic models used for authentication.
These models are used for request and response validation and serialization.
"""

from typing import Optional, List
from pydantic import BaseModel, EmailStr, Field

from api.common.schemas import JSendResponse, TimestampMixin


class StoreInUser(BaseModel):
    """
    Represents a store reference within a user document.
    """
    id: str
    role: str


class UserSignup(BaseModel):
    """
    Represents the request data for signing up a new user.
    """
    email: EmailStr
    password: str = Field(..., min_length=6)
    displayName: Optional[str] = None
    phone: Optional[str] = None
    imageUrl: Optional[str] = None


class UserBase(BaseModel, TimestampMixin):
    """
    Common user fields returned in responses.
    """
    email: str
    contactName: Optional[str] = None
    phone: Optional[str] = None
    imageUrl: Optional[str] = None
    stores: List[StoreInUser] = []


class UserResponse(JSendResponse[UserBase]):
    """
    Response model for user operations.
    """
    pass

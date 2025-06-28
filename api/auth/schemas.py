"""
This module defines the Pydantic models used for authentication.
These models are used for request and response validation and serialization.
"""

from typing import Optional, List
from pydantic import BaseModel, EmailStr, Field
from datetime import datetime

from api.common.schemas import JSendResponse, TimestampMixin


class StoreInUser(BaseModel):
    """
    Represents a store reference within a user document.
    """
    id: str
    role: str


class StoreInfo(BaseModel):
    """
    Represents store information for signup process.
    """
    name: str
    description: str
    imageUrl: Optional[str] = None


class UserSignup(BaseModel):
    """
    Represents the request data for signing up a new user.
    """
    email: EmailStr
    password: str = Field(..., min_length=6)
    displayName: Optional[str] = None
    phone: Optional[str] = None
    imageUrl: Optional[str] = None
    role: str = Field(..., description="User role: 'owner' or 'staff'")
    storeInfo: Optional[StoreInfo] = Field(None, description="Store information for owner role")
    storeId: Optional[str] = Field(None, description="Store ID for staff role")


class UserBase(BaseModel, TimestampMixin):
    """
    Common user fields returned in responses.
    """
    email: str
    contactName: Optional[str] = None
    phone: Optional[str] = None
    imageUrl: Optional[str] = None
    stores: List[StoreInUser] = []
    createdAt: Optional[datetime] = None
    updatedAt: Optional[datetime] = None


class UserResponse(JSendResponse[UserBase]):
    """
    Response model for user operations.
    """
    pass

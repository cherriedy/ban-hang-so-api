"""
This module defines the Pydantic models used for store management.
These models are used for request and response validation and serialization.
"""

from typing import List, Optional

from pydantic import BaseModel

from api.common.schemas import TimestampMixin


class UserStore(BaseModel, TimestampMixin):
    """
    Represents detailed information about a store associated with a user.
    This model includes store metadata and user's role within the store.
    """
    id: str
    role: str
    name: Optional[str] = None
    description: Optional[str] = None


class CreateStoreRequest(BaseModel):
    """
    Represents the request data for creating a new store.
    """
    name: str
    description: str
    imageUrl: Optional[str] = None


class CreateStoreResponse(BaseModel):
    """
    Store data returned after creation in JSend format
    """
    store_id: str


class UserStoresData(BaseModel):
    """
    Stores data returned for a user in JSend format
    """
    stores: List[UserStore]

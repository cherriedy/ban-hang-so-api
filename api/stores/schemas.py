"""
This module defines the Pydantic models used for store management.
These models are used for request and response validation and serialization.
"""

from typing import List, Optional
from pydantic import BaseModel

from api.common.schemas import StoreInUser, TimestampMixin


class UserStore(BaseModel, TimestampMixin):
    """
    Represents detailed information about a store associated with a user.
    This model includes store metadata and user's role within the store.
    """
    id: str
    role: str
    name: Optional[str] = None
    description: Optional[str] = None
    # Add other store fields as needed


class UserStoresResponse(BaseModel):
    """
    Represents the response sent after retrieving a user's associated stores.
    This model wraps a list of UserStore objects.
    """
    stores: List[UserStore]

"""
This module defines common Pydantic models used across multiple API modules.
These models represent shared data structures to ensure consistency throughout the application.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class StoreInUser(BaseModel):
    """
    Represents a store associated with a user, including its ID and role.
    This model is used to represent the minimal store information in user contexts.
    """
    id: str
    role: str


class TimestampMixin(BaseModel):
    """
    A mixin that adds created and updated timestamp fields to models.
    Use this for consistency in models that track creation and modification times.
    """
    createdAt: Optional[datetime] = None
    updatedAt: Optional[datetime] = None

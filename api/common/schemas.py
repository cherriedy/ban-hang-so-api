"""
This module defines common Pydantic models used across multiple API modules.
These models represent shared data structures to ensure consistency throughout the application.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional, TypeVar, Generic, List, Any, Dict

from pydantic import BaseModel


class StoreInUser(BaseModel):
    """
    Represents a store associated with a user, including its ID and role.
    This model is used to represent the minimal store information in user contexts.
    """
    id: str
    role: str


class TimestampMixin:
    """
    A mixin that adds created and updated timestamp fields to models.
    Use this for consistency in models that track creation and modification times.
    """
    createdAt: Optional[datetime] = None
    updatedAt: Optional[datetime] = None


class JSendStatus(str, Enum):
    """
    JSend status options according to specification.
    """
    SUCCESS = "success"
    FAIL = "fail"
    ERROR = "error"


T = TypeVar('T')


class PaginationResponse(BaseModel, Generic[T]):
    """
    A generic model for paginated responses.
    """
    items: List[T]
    total: int
    page: int
    size: int
    pages: int


class JSendResponse(BaseModel, Generic[T]):
    """
    Base JSend response format as per https://github.com/omniti-labs/jsend
    """
    status: JSendStatus
    data: Optional[T] = None
    message: Optional[str] = None
    code: Optional[int] = None  # For error responses

    @classmethod
    def success(cls, data: Any = None) -> 'JSendResponse':
        """Create a success response with data"""
        return cls(status=JSendStatus.SUCCESS, data=data)

    @classmethod
    def fail(cls, data: Dict[str, Any]) -> 'JSendResponse':
        """Create a fail response with validation errors or other data-related failures"""
        return cls(status=JSendStatus.FAIL, data=data)

    @classmethod
    def error(cls, message: str, code: Optional[int] = None, data: Any = None) -> 'JSendResponse':
        """Create an error response for system or unexpected errors"""
        return cls(status=JSendStatus.ERROR, message=message, code=code, data=data)

"""
This module defines common Pydantic models used across multiple API modules.
These models represent shared data structures to ensure consistency throughout the application.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional, TypeVar, Generic, List, Any, Dict

from pydantic import BaseModel, field_validator
import re


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

    @field_validator('createdAt', 'updatedAt', mode='before')
    @classmethod
    def parse_datetime(cls, value):
        """Parse various datetime formats including 'Apr 12, 2025 9:20:43 PM'"""
        if value is None:
            return None

        if isinstance(value, datetime):
            return value

        if isinstance(value, str):
            # Handle the format "Apr 12, 2025 9:20:43 PM"
            pattern = r"(\w+) (\d+), (\d+) (\d+):(\d+):(\d+) ([AP]M)"
            match = re.match(pattern, value)
            if match:
                month_map = {
                    "Jan": 1, "Feb": 2, "Mar": 3, "Apr": 4, "May": 5, "Jun": 6,
                    "Jul": 7, "Aug": 8, "Sep": 9, "Oct": 10, "Nov": 11, "Dec": 12
                }
                month_str, day, year, hour, minute, second, am_pm = match.groups()

                month = month_map.get(month_str, 1)
                day = int(day)
                year = int(year)
                hour = int(hour)
                minute = int(minute)
                second = int(second)

                # Convert to 24-hour format
                if am_pm == "PM" and hour < 12:
                    hour += 12
                elif am_pm == "AM" and hour == 12:
                    hour = 0

                return datetime(year, month, day, hour, minute, second)

            # Try Python's default parser as a fallback
            try:
                return datetime.fromisoformat(value)
            except ValueError:
                try:
                    return datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
                except ValueError:
                    pass

        # If we can't parse it, return as is and let Pydantic handle the validation error
        return value


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

"""
Customer management schemas for CRUD operations.
"""

from typing import Optional, Union
from pydantic import BaseModel, EmailStr, field_validator, model_validator
from datetime import datetime

from api.common.schemas import JSendResponse, PaginationResponse


class CustomerCreate(BaseModel):
    """
    Schema for creating a new customer.
    """
    name: str
    phone: Optional[str] = None
    email: Optional[EmailStr] = None
    address: Optional[str] = None
    dob: Optional[str] = None  # Date of birth in ISO format (YYYY-MM-DD)
    imageUrl: Optional[str] = None

    @field_validator('email', mode='before')
    @classmethod
    def validate_email(cls, v):
        """Convert empty string to None for email validation, then back to empty string."""
        if v == '':
            return None  # Let validation pass, but we'll handle empty string in the service
        return v

    @field_validator('dob', mode='before')
    @classmethod
    def validate_dob(cls, v):
        """Validate and format date of birth to YYYY-MM-DD format."""
        if v is None or v == '':
            return None

        # Ensure v is a string
        if not isinstance(v, str):
            return None

        try:
            # If it's already in YYYY-MM-DD format, return as is
            if len(v) == 10 and v.count('-') == 2:
                datetime.strptime(v, '%Y-%m-%d')
                return v

            # Try to parse as ISO datetime format (with timezone)
            if 'T' in v:
                # Handle ISO datetime format like "2025-07-01T13:39:11.410Z"
                dt = datetime.fromisoformat(v.replace('Z', '+00:00'))
                return dt.strftime('%Y-%m-%d')

            # Try to parse as date only
            dt = datetime.strptime(v, '%Y-%m-%d')
            return dt.strftime('%Y-%m-%d')

        except ValueError:
            raise ValueError(f"Invalid date format for dob: {v}. Expected YYYY-MM-DD or ISO datetime format.")


class CustomerUpdate(BaseModel):
    """
    Schema for updating customer information.
    """
    name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[Union[EmailStr, str]] = None  # Allow both EmailStr and empty string
    address: Optional[str] = None
    dob: Optional[str] = None
    imageUrl: Optional[str] = None

    @field_validator('email', mode='before')
    @classmethod
    def validate_email(cls, v):
        """Handle email validation for updates, preserving empty strings."""
        if v == '':
            # For updates, preserve empty string to clear the field
            return ''
        return v

    @field_validator('dob', mode='before')
    @classmethod
    def validate_dob(cls, v):
        """Validate and format date of birth to YYYY-MM-DD format."""
        if v is None or v == '':
            return None

        # Ensure v is a string
        if not isinstance(v, str):
            return None

        try:
            # If it's already in YYYY-MM-DD format, return as is
            if len(v) == 10 and v.count('-') == 2:
                datetime.strptime(v, '%Y-%m-%d')
                return v

            # Try to parse as ISO datetime format (with timezone)
            if 'T' in v:
                # Handle ISO datetime format like "2025-07-01T13:39:11.410Z"
                dt = datetime.fromisoformat(v.replace('Z', '+00:00'))
                return dt.strftime('%Y-%m-%d')

            # Try to parse as date only
            dt = datetime.strptime(v, '%Y-%m-%d')
            return dt.strftime('%Y-%m-%d')

        except ValueError:
            raise ValueError(f"Invalid date format for dob: {v}. Expected YYYY-MM-DD or ISO datetime format.")


class CustomerInfo(BaseModel):
    """
    Customer information returned in responses.
    """
    id: str
    storeId: str
    name: str
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    dob: Optional[str] = None
    imageUrl: Optional[str] = None
    createdAt: Optional[str] = None
    updatedAt: Optional[str] = None


class CustomerListResponse(JSendResponse[PaginationResponse[CustomerInfo]]):
    """
    Response model for customer list operations with pagination.
    """
    pass


class CustomerItemResponse(BaseModel):
    """
    Wrapper for single customer item response.
    """
    item: CustomerInfo


class CustomerDeleteResponse(BaseModel):
    """
    Response for customer deletion operations.
    """
    message: str


class CustomerResponse(JSendResponse[CustomerItemResponse]):
    """
    Response model for single customer operations with item wrapper.
    """
    pass


class CustomerDeleteResponseModel(JSendResponse[CustomerDeleteResponse]):
    """
    Response model for customer deletion operations.
    """
    pass


class CustomerCreateResponse(JSendResponse[CustomerInfo]):
    """
    Response model for customer creation operations.
    """
    pass

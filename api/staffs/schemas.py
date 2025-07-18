"""
Staff management schemas for CRUD operations.
"""

from typing import Optional, List
from pydantic import BaseModel, EmailStr, Field
from datetime import datetime

from api.common.schemas import JSendResponse, PaginationResponse


class StaffCreate(BaseModel):
    """
    Schema for creating a new staff account.
    """
    email: EmailStr
    displayName: Optional[str] = None
    phone: Optional[str] = None
    imageUrl: Optional[str] = None


class StaffUpdate(BaseModel):
    """
    Schema for updating staff account information.
    """
    displayName: Optional[str] = None
    phone: Optional[str] = None
    imageUrl: Optional[str] = None
    active: Optional[bool] = None


class StaffInfo(BaseModel):
    """
    Staff information returned in responses.
    """
    id: str
    email: str
    displayName: Optional[str] = None
    phone: Optional[str] = None
    imageUrl: Optional[str] = None
    active: bool = True
    storeId: str
    role: str = "staff"
    createdAt: Optional[str] = None
    updatedAt: Optional[str] = None


class StaffListResponse(JSendResponse[PaginationResponse[StaffInfo]]):
    """
    Response model for staff list operations with pagination using generic PaginationResponse.
    """
    pass


class StaffItemResponse(BaseModel):
    """
    Wrapper for single staff item response.
    """
    item: StaffInfo


class StaffDeleteResponse(BaseModel):
    """
    Response for staff deletion operations.
    """
    message: str


class StaffResponse(JSendResponse[StaffItemResponse]):
    """
    Response model for single staff operations with item wrapper.
    """
    pass


class StaffDeleteResponseModel(JSendResponse[StaffDeleteResponse]):
    """
    Response model for staff deletion operations.
    """
    pass


class StaffCredentials(BaseModel):
    """
    Staff credentials information (for creation response).
    """
    email: str
    message: str = "Staff account created successfully. Credentials have been sent to the staff member's email"


class StaffCreateResponse(JSendResponse[StaffCredentials]):
    """
    Response model for staffs creation with credentials.
    """
    pass

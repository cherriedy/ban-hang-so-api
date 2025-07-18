"""
This module defines the Pydantic models used for category management.
These models are used for request and response validation and serialization.
"""

from typing import Optional

from pydantic import BaseModel, Field

from api.common.schemas import TimestampMixin, PaginationResponse, JSendResponse


class CategoryBase(BaseModel):
    """
    Base model for category data that is common to create, update and response models.
    """
    name: str = Field(..., min_length=1, max_length=100, description="Category name")


class CategoryCreate(CategoryBase):
    """
    Represents the request data for creating a new category.
    Only requires name, storeId comes from authentication.
    """
    pass


class CategoryUpdate(BaseModel):
    """
    Represents the request data for updating an existing category.
    All fields are optional as only provided fields will be updated.
    """
    name: Optional[str] = Field(None, min_length=1, max_length=100, description="Category name")


class CategoryInDB(CategoryBase, TimestampMixin):
    """
    Represents a category as stored in the database, including all metadata.
    """
    id: str = Field(..., description="Unique category identifier")
    storeId: str = Field(..., description="Store ID that owns this category")
    productCount: Optional[int] = Field(default=0, description="Number of products in this category")


class CategoryDetailData(BaseModel):
    """
    Container for a single category item.
    """
    item: CategoryInDB


class CategoriesData(PaginationResponse[CategoryInDB]):
    """
    Represents a paginated list of categories.
    Inherits pagination fields from PaginationResponse and specifies
    CategoryInDB as the type for 'items'.
    """
    pass


class CategoryResponse(JSendResponse):
    """
    Category data returned in JSend format.

    Example:
    {
        "status": "success",
        "data": {
            "id": "123",
            "name": "Electronics",
            "storeId": "store123",
            "createdAt": "2023-01-01T00:00:00Z",
            "updatedAt": "2023-01-01T00:00:00Z"
        }
    }
    """
    data: Optional[CategoryInDB] = None


class CategoriesResponse(JSendResponse):
    """
    Multiple categories data returned in JSend format with pagination info.

    Example:
    {
        "status": "success",
        "data": {
            "items": [...],
            "total": 50,
            "page": 1,
            "size": 10,
            "pages": 5
        }
    }
    """
    data: Optional[CategoriesData] = None

"""
This module defines the Pydantic models used for brand management.
These models are used for request and response validation and serialization.
"""

from typing import Optional, List

from pydantic import BaseModel, Field

from api.common.schemas import TimestampMixin, PaginationResponse, JSendResponse


class BrandBase(BaseModel):
    """
    Base model for brand data that is common to create, update and response models.
    """
    name: str = Field(..., min_length=1, max_length=100, description="Brand name")


class BrandCreate(BrandBase):
    """
    Represents the request data for creating a new brand.
    Only requires name, storeId comes from authentication.
    """
    imageUrls: Optional[List[str]] = Field(default=[], description="List of brand image URLs")


class BrandUpdate(BaseModel):
    """
    Represents the request data for updating an existing brand.
    All fields are optional as only provided fields will be updated.
    """
    name: Optional[str] = Field(None, min_length=1, max_length=100, description="Brand name")
    imageUrls: Optional[List[str]] = Field(None, description="List of brand image URLs")


class BrandInDB(BrandBase, TimestampMixin):
    """
    Represents a brand as stored in the database, including all metadata.
    """
    id: str = Field(..., description="Unique brand identifier")
    storeId: str = Field(..., description="Store ID that owns this brand")
    productCount: Optional[int] = Field(default=0, description="Number of products in this brand")
    imageUrls: List[str] = Field(default=[], description="List of brand image URLs")
    thumbnailUrl: Optional[str] = Field(None, description="Thumbnail URL (first image or default)")


class BrandDetailData(BaseModel):
    """
    Container for a single brand item.
    """
    item: BrandInDB


class BrandsData(PaginationResponse[BrandInDB]):
    """
    Represents a paginated list of brands.
    Inherits pagination fields from PaginationResponse and specifies
    BrandInDB as the type for 'items'.
    """
    pass


class BrandResponse(JSendResponse):
    """
    Brand data returned in JSend format.

    Example:
    {
        "status": "success",
        "data": {
            "id": "123",
            "name": "Nike",
            "storeId": "store123",
            "createdAt": "2023-01-01T00:00:00Z",
            "updatedAt": "2023-01-01T00:00:00Z",
            "productCount": 15
        }
    }
    """
    data: Optional[BrandInDB] = None


class BrandsResponse(JSendResponse):
    """
    Multiple brands data returned in JSend format with pagination info.

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
    data: Optional[BrandsData] = None

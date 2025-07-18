"""
This module defines the Pydantic models used for sales management.
These models are used for request and response validation and serialization.
"""

from typing import Optional

from pydantic import BaseModel

from api.common.schemas import PaginationResponse, JSendResponse


class ProductSaleItem(BaseModel):
    """
    Lightweight product model for sale endpoints with only essential fields.
    """
    id: str
    name: str
    thumbnailUrl: Optional[str] = None
    sellingPrice: float
    purchasePrice: float = 0
    discountPrice: float = 0
    status: bool = True


class ProductSaleData(PaginationResponse[ProductSaleItem]):
    """
    Represents a paginated list of products for sale response.
    """
    pass


class ProductSaleResponse(JSendResponse[ProductSaleData]):
    """Response model for product sale operations."""
    pass

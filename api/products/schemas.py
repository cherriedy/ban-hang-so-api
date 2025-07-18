"""
This module defines the Pydantic models used for product management.
These models are used for request and response validation and serialization.
"""

from typing import Optional, List

from pydantic import BaseModel, field_validator

from api.common.schemas import TimestampMixin, PaginationResponse, JSendResponse


class CategorySchema(BaseModel, TimestampMixin):
    """
    Represents a product category with its metadata.
    """
    id: Optional[str] = None  # Made optional to handle data without id
    name: str
    storeId: Optional[str] = None  # Made optional for product creation
    empty: bool = False


class BrandSchema(BaseModel, TimestampMixin):
    """
    Represents a product brand with its metadata.
    """
    id: Optional[str] = None  # Made optional to handle data without id
    name: str
    storeId: Optional[str] = None  # Made optional for product creation
    empty: bool = False


class ProductBase(BaseModel):
    """
    Base model for product data that is common to create, update and response models.
    """
    name: str
    description: str = ""
    barcode: Optional[str] = ""
    note: str = ""
    purchasePrice: float = 0
    sellingPrice: float
    discountPrice: float = 0
    stockQuantity: int = 0
    status: bool = True
    imageUrls: List[str] = []
    thumbnailUrl: Optional[str] = None


class ProductCreate(ProductBase):
    """
    Represents the request data for creating a new product.
    """
    storeId: Optional[str] = None  # Made optional since it comes from query parameter
    brand: Optional[BrandSchema] = None
    category: Optional[CategorySchema] = None


class ProductUpdate(BaseModel):
    """
    Represents the request data for updating an existing product.
    All fields are optional as only provided fields will be updated.
    """
    name: Optional[str] = None
    description: Optional[str] = None
    barcode: Optional[str] = None
    note: Optional[str] = None
    purchasePrice: Optional[float] = None
    sellingPrice: Optional[float] = None
    discountPrice: Optional[float] = None
    stockQuantity: Optional[int] = None
    status: Optional[bool] = None
    imageUrls: Optional[List[str]] = None
    thumbnailUrl: Optional[str] = None
    brand: Optional[BrandSchema] = None
    category: Optional[CategorySchema] = None
    storeId: Optional[str] = None  # Changed from store_id to storeId


class ProductInDB(ProductBase, TimestampMixin):
    """
    Represents a product as stored in the database, including all metadata.
    """
    id: str
    storeId: str  # Required for database storage
    brand: Optional[BrandSchema] = None
    category: Optional[CategorySchema] = None

    @field_validator('category', 'brand', mode='before')
    @classmethod
    def validate_category_and_brand(cls, value):
        """Ensure category and brand have required fields or are set to None"""
        if value is None:
            return None

        if isinstance(value, dict):
            # If name is missing, return None as it's required for meaningful data
            if 'name' not in value or not value['name']:
                return None

            # If id is missing, we can still process the data
            # This handles cases where brand/category data is stored without document IDs
            return value

        return value


class ProductDetailData(BaseModel):
    """
    Container for a single product item.
    """
    item: ProductInDB


class ProductsData(PaginationResponse[ProductInDB]):
    """
    Represents a paginated list of products for response.
    """
    pass


class ProductResponse(JSendResponse[ProductInDB]):
    """Response model for single product operations."""
    pass


class ProductListResponse(JSendResponse[ProductsData]):
    """Response model for product list operations."""
    pass


class ProductDeleteResponse(JSendResponse[dict]):
    """Response model for product deletion operations."""
    pass


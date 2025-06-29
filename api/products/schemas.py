"""
This module defines the Pydantic models used for product management.
These models are used for request and response validation and serialization.
"""

from typing import Optional

from pydantic import BaseModel, field_validator, Field

from api.common.schemas import TimestampMixin, PaginationResponse, JSendResponse


class CategorySchema(BaseModel, TimestampMixin):
    """
    Represents a product category with its metadata.
    """
    id: str
    name: str
    storeId: str  # Added storeId to associate category with store
    empty: bool = False


class BrandSchema(BaseModel, TimestampMixin):
    """
    Represents a product brand with its metadata.
    """
    id: str
    name: str
    storeId: str  # Added storeId to associate brand with store
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
    avatarUrl: Optional[str] = None
    storeId: str  # Database uses storeId directly


class ProductCreate(ProductBase):
    """
    Represents the request data for creating a new product.
    """
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
    avatarUrl: Optional[str] = None
    brand: Optional[BrandSchema] = None
    category: Optional[CategorySchema] = None
    storeId: Optional[str] = None  # Changed from store_id to storeId


class ProductInDB(ProductBase, TimestampMixin):
    """
    Represents a product as stored in the database, including all metadata.
    """
    id: str
    brand: Optional[BrandSchema] = None
    category: Optional[CategorySchema] = None

    @field_validator('category', 'brand', mode='before')
    @classmethod
    def validate_category_and_brand(cls, value):
        """Ensure category and brand have required fields or are set to None"""
        if value is None:
            return None

        if isinstance(value, dict):
            # If id is missing, return None instead of an incomplete object
            if 'id' not in value:
                return None

        return value


class ProductDetailData(BaseModel):
    """
    Container for a single product item.
    """
    item: ProductInDB


class ProductsData(PaginationResponse[ProductInDB]):
    """
    Represents a paginated list of products.
    Inherits pagination fields from PaginationResponse and specifies
    ProductInDB as the type for 'items'.
    """
    pass


class ProductResponse(JSendResponse):
    """
    Product data returned in JSend format.

    Example:
    {
        "status": "success",
        "data": {
            "id": "123",
            "name": "Product name",
            ...
        }
    }
    """
    data: Optional[ProductInDB] = None


class ProductsResponse(JSendResponse):
    """
    Multiple products data returned in JSend format with pagination info.

    Example:
    {
        "status": "success",
        "data": {
            "items": [...],
            "total": 100,
            "page": 2,
            "size": 20,
            "pages": 5
        }
    }
    """
    data: Optional[ProductsData] = None


class ProductUpsert(BaseModel):
    """
    Combined schema for both creating and updating products.
    If id is provided, it will update the product, otherwise create a new one.
    """
    id: Optional[str] = None
    name: Optional[str] = None
    description: Optional[str] = None
    barcode: Optional[str] = None
    note: Optional[str] = None
    purchasePrice: Optional[float] = None
    sellingPrice: Optional[float] = None
    discountPrice: Optional[float] = None
    stockQuantity: Optional[int] = None
    status: Optional[bool] = None
    avatarUrl: Optional[str] = None
    brand: Optional[BrandSchema] = None
    category: Optional[CategorySchema] = None
    storeId: Optional[str] = None  # Changed from store_id to storeId

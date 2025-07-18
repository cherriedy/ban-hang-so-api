"""
Schemas for transaction operations.
"""
from datetime import datetime
from enum import Enum
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, validator

from api.common.schemas import PaginationResponse


class PaymentMethod(str, Enum):
    """Payment methods supported by the system."""
    CASH = "CASH"
    CREDIT_CARD = "CREDIT_CARD"
    MOBILE_BANKING = "MOBILE_BANKING"
    DIGITAL_WALLET = "DIGITAL_WALLET"


class BrandInfo(BaseModel):
    """Basic brand information."""
    id: str
    name: str


class CategoryInfo(BaseModel):
    """Basic category information."""
    id: str
    name: str


class CustomerInfo(BaseModel):
    """Basic customer information."""
    id: Optional[str] = None
    name: str
    phone: Optional[str] = None
    email: str


class StaffInfo(BaseModel):
    """Basic staff information."""
    id: str
    name: str
    phone: Optional[str] = None
    email: str
    role: str


class CartItem(BaseModel):
    """Item in a shopping cart."""
    id: str
    quantity: int = Field(..., gt=0)


class CartRequest(BaseModel):
    """Cart request model for creating transactions. storeId is injected from query parameter."""
    customerId: Optional[str] = None
    staffId: Optional[str] = None
    storeId: Optional[str] = None  # This will be overwritten by query parameter
    totalItems: int
    totalSellingPrices: float
    totalPurchasePrices: float
    totalDiscountPrices: float
    finalPrices: float
    paymentMethod: PaymentMethod
    items: List[CartItem]
    note: Optional[str] = None


class TransactionItem(BaseModel):
    """Item in a completed transaction."""
    id: str
    name: str
    thumbnailUrl: Optional[str] = None
    sellingPrice: float
    purchasePrice: float
    discountPrice: float
    quantity: int
    barcode: Optional[str] = None
    brand: Optional[BrandInfo] = None
    category: Optional[CategoryInfo] = None


class TransactionResponse(BaseModel):
    """Transaction response model."""
    id: str
    customer: Optional[CustomerInfo] = None
    staff: Optional[StaffInfo] = None
    storeId: str
    totalItems: int
    totalSellingPrices: float
    totalPurchasePrices: float
    totalDiscountPrices: float
    finalPrices: float
    paymentMethod: PaymentMethod
    items: List[TransactionItem]
    note: Optional[str] = None
    createdAt: datetime
    updatedAt: datetime


class TransactionCreate(BaseModel):
    """Model for creating a new transaction."""
    id: Optional[str] = None
    customerId: Optional[str] = None
    staffId: Optional[str] = None
    storeId: str
    totalItems: int
    totalSellingPrices: float
    totalPurchasePrices: float
    totalDiscountPrices: float
    finalPrices: float
    paymentMethod: PaymentMethod
    itemsIds: List[dict]  # List of {id, quantity}
    note: Optional[str] = None


class TransactionQuery(BaseModel):
    """Query parameters for transaction search."""
    storeId: Optional[str] = None
    customerId: Optional[str] = None
    staffId: Optional[str] = None
    startDate: Optional[datetime] = None
    endDate: Optional[datetime] = None
    minAmount: Optional[float] = None
    maxAmount: Optional[float] = None
    paymentMethod: Optional[PaymentMethod] = None


class TransactionSummary(BaseModel):
    """Transaction summary model for list endpoints."""
    id: str
    customerName: str
    staffName: Optional[str] = None
    price: float
    createdAt: datetime


class TransactionItemResponse(BaseModel):
    """
    Wrapper for single transaction item response.
    """
    item: TransactionResponse


class TransactionsData(PaginationResponse[TransactionSummary]):
    """
    Represents a paginated list of transactions.
    Inherits pagination fields from PaginationResponse and specifies
    TransactionSummary as the type for 'items'.
    """
    pass

"""
This module defines the Pydantic models used for store management.
These models are used for request and response validation and serialization.
"""

from typing import Optional

from pydantic import BaseModel

from api.common.schemas import TimestampMixin, PaginationResponse, JSendResponse


class UserStore(BaseModel, TimestampMixin):
    """
    Represents detailed information about a store associated with a user.
    This model includes store metadata and user's role within the store.
    """
    id: str
    role: str
    name: Optional[str] = None
    description: Optional[str] = None


class StoreDetail(BaseModel, TimestampMixin):
    """
    Represents detailed information about a store.
    Used for store detail responses.
    """
    id: str
    name: str
    description: str
    imageUrl: Optional[str] = None


class StoreDetailData(BaseModel):
    """
    Wrapper for store detail data that contains the store in an "item" field.
    Used for the store detail endpoint response structure.
    """
    item: StoreDetail


class CreateStoreRequest(BaseModel):
    """
    Represents the request data for creating or updating a store.
    When id is provided, the store will be updated, otherwise a new store will be created.
    """
    id: Optional[str] = None  # Store ID for updates, None for new stores
    name: str
    description: str
    imageUrl: Optional[str] = None


class UpdateStoreRequest(BaseModel):
    """
    Represents the request data for updating store information.
    All fields are optional to allow partial updates.
    """
    name: Optional[str] = None
    description: Optional[str] = None
    imageUrl: Optional[str] = None


class CreateStoreResponse(BaseModel):
    """
    Store data returned after creation in JSend format
    """
    store_id: str


class UserStoresData(PaginationResponse[UserStore]):
    """
    Paginated stores data returned for a user in JSend format.
    Inherits pagination fields from PaginationResponse and specifies
    UserStore as the item type.
    """
    pass


class UserStoresResponse(JSendResponse[UserStoresData]):
    """
    Response model for user stores operations with pagination using generic PaginationResponse.
    """
    pass

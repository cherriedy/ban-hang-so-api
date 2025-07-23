from fastapi import APIRouter, HTTPException, Depends, Query
from starlette import status

from api.auth.dependencies import get_current_user_id, get_store_owner_access
from api.common.schemas import JSendResponse
from api.stores.schemas import CreateStoreRequest, CreateStoreResponse, UpdateStoreRequest, UserStoresResponse, StoreDetail, StoreDetailData
from api.stores.services import get_user_stores_service, save_store_service, update_store_service, get_store_detail_service, delete_store_service

router = APIRouter()


@router.get("/")
def get_stores():
    return {"message": "Stores endpoint"}


@router.get("/{store_id}", response_model=JSendResponse[StoreDetailData])
async def get_store_detail(
    store_id: str,
    user_id: str = Depends(get_current_user_id)
):
    """
    Retrieves detailed information about a store. Only store owners can access this endpoint.

    Args:
        store_id: The ID of the store to retrieve details for
        user_id: The authenticated user ID (injected by dependency)

    Returns:
        JSendResponse containing store detail information
    """
    try:
        store_detail = get_store_detail_service(store_id, user_id)
        return JSendResponse.success(store_detail)
    except HTTPException as e:
        return JSendResponse.error(
            message=str(e.detail),
            code=e.status_code
        )
    except Exception as e:
        return JSendResponse.error(
            message=str(e),
            code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@router.get("/user/{user_id}", response_model=UserStoresResponse)
async def get_user_stores(
    user_id: str,
    page: int = Query(1, ge=1, description="Page number (starts from 1)"),
    size: int = Query(10, ge=1, le=100, description="Number of items per page (1-100)")
):
    """
    Retrieves stores associated with a user with pagination support.

    Args:
        user_id: The ID of the user whose stores to retrieve
        page: Page number (starts from 1)
        size: Number of items per page (1-100)

    Returns:
        UserStoresResponse containing paginated list of stores
    """
    try:
        stores_data = get_user_stores_service(user_id, page, size)
        return UserStoresResponse.success(stores_data)
    except HTTPException as e:
        return UserStoresResponse.error(
            message=str(e.detail),
            code=e.status_code
        )
    except Exception as e:
        return UserStoresResponse.error(
            message=str(e),
            code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@router.post("/", response_model=JSendResponse[CreateStoreResponse])
async def create_store(
    store_data: CreateStoreRequest,
    user_id: str = Depends(get_current_user_id)
):
    """
    Creates a new store and associates it with the authenticated user.

    The store is saved in the Stores collection with the provided data,
    then the store ID is added to the user's document with an ADMIN role.

    Args:
        store_data: The store information to create
        user_id: The authenticated user ID (injected by dependency)

    Returns:
        JSendResponse with store creation data
    """
    try:
        store_response = save_store_service(user_id, store_data)
        return JSendResponse.success(store_response)
    except HTTPException as e:
        return JSendResponse.error(
            message=str(e.detail),
            code=e.status_code
        )
    except Exception as e:
        return JSendResponse.error(
            message=str(e),
            code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@router.post("/user", response_model=JSendResponse[CreateStoreResponse])
async def create_store_legacy(
    store_data: CreateStoreRequest,
    user_id: str = Depends(get_current_user_id)
):
    """
    Creates a new store and associates it with the authenticated user.
    This is a backward-compatible endpoint - use POST /stores/ for new implementations.

    Args:
        store_data: The store information to create
        user_id: The authenticated user ID (injected by dependency)

    Returns:
        JSendResponse with store creation data
    """
    try:
        store_response = save_store_service(user_id, store_data)
        return JSendResponse.success(store_response)
    except HTTPException as e:
        return JSendResponse.error(
            message=str(e.detail),
            code=e.status_code
        )
    except Exception as e:
        return JSendResponse.error(
            message=str(e),
            code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@router.put("/{store_id}", response_model=JSendResponse[dict])
async def update_store(
    store_id: str,
    store_data: UpdateStoreRequest,
    user_store_access: tuple = Depends(get_store_owner_access)
):
    """
    Updates store information. Only store owners can perform this operation.

    Args:
        store_id: The ID of the store to update
        store_data: The store information to update (partial updates allowed)
        user_store_access: Injected dependency that verifies owner access

    Returns:
        JSendResponse with updated store information
    """
    try:
        user_id, store_info = user_store_access
        updated_store = update_store_service(store_id, user_id, store_data)
        return JSendResponse.success(updated_store)
    except HTTPException as e:
        return JSendResponse.error(
            message=str(e.detail),
            code=e.status_code
        )
    except Exception as e:
        return JSendResponse.error(
            message=str(e),
            code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@router.delete("/{store_id}", response_model=JSendResponse[dict])
async def delete_store(
    store_id: str,
    user_id: str = Depends(get_current_user_id)
):
    """
    Deletes a store and all its related data. Only store owners can perform this operation.

    This endpoint will permanently delete:
    - The store document
    - All brands associated with the store
    - All categories associated with the store
    - All products associated with the store
    - All customers associated with the store
    - All staff members associated with the store
    - All sales/transactions associated with the store
    - All reports associated with the store
    - Store references from all user documents

    Args:
        store_id: The ID of the store to delete
        user_id: The authenticated user ID (injected by dependency)

    Returns:
        JSendResponse with deletion confirmation and summary
    """
    try:
        deletion_result = delete_store_service(store_id, user_id)
        return JSendResponse.success(deletion_result)
    except HTTPException as e:
        return JSendResponse.error(
            message=str(e.detail),
            code=e.status_code
        )
    except Exception as e:
        return JSendResponse.error(
            message=str(e),
            code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

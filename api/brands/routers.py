"""
FastAPI routers for brand management endpoints.
Handles HTTP requests and responses for brand operations.
"""

from fastapi import APIRouter, HTTPException, Query, Path, Depends
from starlette import status

from api.auth.dependencies import get_current_user_id, verify_store_access
from api.common.schemas import JSendResponse
from api.brands.schemas import (
    BrandInDB, BrandsData, BrandCreate, BrandUpdate, BrandDetailData,
)
from api.brands.services import (
    get_brands, get_brand_by_id, create_brand,
    update_brand, delete_brand
)

router = APIRouter()


# Create a dependency function for store-based auth
async def get_store_auth(
    store_id: str = Query(..., description="Store ID to access"),
    user_id: str = Depends(get_current_user_id)
) -> tuple[str, dict]:
    """
    Dependency that combines user authentication and store authorization.

    Args:
        store_id: The ID of the store to access (from query parameter)
        user_id: The authenticated user ID (injected by dependency)

    Returns:
        tuple: (user_id, store_info)
    """
    store_info = await verify_store_access(user_id, store_id)
    return user_id, store_info


@router.get("", response_model=JSendResponse[BrandsData])
async def list_brands(
        page: int = Query(1, ge=1, description="Page number"),
        size: int = Query(100, ge=1, le=1000, description="Items per page"),
        sort_by: str = Query("createdAt", description="Field to sort by"),
        sort_order: str = Query("desc", description="Sort order (asc or desc)"),
        auth_info: tuple = Depends(get_store_auth)
):
    """
    Get a list of brands with pagination and product counts for a specific store.

    Args:
        page: The page number (starts at 1)
        size: Number of brands per page (max 1000)
        sort_by: Field to sort the results by
        sort_order: Sort direction ('asc' or 'desc')
        auth_info: Authentication and authorization info (injected)

    Returns:
        JSendResponse containing brands data and pagination info
    """
    try:
        user_id, store_info = auth_info
        store_id = store_info['id']

        # Convert page/size to limit/offset for backend
        offset = (page - 1) * size
        limit = size

        # Get brands with pagination for the specific store
        brands_data = await get_brands(store_id, limit, offset, sort_by, sort_order)
        return JSendResponse.success(brands_data)
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


@router.get("/{brand_id}", response_model=JSendResponse[BrandDetailData])
async def get_brand(
        brand_id: str = Path(..., description="The ID of the brand to retrieve"),
        auth_info: tuple = Depends(get_store_auth)
):
    """
    Get a brand by ID with product count within a specific store.

    Args:
        brand_id: The unique brand identifier
        auth_info: Authentication and authorization info (injected)

    Returns:
        JSendResponse containing the brand data with product count
    """
    try:
        user_id, store_info = auth_info
        store_id = store_info['id']

        brand = await get_brand_by_id(brand_id, store_id)
        return JSendResponse.success(BrandDetailData(item=brand))
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


@router.post("", response_model=JSendResponse[BrandDetailData], status_code=status.HTTP_201_CREATED)
async def create_new_brand(
        brand_data: BrandCreate,
        auth_info: tuple = Depends(get_store_auth)
):
    """
    Create a new brand within a specific store.

    Args:
        brand_data: The brand information to create
        auth_info: Authentication and authorization info (injected)

    Returns:
        JSendResponse containing the created brand data
    """
    try:
        user_id, store_info = auth_info
        store_id = store_info['id']

        # Convert Pydantic model to dict for service layer
        brand_dict = brand_data.model_dump()
        brand_dict['storeId'] = store_id

        created_brand = await create_brand(brand_dict, store_id)
        return JSendResponse.success(BrandDetailData(item=created_brand))
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


@router.put("/{brand_id}", response_model=JSendResponse[BrandDetailData])
async def update_existing_brand(
        brand_id: str = Path(..., description="The ID of the brand to update"),
        brand_data: BrandUpdate = None,
        auth_info: tuple = Depends(get_store_auth)
):
    """
    Update an existing brand within a specific store.

    Args:
        brand_id: The unique brand identifier
        brand_data: The brand information to update
        auth_info: Authentication and authorization info (injected)

    Returns:
        JSendResponse containing the updated brand data with product count
    """
    try:
        user_id, store_info = auth_info
        store_id = store_info['id']

        # Convert Pydantic model to dict for service layer, excluding None values
        update_dict = {}
        if brand_data:
            update_dict = brand_data.model_dump(exclude_unset=True)

        updated_brand = await update_brand(brand_id, update_dict, store_id)
        return JSendResponse.success(BrandDetailData(item=updated_brand))
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


@router.delete("/{brand_id}", response_model=JSendResponse[dict])
async def delete_existing_brand(
        brand_id: str = Path(..., description="The ID of the brand to delete"),
        auth_info: tuple = Depends(get_store_auth)
):
    """
    Delete a brand by ID within a specific store.

    Args:
        brand_id: The unique brand identifier
        auth_info: Authentication and authorization info (injected)

    Returns:
        JSendResponse confirming deletion
    """
    try:
        user_id, store_info = auth_info
        store_id = store_info['id']

        success = await delete_brand(brand_id, store_id)
        if success:
            return JSendResponse.success({"message": "Brand deleted successfully"})
        else:
            return JSendResponse.error(
                message="Failed to delete brand",
                code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
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

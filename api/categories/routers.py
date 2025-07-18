"""
FastAPI routers for category management endpoints.
Handles HTTP requests and responses for category operations.
"""

from fastapi import APIRouter, HTTPException, Query, Path, Depends
from starlette import status

from api.auth.dependencies import get_current_user_id, verify_store_access
from api.common.schemas import JSendResponse
from api.categories.schemas import (
    CategoryInDB, CategoriesData, CategoryCreate, CategoryUpdate, CategoryDetailData,
)
from api.categories.services import (
    get_categories, get_category_by_id, create_category,
    update_category, delete_category, search_categories
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


@router.get("", response_model=JSendResponse[CategoriesData])
async def list_categories(
        page: int = Query(1, ge=1, description="Page number"),
        size: int = Query(100, ge=1, le=1000, description="Items per page"),
        sort_by: str = Query("createdAt", description="Field to sort by"),
        sort_order: str = Query("desc", description="Sort order (asc or desc)"),
        auth_info: tuple = Depends(get_store_auth)
):
    """
    Get a list of categories with pagination for a specific store.

    Args:
        page: The page number (starts at 1)
        size: Number of categories per page (max 1000)
        sort_by: Field to sort the results by
        sort_order: Sort direction ('asc' or 'desc')
        auth_info: Authentication and authorization info (injected)

    Returns:
        JSendResponse containing categories data and pagination info
    """
    try:
        user_id, store_info = auth_info
        store_id = store_info['id']

        # Convert page/size to limit/offset for backend
        offset = (page - 1) * size
        limit = size

        # Get categories with pagination for the specific store
        categories_data = await get_categories(store_id, limit, offset, sort_by, sort_order)
        return JSendResponse.success(categories_data)
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


@router.get("/search", response_model=JSendResponse[CategoriesData])
async def search_categories_endpoint(
        q: str = Query(..., description="Search query"),
        page: int = Query(1, ge=1, description="Page number"),
        size: int = Query(100, ge=1, le=1000, description="Items per page"),
        auth_info: tuple = Depends(get_store_auth)
):
    """
    Search for categories by name within a specific store.

    Args:
        q: The search query
        page: The page number (starts at 1)
        size: Number of categories per page (max 1000)
        auth_info: Authentication and authorization info (injected)

    Returns:
        JSendResponse containing a list of matching categories with product counts
    """
    try:
        user_id, store_info = auth_info
        store_id = store_info['id']

        offset = (page - 1) * size
        limit = size
        categories_data = await search_categories(q, store_id, limit, offset)
        return JSendResponse.success(categories_data)
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


@router.get("/{category_id}", response_model=JSendResponse[CategoryDetailData])
async def get_category(
        category_id: str = Path(..., description="The ID of the category to retrieve"),
        auth_info: tuple = Depends(get_store_auth)
):
    """
    Get a category by ID within a specific store.

    Args:
        category_id: The unique category identifier
        auth_info: Authentication and authorization info (injected)

    Returns:
        JSendResponse containing the category data
    """
    try:
        user_id, store_info = auth_info
        store_id = store_info['id']

        category = await get_category_by_id(category_id, store_id)
        return JSendResponse.success(CategoryDetailData(item=category))
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


@router.post("", response_model=JSendResponse[CategoryDetailData])
async def create_category_endpoint(
    category_data: CategoryCreate,
    auth_info: tuple = Depends(get_store_auth)
):
    """
    Create a new category in a specific store.

    Args:
        category_data: The category data to create (name only)
        auth_info: Authentication and authorization info (injected)

    Returns:
        JSendResponse containing the created category
    """
    try:
        user_id, store_info = auth_info
        store_id = store_info['id']

        # Convert Pydantic model to dict and set storeId from authenticated store
        data = category_data.model_dump()
        data['storeId'] = store_id  # Override any storeId from request body

        created_category = await create_category(data, store_id)
        return JSendResponse.success(CategoryDetailData(item=created_category))
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


@router.put("/{category_id}", response_model=JSendResponse[CategoryInDB])
async def update_existing_category(
        category_id: str = Path(..., description="The ID of the category to update"),
        category_data: CategoryUpdate = ...,
        auth_info: tuple = Depends(get_store_auth)
):
    """
    Update an existing category within a specific store.

    Args:
        category_id: The unique category identifier
        category_data: The category data to update
        auth_info: Authentication and authorization info (injected)

    Returns:
        JSendResponse containing the updated category
    """
    try:
        user_id, store_info = auth_info
        store_id = store_info['id']

        # Filter out None values to avoid overwriting with nulls
        data = {k: v for k, v in category_data.model_dump().items() if v is not None}

        updated_category = await update_category(category_id, data, store_id)
        return JSendResponse.success(updated_category)
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


@router.delete("/{category_id}", response_model=JSendResponse[dict])
async def delete_existing_category(
        category_id: str = Path(..., description="The ID of the category to delete"),
        auth_info: tuple = Depends(get_store_auth)
):
    """
    Delete a category by ID within a specific store.

    Args:
        category_id: The unique category identifier
        auth_info: Authentication and authorization info (injected)

    Returns:
        JSendResponse confirming deletion
    """
    try:
        user_id, store_info = auth_info
        store_id = store_info['id']

        await delete_category(category_id, store_id)
        return JSendResponse.success({"message": "Category deleted successfully"})
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

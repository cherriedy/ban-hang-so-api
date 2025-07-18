"""
This module contains the FastAPI routers for sales endpoints.
"""

from fastapi import APIRouter, HTTPException, Query, Depends
from starlette import status

from api.auth.dependencies import get_current_user_id
from api.common.schemas import JSendResponse
from api.sales.schemas import ProductSaleResponse
from api.sales.services import get_products_for_sale, search_products_for_sale

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
    from api.auth.dependencies import verify_store_access
    store_info = await verify_store_access(user_id, store_id)
    return user_id, store_info


@router.get("/products", response_model=ProductSaleResponse)
async def list_products_for_sale(
        page: int = Query(1, ge=1, description="Page number"),
        size: int = Query(100, ge=1, le=1000, description="Items per page"),
        sort_by: str = Query("createdAt", description="Field to sort by"),
        sort_order: str = Query("desc", description="Sort order (asc or desc)"),
        auth_info: tuple = Depends(get_store_auth)
):
    """
    Get a lightweight list of products for sale with essential fields only.
    Optimized for quick response with minimal data transfer.

    Args:
        page: The page number (starts at 1)
        size: Number of products per page (max 1000)
        sort_by: Field to sort the results by
        sort_order: Sort direction ('asc' or 'desc')
        auth_info: Authentication and authorization info (injected)

    Returns:
        ProductSaleResponse containing essential product data: id, name, thumbnailUrl,
        sellingPrice, purchasePrice, discountPrice, status
    """
    try:
        user_id, store_info = auth_info
        store_id = store_info['id']

        # Convert page/size to limit/offset for backend
        offset = (page - 1) * size
        limit = size

        # Get products with pagination for the specific store (optimized for sale)
        products_data = await get_products_for_sale(
            store_id,
            limit,
            offset,
            sort_by,
            sort_order
        )
        return JSendResponse.success(products_data)
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


@router.get("/products/search", response_model=ProductSaleResponse)
async def search_products_for_sale_endpoint(
        q: str = Query(..., description="Search query"),
        page: int = Query(1, ge=1, description="Page number"),
        size: int = Query(100, ge=1, le=1000, description="Items per page"),
        auth_info: tuple = Depends(get_store_auth)
):
    """
    Search for products for sale with essential fields only.
    Optimized for quick response with minimal data transfer.

    Args:
        q: The search query (searches name, barcode, brand, category, description)
        page: The page number (starts at 1)
        size: Number of products per page (max 1000)
        auth_info: Authentication and authorization info (injected)

    Returns:
        ProductSaleResponse containing essential product data: id, name, thumbnailUrl,
        sellingPrice, purchasePrice, discountPrice, status
    """
    try:
        user_id, store_info = auth_info
        store_id = store_info['id']

        # Convert page/size to limit/offset for backend
        offset = (page - 1) * size
        limit = size

        # Search products with pagination for the specific store (optimized for sale)
        products_data = await search_products_for_sale(q, store_id, limit, offset)
        return JSendResponse.success(products_data)
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

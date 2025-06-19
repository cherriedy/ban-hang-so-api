from fastapi import APIRouter, HTTPException, Query, Path
from starlette import status

from api.common.schemas import JSendResponse
from api.products.schemas import (
    ProductInDB, ProductsData, ProductCreate, ProductUpdate, ProductDetailData
)
from api.products.services import (
    get_products, get_product_by_id, create_product,
    update_product, delete_product, search_products as search_products_service
)

router = APIRouter()


@router.get("", response_model=JSendResponse[ProductsData])
async def list_products(
        page: int = Query(1, ge=1, description="Page number"),
        size: int = Query(100, ge=1, le=1000, description="Items per page"),
        sort_by: str = Query("createdAt", description="Field to sort by"),
        sort_order: str = Query("desc", description="Sort order (asc or desc)")
):
    """
    Get a list of products with pagination.

    Args:
        page: The page number (starts at 1)
        size: Number of products per page (max 1000)
        sort_by: Field to sort the results by
        sort_order: Sort direction ('asc' or 'desc')

    Returns:
        JSendResponse containing products data and pagination info
    """
    try:
        # Convert page/size to limit/offset for backend
        offset = (page - 1) * size
        limit = size

        # Get products with pagination
        products_data = await get_products(limit, offset, sort_by, sort_order)
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


@router.get("/search", response_model=JSendResponse[ProductsData])
async def search_products(q: str = Query(..., description="Search query"),
                          page: int = Query(1, ge=1, description="Page number"),
                          size: int = Query(100, ge=1, le=1000, description="Items per page")):
    """
    Search for products by name, brand, or category.

    Args:
        q: The search query
        page: The page number (starts at 1)
        size: Number of products per page (max 1000)

    Returns:
        JSendResponse containing a list of matching products
    """
    try:
        offset = (page - 1) * size
        limit = size
        products_data = await search_products_service(q, limit, offset)
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


@router.get("/{product_id}", response_model=JSendResponse[ProductDetailData])
async def get_product(product_id: str = Path(..., description="The ID of the product to retrieve")):
    """
    Get a product by ID.

    Args:
        product_id: The unique product identifier

    Returns:
        JSendResponse containing the product data
    """
    try:
        product = await get_product_by_id(product_id)
        return JSendResponse.success(ProductDetailData(item=product))
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


@router.post("", response_model=JSendResponse[ProductInDB])
async def create_new_product(product_data: ProductCreate):
    """
    Create a new product.

    Args:
        product_data: The product data to create

    Returns:
        JSendResponse containing the created product
    """
    try:
        # Filter out None values to avoid overwriting with nulls
        data = {k: v for k, v in product_data.model_dump().items() if v is not None}

        created_product = await create_product(data)
        return JSendResponse.success(created_product)
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


@router.put("/{product_id}", response_model=JSendResponse[ProductInDB])
async def update_existing_product(
        product_id: str = Path(..., description="The ID of the product to update"),
        product_data: ProductUpdate = ...
):
    """
    Update an existing product.

    Args:
        product_id: The unique identifier of the product to update
        product_data: The product data to update

    Returns:
        JSendResponse containing the updated product
    """
    try:
        # Filter out None values to avoid overwriting with nulls
        data = {k: v for k, v in product_data.model_dump().items() if v is not None}

        updated_product = await update_product(product_id, data)
        return JSendResponse.success(updated_product)
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


@router.delete("/{product_id}", response_model=JSendResponse[bool])
async def delete_existing_product(
        product_id: str = Path(..., description="The ID of the product to delete")
):
    """
    Delete a product.

    Args:
        product_id: The unique identifier of the product to delete

    Returns:
        JSendResponse indicating success or failure
    """
    try:
        success = await delete_product(product_id)
        return JSendResponse.success(success)
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

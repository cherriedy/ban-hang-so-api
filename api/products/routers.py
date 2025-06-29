from fastapi import APIRouter, HTTPException, Query, Path, UploadFile, File, Form, Depends
from starlette import status

from api.auth.dependencies import get_authorized_store_access, get_current_user_id, verify_store_access
from api.common.schemas import JSendResponse
from api.common.storage import upload_image
from api.products.schemas import (
    ProductInDB, ProductsData, ProductCreate, ProductUpdate, ProductDetailData,
)
from api.products.services import (
    get_products, get_product_by_id, create_product,
    update_product, delete_product, search_products as search_products_service
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
    from api.auth.dependencies import verify_store_access
    store_info = await verify_store_access(user_id, store_id)
    return user_id, store_info


@router.get("", response_model=JSendResponse[ProductsData])
async def list_products(
        page: int = Query(1, ge=1, description="Page number"),
        size: int = Query(100, ge=1, le=1000, description="Items per page"),
        sort_by: str = Query("createdAt", description="Field to sort by"),
        sort_order: str = Query("desc", description="Sort order (asc or desc)"),
        auth_info: tuple = Depends(get_store_auth)
):
    """
    Get a list of products with pagination for a specific store.

    Args:
        page: The page number (starts at 1)
        size: Number of products per page (max 1000)
        sort_by: Field to sort the results by
        sort_order: Sort direction ('asc' or 'desc')
        auth_info: Authentication and authorization info (injected)

    Returns:
        JSendResponse containing products data and pagination info
    """
    try:
        user_id, store_info = auth_info
        store_id = store_info['id']

        # Convert page/size to limit/offset for backend
        offset = (page - 1) * size
        limit = size

        # Get products with pagination for the specific store
        products_data = await get_products(store_id, limit, offset, sort_by, sort_order)
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
async def search_products(
        q: str = Query(..., description="Search query"),
        page: int = Query(1, ge=1, description="Page number"),
        size: int = Query(100, ge=1, le=1000, description="Items per page"),
        auth_info: tuple = Depends(get_store_auth)
):
    """
    Search for products by name, brand, or category within a specific store.

    Args:
        q: The search query
        page: The page number (starts at 1)
        size: Number of products per page (max 1000)
        auth_info: Authentication and authorization info (injected)

    Returns:
        JSendResponse containing a list of matching products
    """
    try:
        user_id, store_info = auth_info
        store_id = store_info['id']

        offset = (page - 1) * size
        limit = size
        products_data = await search_products_service(q, store_id, limit, offset)
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
async def get_product(
        product_id: str = Path(..., description="The ID of the product to retrieve"),
        auth_info: tuple = Depends(get_store_auth)
):
    """
    Get a product by ID within a specific store.

    Args:
        product_id: The unique product identifier
        auth_info: Authentication and authorization info (injected)

    Returns:
        JSendResponse containing the product data
    """
    try:
        user_id, store_info = auth_info
        store_id = store_info['id']

        product = await get_product_by_id(product_id, store_id)
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
async def create_product_endpoint(
    product_data: ProductCreate,
    user_id: str = Depends(get_current_user_id)
):
    """
    Create a new product in a specific store.

    Args:
        product_data: The product data to create (including storeId)
        user_id: Authenticated user ID (injected)

    Returns:
        JSendResponse containing the created product
    """
    try:
        # Filter out None values to avoid overwriting with nulls
        data = {k: v for k, v in product_data.model_dump().items() if v is not None}

        # Extract storeId from the product data
        store_id = data.get('storeId')
        if not store_id:
            return JSendResponse.error(
                message="storeId is required",
                code=status.HTTP_400_BAD_REQUEST
            )

        # Verify user has access to the store
        await verify_store_access(user_id, store_id)

        created_product = await create_product(data, store_id)
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
        product_data: ProductUpdate = ...,
        auth_info: tuple = Depends(get_store_auth)
):
    """
    Update an existing product within a specific store.

    Args:
        product_id: The unique product identifier
        product_data: The product data to update
        auth_info: Authentication and authorization info (injected)

    Returns:
        JSendResponse containing the updated product
    """
    try:
        user_id, store_info = auth_info
        store_id = store_info['id']

        # Filter out None values to avoid overwriting with nulls
        data = {k: v for k, v in product_data.model_dump().items() if v is not None}

        updated_product = await update_product(product_id, data, store_id)
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


@router.delete("/{product_id}", response_model=JSendResponse[dict])
async def delete_existing_product(
        product_id: str = Path(..., description="The ID of the product to delete"),
        auth_info: tuple = Depends(get_store_auth)
):
    """
    Delete a product by ID within a specific store.

    Args:
        product_id: The unique product identifier
        auth_info: Authentication and authorization info (injected)

    Returns:
        JSendResponse confirming deletion
    """
    try:
        user_id, store_info = auth_info
        store_id = store_info['id']

        await delete_product(product_id, store_id)
        return JSendResponse.success({"message": "Product deleted successfully"})
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


@router.post("/upload-image", response_model=JSendResponse[dict])
async def upload_product_image(file: UploadFile = File(...)):
    """
    Upload an image for a product.

    Args:
        file: The image file to upload

    Returns:
        JSendResponse containing the uploaded image URL
    """
    try:
        image_url = await upload_image(file, folder="products")
        return JSendResponse.success({"imageUrl": image_url})
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

"""
Customer management routers with full CRUD operations.
"""

from fastapi import APIRouter, status, Depends, Path, Query
from fastapi.responses import JSONResponse

from .schemas import (
    CustomerCreate, CustomerUpdate, CustomerCreateResponse, CustomerResponse,
    CustomerListResponse, CustomerDeleteResponseModel
)
from .services import (
    create_customer_service,
    get_customers_list_service,
    get_customer_service,
    update_customer_service,
    delete_customer_service,
    search_customers_service
)
from api.auth.dependencies import get_store_owner_access

router = APIRouter()


@router.post("/", response_model=CustomerCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_customer(
    customer_data: CustomerCreate,
    store_id: str = Query(..., description="Store ID"),
    store_access: tuple[str, dict] = Depends(get_store_owner_access)
):
    """
    Create a new customer.
    Only store owners can create customers for their stores.
    """
    try:
        user_id, store_info = store_access
        result = await create_customer_service(customer_data, store_id)
        return JSONResponse(status_code=status.HTTP_201_CREATED, content=result.model_dump())
    except Exception as e:
        error_response = CustomerCreateResponse.error(str(e), code=status.HTTP_400_BAD_REQUEST)
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content=error_response.model_dump())


@router.get("/", response_model=CustomerListResponse)
async def get_customers_list(
    store_id: str = Query(..., description="Store ID"),
    page: int = Query(1, ge=1, description="Page number (starts from 1)"),
    size: int = Query(10, ge=1, le=100, description="Number of items per page (1-100)"),
    store_access: tuple[str, dict] = Depends(get_store_owner_access)
):
    """
    Get all customers for a store with pagination.
    Only store owners can view customers list.
    """
    try:
        user_id, store_info = store_access
        result = await get_customers_list_service(store_id, page, size)
        return JSONResponse(content=result.model_dump())
    except Exception as e:
        error_response = CustomerListResponse.error(str(e), code=status.HTTP_400_BAD_REQUEST)
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content=error_response.model_dump())


@router.get("/search", response_model=CustomerListResponse)
async def search_customers(
    q: str = Query(..., description="Search query for customers"),
    store_id: str = Query(..., description="Store ID"),
    page: int = Query(1, ge=1, description="Page number (starts from 1)"),
    size: int = Query(10, ge=1, le=100, description="Number of items per page (1-100)"),
    store_access: tuple[str, dict] = Depends(get_store_owner_access)
):
    """
    Search for customers by name, phone, email, or address.
    Only store owners can search for customers.
    """
    try:
        user_id, store_info = store_access
        result = await search_customers_service(q, store_id, page, size)
        return JSONResponse(content=result.model_dump())
    except Exception as e:
        error_response = CustomerListResponse.error(str(e), code=status.HTTP_400_BAD_REQUEST)
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content=error_response.model_dump())


@router.get("/{customer_id}", response_model=CustomerResponse)
async def get_customer(
    customer_id: str = Path(..., description="Customer ID"),
    store_id: str = Query(..., description="Store ID"),
    store_access: tuple[str, dict] = Depends(get_store_owner_access)
):
    """
    Get a specific customer's information.
    Only store owners can view customer details.
    """
    try:
        user_id, store_info = store_access
        result = await get_customer_service(customer_id, store_id)
        return JSONResponse(content=result.model_dump())
    except Exception as e:
        error_response = CustomerResponse.error(str(e), code=status.HTTP_400_BAD_REQUEST)
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content=error_response.model_dump())


@router.put("/{customer_id}", response_model=CustomerResponse)
async def update_customer(
    update_data: CustomerUpdate,
    customer_id: str = Path(..., description="Customer ID"),
    store_id: str = Query(..., description="Store ID"),
    store_access: tuple[str, dict] = Depends(get_store_owner_access)
):
    """
    Update a customer's information.
    Only store owners can update customer details.
    """
    try:
        user_id, store_info = store_access
        result = await update_customer_service(customer_id, store_id, update_data)
        return JSONResponse(content=result.model_dump())
    except Exception as e:
        error_response = CustomerResponse.error(str(e), code=status.HTTP_400_BAD_REQUEST)
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content=error_response.model_dump())


@router.delete("/{customer_id}", response_model=CustomerDeleteResponseModel)
async def delete_customer(
    customer_id: str = Path(..., description="Customer ID"),
    store_id: str = Query(..., description="Store ID"),
    store_access: tuple[str, dict] = Depends(get_store_owner_access)
):
    """
    Delete a customer.
    Only store owners can delete customers.
    """
    try:
        user_id, store_info = store_access
        result = await delete_customer_service(customer_id, store_id)
        return JSONResponse(content=result.model_dump())
    except Exception as e:
        error_response = CustomerDeleteResponseModel.error(str(e), code=status.HTTP_400_BAD_REQUEST)
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content=error_response.model_dump())

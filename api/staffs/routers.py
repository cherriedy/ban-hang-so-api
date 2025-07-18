"""
Staff management routers with full CRUD operations.
"""

from fastapi import APIRouter, status, Depends, Path, Query
from fastapi.responses import JSONResponse

from .schemas import StaffCreate, StaffUpdate, StaffCreateResponse, StaffResponse, StaffListResponse, StaffDeleteResponseModel
from .services import (
    create_staff_service,
    get_staff_list_service,
    get_staff_service,
    update_staff_service,
    delete_staff_service,
    search_staff_service
)
from api.auth.dependencies import get_store_owner_access

router = APIRouter()


@router.post("/", response_model=StaffCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_staff(
    staff_data: StaffCreate,
    store_id: str = Query(..., description="Store ID"),
    store_access: tuple[str, dict] = Depends(get_store_owner_access)
):
    """
    Create a new staff account with auto-generated password.
    Only store owners can create staff accounts for their stores.
    """
    try:
        user_id, store_info = store_access
        result = await create_staff_service(staff_data, store_id)
        return JSONResponse(status_code=status.HTTP_201_CREATED, content=result.model_dump())
    except Exception as e:
        error_response = StaffCreateResponse.error(str(e), code=status.HTTP_400_BAD_REQUEST)
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content=error_response.model_dump())


@router.get("/", response_model=StaffListResponse)
async def get_staff_list(
    store_id: str = Query(..., description="Store ID"),
    page: int = Query(1, ge=1, description="Page number (starts from 1)"),
    size: int = Query(10, ge=1, le=100, description="Number of items per page (1-100)"),
    store_access: tuple[str, dict] = Depends(get_store_owner_access)
):
    """
    Get all staff members for a store with pagination.
    Only store owners can view staff list.
    """
    try:
        user_id, store_info = store_access
        result = await get_staff_list_service(store_id, page, size)
        return JSONResponse(content=result.model_dump())
    except Exception as e:
        error_response = StaffListResponse.error(str(e), code=status.HTTP_400_BAD_REQUEST)
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content=error_response.model_dump())


@router.get("/search", response_model=StaffListResponse)
async def search_staff(
    q: str = Query(..., description="Search query for staff members"),
    store_id: str = Query(..., description="Store ID"),
    page: int = Query(1, ge=1, description="Page number (starts from 1)"),
    size: int = Query(10, ge=1, le=100, description="Number of items per page (1-100)"),
    store_access: tuple[str, dict] = Depends(get_store_owner_access)
):
    """
    Search for staff members by email, display name, or phone number.
    Only store owners can search for staff members.
    """
    try:
        user_id, store_info = store_access
        result = await search_staff_service(q, store_id, page, size)
        return JSONResponse(content=result.model_dump())
    except Exception as e:
        error_response = StaffListResponse.error(str(e), code=status.HTTP_400_BAD_REQUEST)
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content=error_response.model_dump())


@router.get("/{staff_id}", response_model=StaffResponse)
async def get_staff(
    staff_id: str = Path(..., description="Staff member ID"),
    store_id: str = Query(..., description="Store ID"),
    store_access: tuple[str, dict] = Depends(get_store_owner_access)
):
    """
    Get a specific staff member's information.
    Only store owners can view staff details.
    """
    try:
        user_id, store_info = store_access
        result = await get_staff_service(staff_id, store_id)
        return JSONResponse(content=result.model_dump())
    except Exception as e:
        error_response = StaffResponse.error(str(e), code=status.HTTP_400_BAD_REQUEST)
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content=error_response.model_dump())


@router.put("/{staff_id}", response_model=StaffResponse)
async def update_staff(
    update_data: StaffUpdate,
    staff_id: str = Path(..., description="Staff member ID"),
    store_id: str = Query(..., description="Store ID"),
    store_access: tuple[str, dict] = Depends(get_store_owner_access)
):
    """
    Update a staffs member's information.
    Only store owners can update staffs details.
    """
    try:
        user_id, store_info = store_access
        result = await update_staff_service(staff_id, store_id, update_data)
        return JSONResponse(content=result.model_dump())
    except Exception as e:
        error_response = StaffResponse.error(str(e), code=status.HTTP_400_BAD_REQUEST)
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content=error_response.model_dump())


@router.delete("/{staff_id}", response_model=StaffDeleteResponseModel)
async def delete_staff(
    staff_id: str = Path(..., description="Staff member ID"),
    store_id: str = Query(..., description="Store ID"),
    store_access: tuple[str, dict] = Depends(get_store_owner_access)
):
    """
    Remove a staffs member from the store.
    This performs a soft delete by removing the store association.
    Only store owners can remove staffs members.
    """
    try:
        user_id, store_info = store_access
        result = await delete_staff_service(staff_id, store_id)
        return JSONResponse(content=result.model_dump())
    except Exception as e:
        error_response = StaffDeleteResponseModel.error(str(e), code=status.HTTP_400_BAD_REQUEST)
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content=error_response.model_dump())

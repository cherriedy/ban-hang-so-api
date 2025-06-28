from fastapi import APIRouter, HTTPException
from starlette import status

from api.common.schemas import JSendResponse
from api.stores.schemas import CreateStoreRequest, CreateStoreResponse, UserStoresData
from api.stores.services import get_user_stores_service, save_store_service

router = APIRouter()


@router.get("/")
def get_stores():
    return {"message": "Stores endpoint"}


@router.get("/user/{user_id}", response_model=JSendResponse[UserStoresData])
async def get_user_stores(user_id: str):
    """
    Retrieves all stores associated with a user.

    Args:
        user_id: The ID of the user whose stores to retrieve

    Returns:
        JSendResponse containing a list of stores
    """
    try:
        stores_data = get_user_stores_service(user_id)
        return JSendResponse.success(stores_data)
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


@router.post("/user/{user_id}", response_model=JSendResponse[CreateStoreResponse])
async def create_store(user_id: str, store_data: CreateStoreRequest):
    """
    Creates a new store and associates it with a user.

    The store is saved in the Stores collection with the provided data,
    then the store ID is added to the user's document with an ADMIN role.

    Args:
        user_id: The ID of the user who will own the store
        store_data: The store information to create

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


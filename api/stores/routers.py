from fastapi import APIRouter

from api.stores.schemas import UserStoresResponse
from api.stores.services import get_user_stores_service

router = APIRouter()


@router.get("/")
def get_stores():
    return {"message": "Stores endpoint"}


@router.get("/user/{user_id}", response_model=UserStoresResponse)
def get_user_stores(user_id: str):
    """
    Retrieves all stores associated with a user.

    Args:
        user_id: The ID of the user whose stores to retrieve

    Returns:
        Dict containing list of stores
    """
    return get_user_stores_service(user_id)

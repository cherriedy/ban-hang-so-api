from typing import List

from fastapi import APIRouter, HTTPException
from starlette import status

from api.stores.schemas import UserStore
from api.stores.services import get_user_stores_service

router = APIRouter()


@router.get("/")
def get_stores():
    return {"message": "Stores endpoint"}


@router.get("/user/{user_id}", response_model=List[UserStore])
async def get_user_stores(user_id: str):
    """
    Retrieves all stores associated with a user.

    Args:
        user_id: The ID of the user whose stores to retrieve

    Returns:
        List of stores directly without wrapping
    """
    try:
        return await get_user_stores_service(user_id)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

from fastapi import APIRouter, HTTPException, status

from .schemas import UserSignup, UserResponse  # Import UserResponse
from .services import create_user_service

router = APIRouter()


@router.post("/signup", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def signup_user(user_data: UserSignup):
    try:
        return await create_user_service(user_data)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/")
def get_auth():
    return {"message": "Auth endpoint"}

from fastapi import APIRouter, status
from fastapi.responses import JSONResponse

from .schemas import UserSignup, UserResponse  # Import UserResponse
from .services import create_user_service

router = APIRouter()


@router.post("/signup", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def signup_user(user_data: UserSignup):
    try:
        result = await create_user_service(user_data)
        return JSONResponse(status_code=status.HTTP_201_CREATED, content=result.model_dump())
    except Exception as e:
        error_response = UserResponse.error(str(e), code=status.HTTP_400_BAD_REQUEST)
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content=error_response.model_dump())


@router.get("/")
def get_auth():
    return {"message": "Auth endpoint"}

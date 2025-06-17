from fastapi import APIRouter

router = APIRouter()


@router.get("/")
def get_stores():
    return {"message": "Stores endpoint"}

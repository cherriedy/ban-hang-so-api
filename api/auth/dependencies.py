"""
Authentication and authorization dependencies for FastAPI endpoints.
"""

from typing import Optional

from fastapi import HTTPException, Header, Depends
from firebase_admin import auth, firestore


def get_firestore_client():
    return firestore.client()


async def get_current_user_id(authorization: Optional[str] = Header(None)) -> str:
    """
    Extract and verify user ID from Firebase ID token.
    
    Args:
        authorization: Authorization header with Bearer token
        
    Returns:
        str: User ID from verified token
        
    Raises:
        HTTPException: If token is invalid or missing
    """
    if not authorization:
        raise HTTPException(
            status_code=401,
            detail="Authorization header is required"
        )

    try:
        # Extract token from "Bearer <token>" format
        token = authorization.replace("Bearer ", "")
        decoded_token = auth.verify_id_token(token)
        return decoded_token["uid"]
    except Exception as e:
        raise HTTPException(
            status_code=401,
            detail=f"Invalid authentication token: {str(e)}"
        )


async def verify_store_access(user_id: str, store_id: str) -> dict:
    """
    Verify that a user has access to a specific store.
    
    Args:
        user_id: The ID of the user
        store_id: The ID of the store to check access for
        
    Returns:
        dict: Store information from user's stores list
        
    Raises:
        HTTPException: If user doesn't have access to the store
    """
    try:
        db = get_firestore_client()
        user_ref = db.collection('users').document(user_id)
        user_doc = user_ref.get()

        if not user_doc.exists:
            raise HTTPException(
                status_code=404,
                detail="User not found"
            )

        user_data = user_doc.to_dict() or {}
        user_stores = user_data.get('stores', [])

        # Find the store in user's stores list
        user_store = None
        for store in user_stores:
            if store.get('id') == store_id:
                user_store = store
                break

        if not user_store:
            raise HTTPException(
                status_code=403,
                detail="Access denied: User does not have permission to access this store"
            )

        return user_store

    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


async def get_authorized_store_access(
        store_id: str,
        user_id: str = Depends(get_current_user_id)
) -> tuple[str, dict]:
    """
    Dependency that combines user authentication and store authorization.
    
    Args:
        store_id: The ID of the store to access
        user_id: The authenticated user ID (injected by dependency)
        
    Returns:
        tuple: (user_id, store_info)
        
    Raises:
        HTTPException: If authentication fails or user lacks store access
    """
    store_info = await verify_store_access(user_id, store_id)
    return user_id, store_info

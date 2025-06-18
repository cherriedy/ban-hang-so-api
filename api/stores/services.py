from fastapi import HTTPException
from firebase_admin import firestore
from typing import List

from api.stores.schemas import UserStore  # Removed UserStoresResponse as we return List directly


def get_firestore_client():
    return firestore.client()


def get_user_stores_service(user_id: str) -> List[UserStore]:
    """
    Service function to retrieve all stores associated with a user.

    Args:
        user_id: The ID of the user whose stores to retrieve

    Returns:
        List of UserStore objects directly without wrapping

    Raises:
        HTTPException: If user is not found or other errors occur
    """
    if not user_id:
        raise HTTPException(
            status_code=400,
            detail="Missing user ID parameter"
        )

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
        stores = user_data.get('stores', [])
        full_stores = []

        for store in stores:
            store_id = store.get('id')
            role = store.get('role')
            if store_id:
                store_ref = db.collection('stores').document(store_id)
                store_doc = store_ref.get()
                if store_doc.exists:
                    store_data = store_doc.to_dict()
                    store_data['id'] = store_id
                    store_data['role'] = role

                    # Keep timestamp fields as datetime objects for Pydantic model
                    # No need to convert to ISO format as the schema now expects datetime objects

                    full_stores.append(UserStore(**store_data))

        return full_stores  # Return the list directly instead of wrapping it

    except HTTPException:
        # Re-raise HTTP exceptions to preserve status code and detail
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(exc)}"
        )

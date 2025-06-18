from fastapi import HTTPException
from firebase_admin import firestore

from api.stores.schemas import UserStore, CreateStoreRequest, UserStoresData, \
    CreateStoreResponse  # Added CreateStoreResponse


def get_firestore_client():
    return firestore.client()


def get_user_stores_service(user_id: str) -> UserStoresData:
    """
    Service function to retrieve all stores associated with a user.

    Args:
        user_id: The ID of the user whose stores to retrieve

    Returns:
        UserStoresData object containing the list of stores

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

        return UserStoresData(stores=full_stores)  # Return wrapped in UserStoresData

    except HTTPException:
        # Re-raise HTTP exceptions to preserve status code and detail
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(exc)}"
        )


def create_store_service(user_id: str, store_data: CreateStoreRequest) -> CreateStoreResponse:
    """
    Service function to create a new store and associate it with a user.

    Args:
        user_id: The ID of the user who owns the store
        store_data: The store data to create

    Returns:
        CreateStoreResponse object containing the store_id

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

        # Check if user exists
        user_ref = db.collection('users').document(user_id)
        user_doc = user_ref.get()
        if not user_doc.exists:
            raise HTTPException(
                status_code=404,
                detail="User not found"
            )

        # Create store document
        store_dict = {
            "name": store_data.name,
            "description": store_data.description,
            "imageUrl": store_data.imageUrl,
            "createdAt": firestore.firestore.SERVER_TIMESTAMP,
            "updatedAt": firestore.firestore.SERVER_TIMESTAMP
        }

        # Add store to stores collection
        store_ref = db.collection('stores').document()
        store_id = store_ref.id
        store_ref.set(store_dict)

        # Update user document with store reference
        user_data = user_doc.to_dict() or {}
        user_stores = user_data.get('stores', [])

        # Add new store with ADMIN role
        user_stores.append({
            "id": store_id,
            "role": "ADMIN"
        })

        # Update user document
        user_ref.update({"stores": user_stores})

        return CreateStoreResponse(store_id=store_id)

    except HTTPException:
        # Re-raise HTTP exceptions to preserve status code and detail
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(exc)}"
        )

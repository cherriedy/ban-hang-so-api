from fastapi import HTTPException
from firebase_admin import firestore
import math

from api.stores.schemas import UserStore, CreateStoreRequest, UserStoresData, \
    CreateStoreResponse, UpdateStoreRequest, StoreDetail, StoreDetailData  # Added StoreDetailData


def get_firestore_client():
    return firestore.client()


def get_store_detail_service(store_id: str, user_id: str) -> StoreDetailData:
    """
    Service function to retrieve detailed information about a store.
    Only store owners can access this information.

    Args:
        store_id: The ID of the store to retrieve details for
        user_id: The ID of the user requesting the store details

    Returns:
        StoreDetail object containing the store information

    Raises:
        HTTPException: If store is not found, user lacks permission, or other errors occur
    """
    print(f"DEBUG: get_store_detail_service called with store_id={store_id}, user_id={user_id}")

    if not store_id or not user_id:
        raise HTTPException(
            status_code=400,
            detail="Missing store ID or user ID parameter"
        )

    try:
        db = get_firestore_client()

        # Check if store exists
        print(f"DEBUG: Checking if store {store_id} exists")
        store_ref = db.collection('stores').document(store_id)
        store_doc = store_ref.get()
        if not store_doc.exists:
            print(f"DEBUG: Store {store_id} does not exist")
            raise HTTPException(
                status_code=404,
                detail=f"Store with ID {store_id} not found"
            )

        store_data = store_doc.to_dict()
        print(f"DEBUG: Store data retrieved: {store_data}")

        # Check if the store has an owner field that matches the user
        store_owner_id = store_data.get('ownerId') or store_data.get('owner_id')
        print(f"DEBUG: Store owner ID from store document: {store_owner_id}")

        if store_owner_id == user_id:
            print(f"DEBUG: User {user_id} is direct owner of store")
            # User is the direct owner of the store
            store_data['id'] = store_id
            store_detail = StoreDetail(**store_data)
            return StoreDetailData(item=store_detail)

        # Alternative: Check if user exists in Firestore and has access
        print(f"DEBUG: Checking user {user_id} in Firestore")
        user_ref = db.collection('users').document(user_id)
        user_doc = user_ref.get()

        if user_doc.exists:
            print(f"DEBUG: User document exists")
            user_data = user_doc.to_dict() or {}
            user_stores = user_data.get('stores', [])
            print(f"DEBUG: User stores: {user_stores}")

            # Find user's role for this store
            user_store_role = None
            for store in user_stores:
                print(f"DEBUG: Checking store in user's stores: {store}")
                if store.get('id') == store_id:
                    user_store_role = store.get('role')
                    print(f"DEBUG: Found matching store! Role: {user_store_role}")
                    break

            print(f"DEBUG: Final user_store_role: {user_store_role}")

            # Check if user has owner/admin permissions
            if user_store_role in ['owner', 'ADMIN']:
                print(f"DEBUG: User has permission, returning store data")
                store_data['id'] = store_id
                store_detail = StoreDetail(**store_data)
                return StoreDetailData(item=store_detail)
            else:
                print(f"DEBUG: User role '{user_store_role}' not in ['owner', 'ADMIN']")
        else:
            print(f"DEBUG: User document does not exist")

        # If we reach here, user doesn't have access
        print(f"DEBUG: Access denied for user {user_id} to store {store_id}")
        raise HTTPException(
            status_code=403,
            detail="Access denied: Only store owners can view store details"
        )

    except HTTPException:
        # Re-raise HTTP exceptions to preserve status code and detail
        raise
    except Exception as exc:
        print(f"DEBUG: Exception occurred: {exc}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(exc)}"
        )


def get_user_stores_service(user_id: str, page: int = 1, size: int = 10) -> UserStoresData:
    """
    Service function to retrieve stores associated with a user with pagination support.

    Args:
        user_id: The ID of the user whose stores to retrieve
        page: Page number (starts from 1)
        size: Number of items per page

    Returns:
        UserStoresData object containing the paginated list of stores

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

        # Calculate pagination
        total = len(full_stores)
        pages = math.ceil(total / size) if total > 0 else 1
        start_index = (page - 1) * size
        end_index = start_index + size

        # Get paginated items
        paginated_stores = full_stores[start_index:end_index]

        # Return paginated response
        return UserStoresData(
            items=paginated_stores,
            total=total,
            page=page,
            size=size,
            pages=pages
        )

    except HTTPException:
        # Re-raise HTTP exceptions to preserve status code and detail
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(exc)}"
        )


def save_store_service(user_id: str, store_data: CreateStoreRequest) -> CreateStoreResponse:
    """
    Service function to create a new store or update an existing one and associate it with a user.

    Args:
        user_id: The ID of the user who owns the store
        store_data: The store data to create or update

    Returns:
        CreateStoreResponse object containing the store_id

    Raises:
        HTTPException: If user is not found, store is not found, or other errors occur
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

        # Extract user data
        user_data = user_doc.to_dict() or {}
        user_stores = user_data.get('stores', [])

        # Check if we're updating an existing store (store_id is provided)
        store_id = getattr(store_data, 'id', None)
        if store_id:
            # Validate that the store exists
            store_ref = db.collection('stores').document(store_id)
            store_doc = store_ref.get()
            if not store_doc.exists:
                raise HTTPException(
                    status_code=404,
                    detail=f"Store with ID {store_id} not found"
                )

            # Check if user has access to this store
            user_has_access = any(store.get('id') == store_id for store in user_stores)
            if not user_has_access:
                raise HTTPException(
                    status_code=403,
                    detail=f"User does not have access to store with ID {store_id}"
                )

            # Update store document
            store_dict = {
                "name": store_data.name,
                "description": store_data.description,
                "updatedAt": firestore.firestore.SERVER_TIMESTAMP
            }

            # Only update imageUrl if provided
            if store_data.imageUrl is not None:
                store_dict["imageUrl"] = store_data.imageUrl

            # Update the existing store
            store_ref.update(store_dict)
        else:
            # Create new store document
            store_dict = {
                "name": store_data.name,
                "description": store_data.description,
                "createdAt": firestore.firestore.SERVER_TIMESTAMP,
                "updatedAt": firestore.firestore.SERVER_TIMESTAMP
            }

            # Add imageUrl if provided
            if store_data.imageUrl is not None:
                store_dict["imageUrl"] = store_data.imageUrl

            # Add store to stores collection
            store_ref = db.collection('stores').document()
            store_id = store_ref.id
            store_ref.set(store_dict)

            # Add new store with ADMIN role to user's stores
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


def update_store_service(store_id: str, user_id: str, store_data: UpdateStoreRequest) -> dict:
    """
    Service function to update store information. Only store owners can perform this operation.

    Args:
        store_id: The ID of the store to update
        user_id: The ID of the user requesting the update
        store_data: The store data to update

    Returns:
        dict: Updated store information

    Raises:
        HTTPException: If store is not found, user lacks permission, or other errors occur
    """
    if not store_id or not user_id:
        raise HTTPException(
            status_code=400,
            detail="Missing store ID or user ID parameter"
        )

    try:
        db = get_firestore_client()

        # Check if store exists
        store_ref = db.collection('stores').document(store_id)
        store_doc = store_ref.get()
        if not store_doc.exists:
            raise HTTPException(
                status_code=404,
                detail=f"Store with ID {store_id} not found"
            )

        # Check if user has owner access to this store
        user_ref = db.collection('users').document(user_id)
        user_doc = user_ref.get()
        if not user_doc.exists:
            raise HTTPException(
                status_code=404,
                detail="User not found"
            )

        user_data = user_doc.to_dict() or {}
        user_stores = user_data.get('stores', [])

        # Find user's role for this store
        user_store_role = None
        for store in user_stores:
            if store.get('id') == store_id:
                user_store_role = store.get('role')
                break

        # Check if user has owner/admin permissions
        if user_store_role not in ['owner', 'ADMIN']:
            raise HTTPException(
                status_code=403,
                detail="Access denied: Only store owners can update store information"
            )

        # Build update dictionary with only provided fields
        update_dict = {"updatedAt": firestore.firestore.SERVER_TIMESTAMP}

        if store_data.name is not None:
            update_dict["name"] = store_data.name
        if store_data.description is not None:
            update_dict["description"] = store_data.description
        if store_data.imageUrl is not None:
            update_dict["imageUrl"] = store_data.imageUrl

        # Update the store
        store_ref.update(update_dict)

        # Return updated store data
        updated_store_doc = store_ref.get()
        updated_store_data = updated_store_doc.to_dict()
        updated_store_data['id'] = store_id

        return updated_store_data

    except HTTPException:
        # Re-raise HTTP exceptions to preserve status code and detail
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(exc)}"
        )


def delete_store_service(store_id: str, user_id: str) -> dict:
    """
    Service function to delete a store and all its related data.
    Only store owners can perform this operation.

    This will delete:
    - The store document from the 'stores' collection
    - Remove store reference from all users' stores arrays
    - All brands associated with the store
    - All categories associated with the store
    - All products associated with the store
    - All customers associated with the store
    - All staff members associated with the store
    - All sales/transactions associated with the store
    - All reports associated with the store

    Args:
        store_id: The ID of the store to delete
        user_id: The ID of the user requesting the deletion

    Returns:
        dict: Success message with deleted store information

    Raises:
        HTTPException: If store is not found, user lacks permission, or other errors occur
    """
    print(f"DEBUG: delete_store_service called with store_id={store_id}, user_id={user_id}")

    if not store_id or not user_id:
        raise HTTPException(
            status_code=400,
            detail="Missing store ID or user ID parameter"
        )

    try:
        db = get_firestore_client()

        # First, verify the store exists and user has owner permissions
        store_ref = db.collection('stores').document(store_id)
        store_doc = store_ref.get()

        if not store_doc.exists:
            print(f"DEBUG: Store {store_id} does not exist")
            raise HTTPException(
                status_code=404,
                detail=f"Store with ID {store_id} not found"
            )

        store_data = store_doc.to_dict()
        print(f"DEBUG: Store data retrieved for deletion: {store_data}")

        # Check user permissions - similar logic to get_store_detail_service
        user_ref = db.collection('users').document(user_id)
        user_doc = user_ref.get()

        if not user_doc.exists:
            raise HTTPException(
                status_code=404,
                detail="User not found"
            )

        user_data = user_doc.to_dict() or {}
        user_stores = user_data.get('stores', [])

        # Find user's role for this store
        user_store_role = None
        for store in user_stores:
            if store.get('id') == store_id:
                user_store_role = store.get('role')
                break

        # Only owners/ADMIN can delete stores
        if user_store_role not in ['owner', 'ADMIN']:
            print(f"DEBUG: Access denied for user {user_id} to delete store {store_id}")
            raise HTTPException(
                status_code=403,
                detail="Access denied: Only store owners can delete stores"
            )

        print(f"DEBUG: User {user_id} has permission to delete store {store_id}")

        # Use batch operations for atomic deletion
        batch = db.batch()
        deletion_count = {'total': 0}

        # Helper function to delete collection documents in batches
        def delete_collection_documents(collection_name: str, field_name: str):
            collection_ref = db.collection(collection_name)
            docs = collection_ref.where(field_name, '==', store_id).stream()
            count = 0
            for doc in docs:
                batch.delete(doc.reference)
                count += 1
            deletion_count[collection_name] = count
            deletion_count['total'] += count
            print(f"DEBUG: Marked {count} documents from {collection_name} collection for deletion")

        # Delete all related data
        print("DEBUG: Starting deletion of related collections...")

        # Delete brands associated with the store
        delete_collection_documents('brands', 'storeId')

        # Delete categories associated with the store
        delete_collection_documents('categories', 'storeId')

        # Delete products associated with the store
        delete_collection_documents('products', 'storeId')

        # Delete customers associated with the store
        delete_collection_documents('customers', 'storeId')

        # Delete staff members associated with the store
        delete_collection_documents('staffs', 'storeId')

        # Delete sales/transactions associated with the store
        delete_collection_documents('sales', 'storeId')
        delete_collection_documents('transactions', 'storeId')

        # Delete reports associated with the store
        delete_collection_documents('reports', 'storeId')

        # Remove store from all users' stores arrays
        print("DEBUG: Removing store reference from all users...")
        users_collection = db.collection('users')
        users_with_store = users_collection.where('stores', 'array_contains', {'id': store_id, 'role': 'owner'}).stream()

        users_updated = 0
        for user_doc in users_with_store:
            user_data = user_doc.to_dict() or {}
            user_stores = user_data.get('stores', [])

            # Remove the store from user's stores array
            updated_stores = [store for store in user_stores if store.get('id') != store_id]

            if len(updated_stores) != len(user_stores):  # Only update if there was a change
                batch.update(user_doc.reference, {'stores': updated_stores})
                users_updated += 1

        # Also remove from the current user (in case role matching didn't catch it)
        current_user_stores = [store for store in user_stores if store.get('id') != store_id]
        if len(current_user_stores) != len(user_stores):
            batch.update(user_ref, {'stores': current_user_stores})
            users_updated += 1

        deletion_count['users_updated'] = users_updated
        print(f"DEBUG: Marked {users_updated} user documents for store reference removal")

        # Finally, delete the store document itself
        batch.delete(store_ref)
        deletion_count['stores'] = 1
        deletion_count['total'] += 1

        # Commit all deletions
        print(f"DEBUG: Committing batch deletion of {deletion_count['total']} documents...")
        batch.commit()

        print(f"DEBUG: Store {store_id} and all related data successfully deleted")

        return {
            "message": f"Store '{store_data.get('name', store_id)}' and all related data successfully deleted",
            "store_id": store_id,
            "deletion_summary": deletion_count
        }

    except HTTPException:
        # Re-raise HTTP exceptions to preserve status code and detail
        raise
    except Exception as exc:
        print(f"DEBUG: Exception occurred during store deletion: {exc}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error during store deletion: {str(exc)}"
        )

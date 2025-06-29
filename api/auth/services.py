from firebase_admin import auth, firestore
from datetime import datetime

from .schemas import UserSignup, UserResponse, StoreInUser, UserBase  # Added UserBase

db = firestore.client()


async def create_user_service(user_data: UserSignup) -> UserResponse:  # Changed return type annotation
    """Create user in Firebase Auth and Firestore with rollback support"""
    user_record = None
    store_ref = None
    try:
        # Validate input based on role
        if user_data.role == "owner" and not user_data.storeInfo:
            raise ValueError("Store information is required for owner role")
        if user_data.role == "staff" and not user_data.storeId:
            raise ValueError("Store ID is required for staff role")
        if user_data.role not in ["owner", "staff"]:
            raise ValueError("Role must be either 'owner' or 'staff'")

        # If staff role, validate that the store exists
        if user_data.role == "staff":
            store_ref = db.collection('stores').document(user_data.storeId)
            store_doc = store_ref.get()
            if not store_doc.exists:
                raise ValueError(f"Store with ID {user_data.storeId} does not exist")

        # Create user in Firebase Auth
        try:
            user_record = auth.create_user(
                email=user_data.email,
                password=user_data.password,
                display_name=user_data.displayName,
                photo_url=user_data.imageUrl
            )
        except auth.EmailAlreadyExistsError:
            return UserResponse.error("Email is already in use.", code=409)

        # Handle store creation/assignment based on role
        stores_list = []
        if user_data.role == "owner":
            # Create new store
            store_dict = {
                "name": user_data.storeInfo.name,
                "description": user_data.storeInfo.description,
                "createdAt": firestore.firestore.SERVER_TIMESTAMP,
                "updatedAt": firestore.firestore.SERVER_TIMESTAMP
            }

            if user_data.storeInfo.imageUrl:
                store_dict["imageUrl"] = user_data.storeInfo.imageUrl

            # Add store to stores collection
            store_ref = db.collection('stores').document()
            store_id = store_ref.id
            store_ref.set(store_dict)

            # Add store with ADMIN role to user's stores
            stores_list = [{
                "id": store_id,
                "role": "ADMIN"
            }]

        elif user_data.role == "staff":
            # Add existing store with STAFF role to user's stores
            stores_list = [{
                "id": user_data.storeId,
                "role": "STAFF"
            }]

        # Prepare user document for Firestore
        user_doc_data = {
            "email": user_data.email,
            "phone": user_data.phone,
            "contactName": user_data.displayName,
            "imageUrl": user_data.imageUrl,
            "createdAt": firestore.firestore.SERVER_TIMESTAMP,
            "updatedAt": firestore.firestore.SERVER_TIMESTAMP,
            "stores": stores_list
        }

        doc_ref = db.collection('users').document(user_record.uid)
        doc_ref.set(user_doc_data)

        # Fetch the created document to get server timestamps and other data
        created_user_doc = doc_ref.get()
        if not created_user_doc.exists:
            raise Exception("Failed to retrieve created user document from Firestore")

        user_doc_dict = created_user_doc.to_dict()

        # Convert Firestore timestamps to Python datetime objects
        created_at = user_doc_dict.get("createdAt")
        updated_at = user_doc_dict.get("updatedAt")

        if hasattr(created_at, 'timestamp'):
            created_at = datetime.fromtimestamp(created_at.timestamp())
        if hasattr(updated_at, 'timestamp'):
            updated_at = datetime.fromtimestamp(updated_at.timestamp())

        # Ensure stores is an empty list if not present or None (it should be [] from user_doc_data)
        stores_data = user_doc_dict.get("stores", [])
        stores_models = [StoreInUser(**store) for store in stores_data]  # Convert store data to StoreInUser models

        user_base = UserBase(
            id=user_record.uid,  # Add the user ID from Firebase Auth
            email=user_doc_dict.get("email"),
            contactName=user_doc_dict.get("contactName"),
            phone=user_doc_dict.get("phone"),
            imageUrl=user_doc_dict.get("imageUrl"),
            stores=stores_models,
            createdAt=created_at,
            updatedAt=updated_at
        )

        return UserResponse.success(user_base)
    except Exception as e:
        # Comprehensive rollback logic
        rollback_errors = []

        # Rollback Firebase Auth user if it was created
        if user_record:
            try:
                auth.delete_user(user_record.uid)
                print(f"Successfully rolled back Firebase Auth user: {user_record.uid}")
            except Exception as rollback_error:
                rollback_errors.append(f"Failed to rollback Firebase Auth user: {str(rollback_error)}")

        # Rollback store creation if it was created (only for owner role)
        if store_ref and user_data.role == "owner":
            try:
                store_ref.delete()
                print(f"Successfully rolled back store creation")
            except Exception as rollback_error:
                rollback_errors.append(f"Failed to rollback store creation: {str(rollback_error)}")

        # Log all rollback errors if any occurred
        if rollback_errors:
            for error in rollback_errors:
                print(f"Rollback error: {error}")

        # Re-raise the original exception
        raise e

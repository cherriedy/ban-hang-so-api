from firebase_admin import auth, firestore

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
        user_record = auth.create_user(
            email=user_data.email,
            password=user_data.password,
            display_name=user_data.displayName,
            photo_url=user_data.imageUrl
        )

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

        # Ensure stores is an empty list if not present or None (it should be [] from user_doc_data)
        stores_data = user_doc_dict.get("stores", [])
        stores_models = [StoreInUser(**store) for store in stores_data]  # Convert store data to StoreInUser models

        user_base = UserBase(
            email=user_doc_dict.get("email"),
            contactName=user_doc_dict.get("contactName"),
            phone=user_doc_dict.get("phone"),
            imageUrl=user_doc_dict.get("imageUrl"),
            stores=stores_models,
            createdAt=user_doc_dict.get("createdAt"),
            updatedAt=user_doc_dict.get("updatedAt")
        )

        return UserResponse.success(user_base)
    except Exception as e:
        # Rollback if Auth succeeded but Firestore failed
        if user_record:
            try:
                auth.delete_user(user_record.uid)
            except Exception as rollback_error:
                print(f"Rollback failed: {str(rollback_error)}")

        # Rollback store creation if it was created
        if store_ref and user_data.role == "owner":
            try:
                store_ref.delete()
            except Exception as rollback_error:
                print(f"Store rollback failed: {str(rollback_error)}")

        raise e

from firebase_admin import auth, firestore

from .schemas import UserSignup, UserResponse, StoreInUser  # Added UserResponse and StoreInUser

db = firestore.client()


async def create_user_service(user_data: UserSignup) -> UserResponse:  # Changed return type annotation
    """Create user in Firebase Auth and Firestore with rollback support"""
    user_record = None
    try:
        # Create user in Firebase Auth
        user_record = auth.create_user(
            email=user_data.email,
            password=user_data.password,
            display_name=user_data.displayName,
            photo_url=user_data.imageUrl
        )

        # Prepare user document for Firestore
        user_doc_data = {
            "email": user_data.email,
            "phone": user_data.phone,
            "contactName": user_data.displayName,
            "imageUrl": user_data.imageUrl,
            "createdAt": firestore.firestore.SERVER_TIMESTAMP,
            "updatedAt": firestore.firestore.SERVER_TIMESTAMP,
            "stores": []  # New users will have an empty list of stores
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
        stores_list = [StoreInUser(**store) for store in stores_data]  # Convert store data to StoreInUser models

        return UserResponse(
            email=user_doc_dict.get("email"),
            contactName=user_doc_dict.get("contactName"),
            phone=user_doc_dict.get("phone"),
            imageUrl=user_doc_dict.get("imageUrl"),
            createdAt=user_doc_dict.get("createdAt"),
            updatedAt=user_doc_dict.get("updatedAt"),
            stores=stores_list
        )
    except Exception as e:
        # Rollback if Auth succeeded but Firestore failed
        if user_record:
            try:
                auth.delete_user(user_record.uid)
            except Exception as rollback_error:
                print(f"Rollback failed: {str(rollback_error)}")
        raise e

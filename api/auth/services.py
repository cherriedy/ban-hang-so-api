from datetime import datetime
import secrets
import string

from firebase_admin import auth, firestore

from .schemas import UserSignup, UserResponse, StoreInUser, UserBase, StaffAccountCreate
from api.common.email_service import email_service

db = firestore.client()


def generate_password(length: int = 12) -> str:
    """Generate a secure random password."""
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    password = ''.join(secrets.choice(alphabet) for _ in range(length))
    return password


async def create_user_service(user_data: UserSignup) -> UserResponse:  # Changed return type annotation
    """Create user in Firebase Auth and Firestore with rollback support"""
    user_record = None
    store_ref = None
    try:
        # Validate input based on role
        if user_data.role == "owner" and not user_data.storeInfo:
            raise ValueError("Store information is required for owner role")
        if user_data.role == "staffs" and not user_data.storeId:
            raise ValueError("Store ID is required for staffs role")
        if user_data.role not in ["owner", "staffs"]:
            raise ValueError("Role must be either 'owner' or 'staffs'")

        # If staffs role, validate that the store exists
        if user_data.role == "staffs":
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

            # Add store with owner role to user's stores
            stores_list = [{
                "id": store_id,
                "role": "owner"
            }]

        elif user_data.role == "staffs":
            # Add existing store with staffs role remto user's stores
            stores_list = [{
                "id": user_data.storeId,
                "role": "staffs"
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


async def create_staff_account_service(staff_data: StaffAccountCreate, store_id: str) -> UserResponse:
    """Create staffs account with auto-generated password and send credentials via email"""
    user_record = None
    generated_password = None

    try:
        # Validate that the store exists
        store_ref = db.collection('stores').document(store_id)
        store_doc = store_ref.get()
        if not store_doc.exists:
            raise ValueError(f"Store with ID {store_id} does not exist")

        # Generate secure password
        generated_password = generate_password()

        # Create user in Firebase Auth
        try:
            user_record = auth.create_user(
                email=staff_data.email,
                password=generated_password,
                display_name=staff_data.displayName,
                photo_url=staff_data.imageUrl
            )
        except auth.EmailAlreadyExistsError:
            return UserResponse.error("Email is already in use.", code=409)

        # Prepare user document for Firestore with staffs role
        stores_list = [{
            "id": store_id,
            "role": "staffs"
        }]

        user_doc_data = {
            "email": staff_data.email,
            "phone": staff_data.phone,
            "contactName": staff_data.displayName,
            "imageUrl": staff_data.imageUrl,
            "createdAt": firestore.firestore.SERVER_TIMESTAMP,
            "updatedAt": firestore.firestore.SERVER_TIMESTAMP,
            "stores": stores_list
        }

        doc_ref = db.collection('users').document(user_record.uid)
        doc_ref.set(user_doc_data)

        # Send credentials email
        await email_service.send_staff_credentials_email(
            to_email=staff_data.email,
            password=generated_password,
            staff_name=staff_data.displayName
        )

        # Fetch the created document to get server timestamps
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

        # Create response data
        stores_data = user_doc_dict.get("stores", [])
        stores_models = [StoreInUser(**store) for store in stores_data]

        user_base = UserBase(
            id=user_record.uid,
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
        # Rollback Firebase Auth user if it was created
        if user_record:
            try:
                auth.delete_user(user_record.uid)
                print(f"Successfully rolled back Firebase Auth user: {user_record.uid}")
            except Exception as rollback_error:
                print(f"Failed to rollback Firebase Auth user: {str(rollback_error)}")

        # Re-raise the original exception
        raise e

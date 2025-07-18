"""
Staff management services for CRUD operations.
"""

import secrets
import string
from datetime import datetime
from typing import List, Optional

from firebase_admin import auth, firestore
from fastapi import HTTPException

from .schemas import StaffCreate, StaffUpdate, StaffInfo, StaffCreateResponse, StaffResponse, StaffListResponse, StaffCredentials, StaffItemResponse, StaffDeleteResponse, StaffDeleteResponseModel
from api.common.email_service import email_service
from api.common.schemas import OWNER_ROLE, STAFF_ROLE, PaginationResponse

db = firestore.client()


def generate_password(length: int = 12) -> str:
    """Generate a secure random password."""
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    password = ''.join(secrets.choice(alphabet) for _ in range(length))
    return password


async def create_staff_service(staff_data: StaffCreate, store_id: str) -> StaffCreateResponse:
    """Create a new staffs account with auto-generated password."""
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
            return StaffCreateResponse.error("Email is already in use.", code=409)

        # Prepare user document for Firestore with staffs role
        stores_list = [{
            "id": store_id,
            "role": STAFF_ROLE
        }]

        user_doc_data = {
            "email": staff_data.email,
            "phone": staff_data.phone,
            "contactName": staff_data.displayName,
            "imageUrl": staff_data.imageUrl,
            "active": True,
            "createdAt": firestore.firestore.SERVER_TIMESTAMP,
            "updatedAt": firestore.firestore.SERVER_TIMESTAMP,
            "stores": stores_list
        }

        doc_ref = db.collection('users').document(user_record.uid)
        doc_ref.set(user_doc_data)

        # Send credentials email
        try:
            await email_service.send_staff_credentials_email(
                to_email=staff_data.email,
                password=generated_password,
                staff_name=staff_data.displayName
            )
        except Exception as email_error:
            print(f"Warning: Failed to send email: {str(email_error)}")
            # Continue without failing the entire operation

        # Return credentials response
        credentials = StaffCredentials(
            email=str(staff_data.email)
        )

        return StaffCreateResponse.success(credentials)

    except Exception as e:
        # Rollback Firebase Auth user if it was created
        if user_record:
            try:
                auth.delete_user(user_record.uid)
                print(f"Successfully rolled back Firebase Auth user: {user_record.uid}")
            except Exception as rollback_error:
                print(f"Failed to rollback Firebase Auth user: {str(rollback_error)}")

        raise e


async def get_staff_list_service(store_id: str, page: int = 1, size: int = 10) -> StaffListResponse:
    """Get all staff members for a store with pagination."""
    try:
        # Query users collection for staff members of this store
        users_ref = db.collection('users')

        # Get all users and filter by store
        users_query = users_ref.stream()
        all_staff = []

        for user_doc in users_query:
            user_data = user_doc.to_dict()
            if not user_data:
                continue

            stores = user_data.get('stores', [])

            # Check if user is staff in this store
            for store in stores:
                if store.get('id') == store_id and store.get('role') == STAFF_ROLE:
                    staff_info = StaffInfo(
                        id=user_doc.id,
                        email=user_data.get('email', ''),
                        displayName=user_data.get('contactName'),
                        phone=user_data.get('phone'),
                        imageUrl=user_data.get('imageUrl'),
                        active=user_data.get('active', True),
                        storeId=store_id,
                        role=STAFF_ROLE,
                        createdAt=_convert_timestamp(user_data.get('createdAt')),
                        updatedAt=_convert_timestamp(user_data.get('updatedAt'))
                    )
                    all_staff.append(staff_info)
                    break

        # Calculate pagination
        total = len(all_staff)
        pages = (total + size - 1) // size  # Ceiling division
        start_index = (page - 1) * size
        end_index = start_index + size

        # Get paginated items
        paginated_staff = all_staff[start_index:end_index]

        # Wrap staff list in items property with pagination info
        staff_list_data = PaginationResponse(
            items=paginated_staff,
            total=total,
            page=page,
            size=size,
            pages=pages
        )
        return StaffListResponse.success(staff_list_data)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve staff list: {str(e)}")


async def get_staff_service(staff_id: str, store_id: str) -> StaffResponse:
    """Get a specific staffs member."""
    try:
        user_ref = db.collection('users').document(staff_id)
        user_doc = user_ref.get()

        if not user_doc.exists:
            return StaffResponse.error("Staff member not found", code=404)

        user_data = user_doc.to_dict()
        stores = user_data.get('stores', [])

        # Verify staffs member belongs to the store (allow both staff and owner roles)
        is_staff_in_store = False
        user_role = None
        for store in stores:
            if store.get('id') == store_id and store.get('role') in [STAFF_ROLE, OWNER_ROLE]:
                is_staff_in_store = True
                user_role = store.get('role')
                break

        if not is_staff_in_store:
            return StaffResponse.error("Staff member not found in this store", code=404)

        staff_info = StaffInfo(
            id=staff_id,
            email=user_data.get('email', ''),
            displayName=user_data.get('contactName'),
            phone=user_data.get('phone'),
            imageUrl=user_data.get('imageUrl'),
            active=user_data.get('active', True),
            storeId=store_id,
            role=user_role,  # Use the actual role from the store data
            createdAt=_convert_timestamp(user_data.get('createdAt')),
            updatedAt=_convert_timestamp(user_data.get('updatedAt'))
        )

        staff_item = StaffItemResponse(item=staff_info)
        return StaffResponse.success(staff_item)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve staffs member: {str(e)}")


async def update_staff_service(staff_id: str, store_id: str, update_data: StaffUpdate) -> StaffResponse:
    """Update a staffs member's information."""
    try:
        user_ref = db.collection('users').document(staff_id)
        user_doc = user_ref.get()

        if not user_doc.exists:
            return StaffResponse.error("Staff member not found", code=404)

        user_data = user_doc.to_dict()
        stores = user_data.get('stores', [])

        # Verify staffs member belongs to the store
        is_staff_in_store = False
        for store in stores:
            if store.get('id') == store_id and store.get('role') == STAFF_ROLE:
                is_staff_in_store = True
                break

        if not is_staff_in_store:
            return StaffResponse.error("Staff member not found in this store", code=404)

        # Prepare update data
        update_dict = {"updatedAt": firestore.firestore.SERVER_TIMESTAMP}

        if update_data.displayName is not None:
            update_dict["contactName"] = update_data.displayName
            # Also update Firebase Auth display name
            try:
                auth.update_user(staff_id, display_name=update_data.displayName)
            except Exception as auth_error:
                print(f"Warning: Failed to update Firebase Auth display name: {str(auth_error)}")

        if update_data.phone is not None:
            update_dict["phone"] = update_data.phone

        if update_data.imageUrl is not None:
            update_dict["imageUrl"] = update_data.imageUrl
            # Also update Firebase Auth photo URL
            try:
                auth.update_user(staff_id, photo_url=update_data.imageUrl)
            except Exception as auth_error:
                print(f"Warning: Failed to update Firebase Auth photo URL: {str(auth_error)}")

        if update_data.active is not None:
            update_dict["active"] = update_data.active
            # Disable/enable Firebase Auth user
            try:
                auth.update_user(staff_id, disabled=not update_data.active)
            except Exception as auth_error:
                print(f"Warning: Failed to update Firebase Auth status: {str(auth_error)}")

        # Update Firestore document
        user_ref.update(update_dict)

        # Get updated document
        updated_doc = user_ref.get()
        updated_data = updated_doc.to_dict()

        staff_info = StaffInfo(
            id=staff_id,
            email=updated_data.get('email', ''),
            displayName=updated_data.get('contactName'),
            phone=updated_data.get('phone'),
            imageUrl=updated_data.get('imageUrl'),
            active=updated_data.get('active', True),
            storeId=store_id,
            role=STAFF_ROLE,
            createdAt=_convert_timestamp(updated_data.get('createdAt')),
            updatedAt=_convert_timestamp(updated_data.get('updatedAt'))
        )

        staff_item = StaffItemResponse(item=staff_info)
        return StaffResponse.success(staff_item)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update staffs member: {str(e)}")


async def delete_staff_service(staff_id: str, store_id: str) -> StaffDeleteResponseModel:
    """Delete a staff member (soft delete by removing from store and hard delete from Firebase Auth)."""
    try:
        user_ref = db.collection('users').document(staff_id)
        user_doc = user_ref.get()

        if not user_doc.exists:
            return StaffDeleteResponseModel.error("Staff member not found", code=404)

        user_data = user_doc.to_dict()
        stores = user_data.get('stores', [])

        # Remove the store from user's stores list
        updated_stores = [store for store in stores if not (store.get('id') == store_id and store.get('role') == STAFF_ROLE)]

        if len(updated_stores) == len(stores):
            return StaffDeleteResponseModel.error("Staff member not found in this store", code=404)

        # If user has no stores left, delete Firebase Auth account and Firestore document
        if not updated_stores:
            # Delete Firebase Auth user account first
            try:
                auth.delete_user(staff_id)
                print(f"Successfully deleted Firebase Auth user: {staff_id}")
            except Exception as auth_error:
                print(f"Warning: Failed to delete Firebase Auth user: {str(auth_error)}")
                # Continue to delete Firestore document even if Firebase Auth deletion fails

            # Always delete Firestore user document when no stores remain
            try:
                user_ref.delete()
                print(f"Successfully deleted Firestore user document: {staff_id}")
            except Exception as firestore_error:
                print(f"Warning: Failed to delete Firestore user document: {str(firestore_error)}")

        else:
            # User still has other stores, just update the stores list
            user_ref.update({
                "stores": updated_stores,
                "updatedAt": firestore.firestore.SERVER_TIMESTAMP
            })

        # Return a proper delete response
        delete_response = StaffDeleteResponse(message="Staff member removed successfully")
        return StaffDeleteResponseModel.success(delete_response)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete staff member: {str(e)}")


async def search_staff_service(query: str, store_id: str, page: int = 1, size: int = 10) -> StaffListResponse:
    """
    Service function to search for staff by email, displayName, or phone with pagination within a specific store.

    Args:
        query: The search query
        store_id: The ID of the store to search staff in
        page: Page number (starts from 1)
        size: Number of items per page

    Returns:
        StaffListResponse object containing the paginated search results

    Raises:
        HTTPException: If errors occur during search
    """
    if not store_id:
        raise HTTPException(
            status_code=400,
            detail="Missing store ID parameter"
        )

    try:
        # If query is empty, return all staff for the store instead of searching
        if not query or query.strip() == "":
            return await get_staff_list_service(store_id, page, size)

        query = query.lower().strip()  # Normalize query for case-insensitive search

        # Dictionary to store all found staff with their relevance score
        staff_results = {}

        # Query users collection for staff members of this store
        users_ref = db.collection('users')
        users_query = users_ref.stream()

        for user_doc in users_query:
            user_data = user_doc.to_dict()
            if not user_data:
                continue

            stores = user_data.get('stores', [])

            # Check if user is staff in this store
            is_staff_in_store = False
            for store in stores:
                if store.get('id') == store_id and store.get('role') == STAFF_ROLE:
                    is_staff_in_store = True
                    break

            if not is_staff_in_store:
                continue

            # Initialize relevance score
            relevance_score = 0

            # Check email field (highest priority)
            email = user_data.get('email', '').lower()
            if query in email:
                # Higher score for exact matches
                if email == query:
                    relevance_score += 15
                # Higher score if query is at the beginning of the email
                elif email.startswith(query):
                    relevance_score += 12
                # Standard score for substring matches
                else:
                    relevance_score += 10

            # Check display name (high priority)
            display_name = user_data.get('contactName', '').lower()
            if query in display_name:
                # Higher score for exact matches
                if display_name == query:
                    relevance_score += 12
                # Higher score if query is at the beginning of the name
                elif display_name.startswith(query):
                    relevance_score += 10
                # Standard score for substring matches
                else:
                    relevance_score += 8

            # Check phone field (medium priority)
            phone = user_data.get('phone', '').lower()
            if query in phone:
                relevance_score += 5

            # If this staff member matches the query in any field, add to results
            if relevance_score > 0:
                staff_info = StaffInfo(
                    id=user_doc.id,
                    email=user_data.get('email', ''),
                    displayName=user_data.get('contactName'),
                    phone=user_data.get('phone'),
                    imageUrl=user_data.get('imageUrl'),
                    active=user_data.get('active', True),
                    storeId=store_id,
                    role=STAFF_ROLE,
                    createdAt=_convert_timestamp(user_data.get('createdAt')),
                    updatedAt=_convert_timestamp(user_data.get('updatedAt'))
                )
                staff_results[user_doc.id] = {
                    'staff': staff_info,
                    'relevance': relevance_score
                }

        # Sort by relevance score (highest first)
        sorted_staff = sorted(staff_results.values(), key=lambda x: x['relevance'], reverse=True)
        all_staff = [item['staff'] for item in sorted_staff]

        # Calculate pagination
        total = len(all_staff)
        pages = (total + size - 1) // size  # Ceiling division
        start_index = (page - 1) * size
        end_index = start_index + size

        # Get paginated items
        paginated_staff = all_staff[start_index:end_index]

        # Wrap staff list in items property with pagination info
        staff_list_data = PaginationResponse(
            items=paginated_staff,
            total=total,
            page=page,
            size=size,
            pages=pages
        )
        return StaffListResponse.success(staff_list_data)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to search staff: {str(e)}")


def _convert_timestamp(timestamp) -> Optional[str]:
    """Convert Firestore timestamp to ISO format string for JSON serialization."""
    if timestamp is None:
        return None
    if hasattr(timestamp, 'timestamp'):
        return datetime.fromtimestamp(timestamp.timestamp()).isoformat()
    if isinstance(timestamp, datetime):
        return timestamp.isoformat()
    return str(timestamp)

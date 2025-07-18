"""
Customer management services for CRUD operations.
"""

import urllib.parse
from datetime import datetime
from typing import Optional

from firebase_admin import firestore
from fastapi import HTTPException

from .schemas import (
    CustomerCreate, CustomerUpdate, CustomerInfo, CustomerResponse,
    CustomerListResponse, CustomerDeleteResponse, CustomerDeleteResponseModel,
    CustomerCreateResponse, CustomerItemResponse
)
from api.common.schemas import PaginationResponse

db = firestore.client()


async def create_customer_service(customer_data: CustomerCreate, store_id: str) -> CustomerCreateResponse:
    """Create a new customer."""
    try:
        # Validate that the store exists and user has access
        store_ref = db.collection('stores').document(store_id)
        store_doc = store_ref.get()
        if not store_doc.exists:
            raise ValueError(f"Store with ID {store_id} does not exist")

        # Prepare customer document for Firestore
        # Set default image URL if imageUrl is empty or None
        image_url = customer_data.imageUrl
        if not image_url:
            # Generate default avatar using customer's name initials with URL encoding
            encoded_name = urllib.parse.quote(customer_data.name)
            encoded_colors = urllib.parse.quote("b6e3f4,c0aede,d1d4f9")
            image_url = f"https://api.dicebear.com/9.x/initials/png?seed={encoded_name}&backgroundColor={encoded_colors}"

        # Handle email field - if it was originally empty string, store as empty string
        email_value = str(customer_data.email) if customer_data.email else ""

        customer_doc_data = {
            "name": customer_data.name,
            "storeId": store_id,  # Use store_id parameter instead of customer_data.storeId
            "phone": customer_data.phone,
            "email": email_value,  # Store empty string if email was blank
            "address": customer_data.address,
            "dob": customer_data.dob,
            "imageUrl": image_url,
            "createdAt": firestore.firestore.SERVER_TIMESTAMP,
            "updatedAt": firestore.firestore.SERVER_TIMESTAMP
        }

        # Create customer document in Firestore
        doc_ref = db.collection('customers').document()
        doc_ref.set(customer_doc_data)

        # Get the created document to return with ID
        created_doc = doc_ref.get()
        created_data = created_doc.to_dict()

        customer_info = CustomerInfo(
            id=created_doc.id,
            storeId=created_data.get('storeId'),
            name=created_data.get('name'),
            phone=created_data.get('phone'),
            email=created_data.get('email'),
            address=created_data.get('address'),
            dob=created_data.get('dob'),
            imageUrl=created_data.get('imageUrl'),
            createdAt=_convert_timestamp(created_data.get('createdAt')),
            updatedAt=_convert_timestamp(created_data.get('updatedAt'))
        )

        return CustomerCreateResponse.success(customer_info)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create customer: {str(e)}")


async def get_customers_list_service(store_id: str, page: int = 1, size: int = 10) -> CustomerListResponse:
    """Get all customers for a store with pagination."""
    try:
        # Query customers collection for customers of this store
        customers_ref = db.collection('customers').where('storeId', '==', store_id)

        # Get all customers and apply pagination
        customers_query = customers_ref.stream()
        all_customers = []

        for customer_doc in customers_query:
            customer_data = customer_doc.to_dict()
            if not customer_data:
                continue

            customer_info = CustomerInfo(
                id=customer_doc.id,
                storeId=customer_data.get('storeId'),
                name=customer_data.get('name'),
                phone=customer_data.get('phone'),
                email=customer_data.get('email'),
                address=customer_data.get('address'),
                dob=customer_data.get('dob'),
                imageUrl=customer_data.get('imageUrl'),
                createdAt=_convert_timestamp(customer_data.get('createdAt')),
                updatedAt=_convert_timestamp(customer_data.get('updatedAt'))
            )
            all_customers.append(customer_info)

        # Sort by creation date (newest first)
        all_customers.sort(key=lambda x: x.createdAt or "", reverse=True)

        # Calculate pagination
        total = len(all_customers)
        pages = (total + size - 1) // size  # Ceiling division
        start_index = (page - 1) * size
        end_index = start_index + size

        # Get paginated items
        paginated_customers = all_customers[start_index:end_index]

        # Wrap customers list in items property with pagination info
        customers_list_data = PaginationResponse(
            items=paginated_customers,
            total=total,
            page=page,
            size=size,
            pages=pages
        )
        return CustomerListResponse.success(customers_list_data)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve customers list: {str(e)}")


async def get_customer_service(customer_id: str, store_id: str) -> CustomerResponse:
    """Get a specific customer."""
    try:
        customer_ref = db.collection('customers').document(customer_id)
        customer_doc = customer_ref.get()

        if not customer_doc.exists:
            return CustomerResponse.error("Customer not found", code=404)

        customer_data = customer_doc.to_dict()

        # Verify customer belongs to the store
        if customer_data.get('storeId') != store_id:
            return CustomerResponse.error("Customer not found in this store", code=404)

        customer_info = CustomerInfo(
            id=customer_id,
            storeId=customer_data.get('storeId'),
            name=customer_data.get('name'),
            phone=customer_data.get('phone'),
            email=customer_data.get('email'),
            address=customer_data.get('address'),
            dob=customer_data.get('dob'),
            imageUrl=customer_data.get('imageUrl'),
            createdAt=_convert_timestamp(customer_data.get('createdAt')),
            updatedAt=_convert_timestamp(customer_data.get('updatedAt'))
        )

        customer_item = CustomerItemResponse(item=customer_info)
        return CustomerResponse.success(customer_item)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve customer: {str(e)}")


async def update_customer_service(customer_id: str, store_id: str, update_data: CustomerUpdate) -> CustomerResponse:
    """Update a customer's information."""
    try:
        customer_ref = db.collection('customers').document(customer_id)
        customer_doc = customer_ref.get()

        if not customer_doc.exists:
            return CustomerResponse.error("Customer not found", code=404)

        customer_data = customer_doc.to_dict()

        # Verify customer belongs to the store
        if customer_data.get('storeId') != store_id:
            return CustomerResponse.error("Customer not found in this store", code=404)

        # Prepare update data
        update_dict = {"updatedAt": firestore.firestore.SERVER_TIMESTAMP}

        if update_data.name is not None:
            update_dict["name"] = update_data.name

        if update_data.phone is not None:
            update_dict["phone"] = update_data.phone

        # Handle email field - check if it was explicitly provided (even if empty)
        if hasattr(update_data, 'email') and update_data.email is not None:
            # Email field was provided in the request (could be empty string or valid email)
            update_dict["email"] = update_data.email

        if update_data.address is not None:
            update_dict["address"] = update_data.address

        if update_data.dob is not None:
            update_dict["dob"] = update_data.dob

        if update_data.imageUrl is not None:
            update_dict["imageUrl"] = update_data.imageUrl

        # Update Firestore document
        customer_ref.update(update_dict)

        # Get updated document
        updated_doc = customer_ref.get()
        updated_data = updated_doc.to_dict()

        customer_info = CustomerInfo(
            id=customer_id,
            storeId=updated_data.get('storeId'),
            name=updated_data.get('name'),
            phone=updated_data.get('phone'),
            email=updated_data.get('email'),
            address=updated_data.get('address'),
            dob=updated_data.get('dob'),
            imageUrl=updated_data.get('imageUrl'),
            createdAt=_convert_timestamp(updated_data.get('createdAt')),
            updatedAt=_convert_timestamp(updated_data.get('updatedAt'))
        )

        customer_item = CustomerItemResponse(item=customer_info)
        return CustomerResponse.success(customer_item)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update customer: {str(e)}")


async def delete_customer_service(customer_id: str, store_id: str) -> CustomerDeleteResponseModel:
    """Delete a customer."""
    try:
        customer_ref = db.collection('customers').document(customer_id)
        customer_doc = customer_ref.get()

        if not customer_doc.exists:
            return CustomerDeleteResponseModel.error("Customer not found", code=404)

        customer_data = customer_doc.to_dict()

        # Verify customer belongs to the store
        if customer_data.get('storeId') != store_id:
            return CustomerDeleteResponseModel.error("Customer not found in this store", code=404)

        # Delete customer document
        customer_ref.delete()

        # Return success response
        delete_response = CustomerDeleteResponse(message="Customer deleted successfully")
        return CustomerDeleteResponseModel.success(delete_response)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete customer: {str(e)}")


async def search_customers_service(query: str, store_id: str, page: int = 1, size: int = 10) -> CustomerListResponse:
    """
    Service function to search for customers by name, phone, or email with pagination within a specific store.

    Args:
        query: The search query
        store_id: The ID of the store to search customers in
        page: Page number (starts from 1)
        size: Number of items per page

    Returns:
        CustomerListResponse object containing the paginated search results

    Raises:
        HTTPException: If errors occur during search
    """
    if not store_id:
        raise HTTPException(
            status_code=400,
            detail="Missing store ID parameter"
        )

    try:
        # If query is empty, return all customers for the store instead of searching
        if not query or query.strip() == "":
            return await get_customers_list_service(store_id, page, size)

        query = query.lower().strip()  # Normalize query for case-insensitive search

        # Dictionary to store all found customers with their relevance score
        customer_results = {}

        # Query customers collection for customers of this store
        customers_ref = db.collection('customers').where('storeId', '==', store_id)
        customers_query = customers_ref.stream()

        for customer_doc in customers_query:
            customer_data = customer_doc.to_dict()
            if not customer_data:
                continue

            # Initialize relevance score
            relevance_score = 0

            # Check name field (highest priority)
            name = customer_data.get('name', '') or ''
            if query in name.lower():
                # Higher score for exact matches
                if name.lower() == query:
                    relevance_score += 15
                # Higher score if query is at the beginning of the name
                elif name.lower().startswith(query):
                    relevance_score += 12
                # Standard score for substring matches
                else:
                    relevance_score += 10

            # Check phone field (high priority)
            phone = customer_data.get('phone', '') or ''
            if query in phone.lower():
                relevance_score += 8

            # Check email field (medium priority)
            email = customer_data.get('email', '') or ''
            if query in email.lower():
                relevance_score += 5

            # Check address field (low priority)
            address = customer_data.get('address', '') or ''
            if query in address.lower():
                relevance_score += 3

            # If this customer matches the query in any field, add to results
            if relevance_score > 0:
                customer_info = CustomerInfo(
                    id=customer_doc.id,
                    storeId=customer_data.get('storeId'),
                    name=customer_data.get('name'),
                    phone=customer_data.get('phone'),
                    email=customer_data.get('email'),
                    address=customer_data.get('address'),
                    dob=customer_data.get('dob'),
                    imageUrl=customer_data.get('imageUrl'),
                    createdAt=_convert_timestamp(customer_data.get('createdAt')),
                    updatedAt=_convert_timestamp(customer_data.get('updatedAt'))
                )
                customer_results[customer_doc.id] = {
                    'customer': customer_info,
                    'relevance': relevance_score
                }

        # Sort by relevance score (highest first)
        sorted_customers = sorted(customer_results.values(), key=lambda x: x['relevance'], reverse=True)
        all_customers = [item['customer'] for item in sorted_customers]

        # Calculate pagination
        total = len(all_customers)
        pages = (total + size - 1) // size  # Ceiling division
        start_index = (page - 1) * size
        end_index = start_index + size

        # Get paginated items
        paginated_customers = all_customers[start_index:end_index]

        # Wrap customers list in items property with pagination info
        customers_list_data = PaginationResponse(
            items=paginated_customers,
            total=total,
            page=page,
            size=size,
            pages=pages
        )
        return CustomerListResponse.success(customers_list_data)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to search customers: {str(e)}")


def _convert_timestamp(timestamp) -> Optional[str]:
    """Convert Firestore timestamp to ISO format string for JSON serialization."""
    if timestamp is None:
        return None
    if hasattr(timestamp, 'timestamp'):
        return datetime.fromtimestamp(timestamp.timestamp()).isoformat()
    if isinstance(timestamp, datetime):
        return timestamp.isoformat()
    return str(timestamp)

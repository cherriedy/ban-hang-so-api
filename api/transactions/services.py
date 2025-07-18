"""
Services for handling transactions business logic.
"""
from datetime import datetime, timezone
import uuid
from typing import Optional
import math

from fastapi import HTTPException, status
from firebase_admin import firestore
from google.cloud.firestore import Query

from api.transactions.schemas import (
    CartRequest, TransactionCreate, TransactionResponse, TransactionsData, TransactionSummary
)
from api.transactions.constants import DEFAULT_RETAIL_CUSTOMER
from api.products.services import get_product_by_id
from api.customers.services import get_customer_service
from api.staffs.services import get_staff_service


# Firebase collections
TRANSACTIONS_COLLECTION = "transactions"
PRODUCTS_COLLECTION = "products"


def get_firestore_client():
    """Get Firestore client instance."""
    return firestore.client()


async def process_cart_to_transaction(cart: CartRequest) -> TransactionCreate:
    """
    Process cart data to create a transaction.

    Args:
        cart: The cart data from request

    Returns:
        TransactionCreate object ready to be saved
    """
    # Create unique transaction ID
    transaction_id = str(uuid.uuid4())

    # Map cart items to transaction items
    items_with_quantities = [{"id": item.id, "quantity": item.quantity} for item in cart.items]

    # Create transaction object
    transaction = TransactionCreate(
        id=transaction_id,
        customerId=cart.customerId,
        staffId=cart.staffId,
        storeId=cart.storeId,
        totalItems=cart.totalItems,
        totalSellingPrices=cart.totalSellingPrices,
        totalPurchasePrices=cart.totalPurchasePrices,
        totalDiscountPrices=cart.totalDiscountPrices,
        finalPrices=cart.finalPrices,
        paymentMethod=cart.paymentMethod,
        itemsIds=items_with_quantities,
        note=cart.note
    )

    return transaction


async def create_transaction(transaction: TransactionCreate) -> TransactionResponse:
    """
    Create a new transaction in the Firebase database.

    Args:
        transaction: Transaction data to create

    Returns:
        Created transaction with full details
    """
    db = get_firestore_client()

    # Fetch complete data for all items
    items = []
    for item_data in transaction.itemsIds:
        product_id = item_data["id"]
        quantity = item_data["quantity"]

        # Get complete product data
        product = await get_product_by_id(product_id, transaction.storeId)
        if not product:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Product with ID {product_id} not found"
            )

        # Create transaction item
        transaction_item = {
            "id": product.id,
            "name": product.name,
            "thumbnailUrl": product.thumbnailUrl if hasattr(product, "thumbnailUrl") else None,
            "sellingPrice": product.sellingPrice,
            "purchasePrice": product.purchasePrice,
            "discountPrice": product.discountPrice if hasattr(product, "discountPrice") else 0.0,
            "quantity": quantity,
            "barcode": product.barcode if hasattr(product, "barcode") else None,
            "brand": {
                "id": product.brand.id,
                "name": product.brand.name
            } if hasattr(product, "brand") and product.brand else None,
            "category": {
                "id": product.category.id,
                "name": product.category.name
            } if hasattr(product, "category") and product.category else None
        }
        items.append(transaction_item)

    # Get customer data if available
    customer = None
    if transaction.customerId:
        customer_data = await get_customer_service(transaction.customerId, transaction.storeId)
        if customer_data and customer_data.success and customer_data.data and customer_data.data.item:
            customer = {
                "id": customer_data.data.item.id,
                "name": customer_data.data.item.name,
                "phone": customer_data.data.item.phone,
                "email": customer_data.data.item.email
            }
    else:
        # If no customerId provided, use default retail customer
        customer = DEFAULT_RETAIL_CUSTOMER.copy()

    # Get staff data if available
    staff = None
    if transaction.staffId:
        staff_data = await get_staff_service(transaction.staffId, transaction.storeId)
        if staff_data and staff_data.success and staff_data.data and staff_data.data.item:
            staff = {
                "id": staff_data.data.item.id,
                "name": staff_data.data.item.displayName or staff_data.data.item.email,  # Use displayName or fallback to email
                "phone": staff_data.data.item.phone,
                "email": staff_data.data.item.email,
                "role": staff_data.data.item.role
            }

    # Create timestamps
    now = datetime.now()

    # Prepare transaction data for Firestore
    transaction_data = {
        "id": transaction.id,
        "customer": customer,
        "staff": staff,
        "storeId": transaction.storeId,
        "totalItems": transaction.totalItems,
        "totalSellingPrices": transaction.totalSellingPrices,
        "totalPurchasePrices": transaction.totalPurchasePrices,
        "totalDiscountPrices": transaction.totalDiscountPrices,
        "finalPrices": transaction.finalPrices,
        "paymentMethod": transaction.paymentMethod.value,
        "items": items,
        "note": transaction.note,
        "createdAt": now,
        "updatedAt": now
    }

    try:
        # Save transaction to Firestore
        doc_ref = db.collection(TRANSACTIONS_COLLECTION).document(transaction.id)
        doc_ref.set(transaction_data)

        return TransactionResponse(**transaction_data)

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create transaction: {str(e)}"
        )


async def get_transaction_by_id(transaction_id: str) -> Optional[TransactionResponse]:
    """
    Get a transaction by ID from Firebase database.

    Args:
        transaction_id: The transaction ID to retrieve

    Returns:
        Transaction data if found, otherwise None
    """
    db = get_firestore_client()

    try:
        doc_ref = db.collection(TRANSACTIONS_COLLECTION).document(transaction_id)
        doc = doc_ref.get()

        if doc.exists:
            transaction_data = doc.to_dict()
            return TransactionResponse(**transaction_data)
        else:
            return None

    except Exception as e:
        print(f"Error retrieving transaction {transaction_id}: {str(e)}")
        return None


async def search_transactions(
    store_id: Optional[str] = None,
    customer_id: Optional[str] = None,
    staff_id: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    min_amount: Optional[float] = None,
    max_amount: Optional[float] = None,
    payment_method: Optional[str] = None,
    text_query: Optional[str] = None,  # New parameter for text search
    page: int = 1,
    size: int = 20
) -> TransactionsData:
    """
    Search transactions based on filter criteria from Firebase with pagination.

    Args:
        store_id: Filter by store ID
        customer_id: Filter by customer ID
        staff_id: Filter by staff ID
        start_date: Filter by start date
        end_date: Filter by end date
        min_amount: Minimum transaction amount
        max_amount: Maximum transaction amount
        payment_method: Filter by payment method
        text_query: Text search query for customer name, staff name, or transaction ID
        page: Page number (starts at 1)
        size: Number of items per page

    Returns:
        TransactionsData with pagination information
    """
    db = get_firestore_client()

    try:
        print(f"DEBUG: Search transactions for store_id={store_id}, filters: start_date={start_date}, end_date={end_date}, min_amount={min_amount}, max_amount={max_amount}, payment_method={payment_method}")

        # Start building the query with only basic filters to avoid composite index issues
        query = db.collection(TRANSACTIONS_COLLECTION)

        # Apply only essential filters that don't require composite indexes
        if store_id:
            query = query.where("storeId", "==", store_id)

        # Apply customer filter if provided
        if customer_id:
            query = query.where("customer.id", "==", customer_id)

        # Apply staff filter if provided
        if staff_id:
            query = query.where("staff.id", "==", staff_id)

        # Order by creation date (newest first) - this works with single field filters
        query = query.order_by("createdAt", direction=Query.DESCENDING)

        # Get all documents matching basic criteria
        print("DEBUG: Executing query with basic filters...")
        all_docs = list(query.stream())
        print(f"DEBUG: Found {len(all_docs)} documents with basic filters")

        # Apply additional filters in memory
        filtered_docs = []
        for doc in all_docs:
            transaction_data = doc.to_dict()

            # Apply date filters
            if start_date or end_date:
                created_at = transaction_data.get("createdAt")
                if created_at:
                    # Ensure both are timezone-aware (UTC)
                    if created_at.tzinfo is None:
                        created_at = created_at.replace(tzinfo=timezone.utc)
                    if start_date and start_date.tzinfo is None:
                        start_date_cmp = start_date.replace(tzinfo=timezone.utc)
                    else:
                        start_date_cmp = start_date
                    if end_date and end_date.tzinfo is None:
                        end_date_cmp = end_date.replace(tzinfo=timezone.utc)
                    else:
                        end_date_cmp = end_date
                    if start_date and created_at < start_date_cmp:
                        continue
                    if end_date and created_at > end_date_cmp:
                        continue

            # Apply amount filters
            final_price = transaction_data.get("finalPrices", 0)
            if min_amount is not None and final_price < min_amount:
                continue
            if max_amount is not None and final_price > max_amount:
                continue

            # Apply payment method filter
            if payment_method and transaction_data.get("paymentMethod") != payment_method:
                continue

            # Apply text search filter
            if text_query:
                text_query_lower = text_query.lower().strip()
                matches = False

                # Check transaction ID
                if text_query_lower in transaction_data.get("id", "").lower():
                    matches = True

                # Check customer name
                if not matches and transaction_data.get("customer"):
                    customer_name = transaction_data["customer"].get("name", "").lower()
                    if text_query_lower in customer_name:
                        matches = True

                # Check staff name
                if not matches and transaction_data.get("staff"):
                    staff_name = transaction_data["staff"].get("name", "").lower()
                    if text_query_lower in staff_name:
                        matches = True

                if not matches:
                    continue

            filtered_docs.append((doc, transaction_data))

        print(f"DEBUG: Found {len(filtered_docs)} documents after all filtering")

        # Calculate pagination for filtered results
        total = len(filtered_docs)
        offset = (page - 1) * size
        paginated_docs = filtered_docs[offset:offset + size]

        results = []
        for doc, transaction_data in paginated_docs:
            print(f"DEBUG: Processing transaction {doc.id}")

            try:
                # Create TransactionSummary with only essential fields
                customer_name = "Unknown"
                if transaction_data.get("customer"):
                    customer_name = transaction_data["customer"].get("name", "Unknown")

                staff_name = None
                if transaction_data.get("staff"):
                    staff_name = transaction_data["staff"].get("name")

                summary = TransactionSummary(
                    id=transaction_data.get("id", doc.id),
                    customerName=customer_name,
                    staffName=staff_name,
                    price=transaction_data.get("finalPrices", 0.0),
                    createdAt=transaction_data.get("createdAt")
                )
                results.append(summary)
                print(f"DEBUG: Successfully created summary for transaction {summary.id}")
            except Exception as validation_error:
                print(f"DEBUG: Validation error for transaction {doc.id}: {validation_error}")
                # Skip this transaction if validation fails
                continue

        # Calculate pagination metadata
        pages = math.ceil(total / size) if total > 0 else 1

        print(f"DEBUG: Returning {len(results)} results, total: {total}")

        return TransactionsData(
            items=results,
            total=total,
            page=page,
            size=size,
            pages=pages
        )

    except Exception as e:
        print(f"DEBUG: Error in search_transactions: {str(e)}")
        return TransactionsData(
            items=[],
            total=0,
            page=page,
            size=size,
            pages=1
        )


async def update_product_inventory(product_id: str, quantity: int, store_id: str) -> bool:
    """
    Update product inventory after a transaction in Firebase.

    Args:
        product_id: The product ID
        quantity: Quantity to reduce (negative for reducing stock)
        store_id: The store ID

    Returns:
        True if successful, False otherwise
    """
    db = get_firestore_client()

    try:
        # Get the product document
        product_ref = db.collection(PRODUCTS_COLLECTION).document(product_id)

        # Use a transaction to ensure atomic updates
        @firestore.transactional
        def update_inventory(transaction_obj, product_ref):
            product_doc = product_ref.get(transaction=transaction_obj)

            if not product_doc.exists:
                return False

            product_data = product_doc.to_dict()

            # Update inventory for the specific store
            if "inventory" not in product_data:
                product_data["inventory"] = {}

            if store_id not in product_data["inventory"]:
                product_data["inventory"][store_id] = 0

            # Update the inventory (quantity is negative for sales)
            new_quantity = product_data["inventory"][store_id] + quantity

            # Ensure inventory doesn't go below 0
            if new_quantity < 0:
                new_quantity = 0

            product_data["inventory"][store_id] = new_quantity
            product_data["updatedAt"] = datetime.now()

            # Update the document
            transaction_obj.update(product_ref, product_data)
            return True

        # Execute the transaction
        transaction_obj = db.transaction()
        result = update_inventory(transaction_obj, product_ref)

        return result

    except Exception as e:
        print(f"Error updating inventory for product {product_id}: {str(e)}")
        return False

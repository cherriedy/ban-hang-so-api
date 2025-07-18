"""
Transaction management routers with full CRUD operations.
"""
from typing import Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query, Path, status

from api.auth.dependencies import get_current_user_id
from api.common.schemas import JSendResponse
from .schemas import (
    CartRequest, PaymentMethod,
    TransactionsData, TransactionItemResponse
)
from .services import (
    process_cart_to_transaction,
    create_transaction,
    get_transaction_by_id,
    search_transactions,
    update_product_inventory
)

router = APIRouter()


def parse_flexible_date(date_str: str, is_end_date: bool = False) -> datetime:
    """
    Parse flexible date formats:
    - "2025" -> January 1, 2025 00:00:00 (start) or December 31, 2025 23:59:59 (end)
    - "2025-07" -> July 1, 2025 00:00:00 (start) or July 31, 2025 23:59:59 (end)
    - "2025-07-16" -> July 16, 2025 00:00:00 (start) or July 16, 2025 23:59:59 (end)

    Args:
        date_str: The date string to parse
        is_end_date: If True, returns end of period; if False, returns start of period
    """
    if not date_str:
        return None

    date_str = date_str.strip()

    # Year only (e.g., "2025")
    if len(date_str) == 4 and date_str.isdigit():
        year = int(date_str)
        if is_end_date:
            # End of year: December 31, 23:59:59
            return datetime(year, 12, 31, 23, 59, 59)
        else:
            # Start of year: January 1, 00:00:00
            return datetime(year, 1, 1, 0, 0, 0)

    # Year-Month (e.g., "2025-07")
    elif len(date_str) == 7 and date_str.count('-') == 1:
        try:
            year, month = map(int, date_str.split('-'))
            if is_end_date:
                # End of month: last day of month, 23:59:59
                import calendar
                last_day = calendar.monthrange(year, month)[1]
                return datetime(year, month, last_day, 23, 59, 59)
            else:
                # Start of month: first day, 00:00:00
                return datetime(year, month, 1, 0, 0, 0)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid date format: {date_str}. Expected format: YYYY-MM"
            )

    # Full date (e.g., "2025-07-16")
    elif len(date_str) == 10 and date_str.count('-') == 2:
        try:
            parsed_date = datetime.strptime(date_str, "%Y-%m-%d")
            if is_end_date:
                # End of day: 23:59:59
                return parsed_date.replace(hour=23, minute=59, second=59)
            else:
                # Start of day: 00:00:00
                return parsed_date.replace(hour=0, minute=0, second=0)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid date format: {date_str}. Expected format: YYYY-MM-DD"
            )

    # Invalid format
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid date format: {date_str}. Supported formats: YYYY, YYYY-MM, YYYY-MM-DD"
        )


# Create a dependency function for store-based auth (following Products pattern)
async def get_store_auth(
    store_id: str = Query(..., description="Store ID to access"),
    user_id: str = Depends(get_current_user_id)
) -> tuple[str, dict]:
    """
    Dependency that combines user authentication and store authorization.

    Args:
        store_id: The ID of the store to access (from query parameter)
        user_id: The authenticated user ID (injected by dependency)

    Returns:
        tuple: (user_id, store_info)
    """
    from api.auth.dependencies import verify_store_access
    store_info = await verify_store_access(user_id, store_id)
    return user_id, store_info


@router.get("", response_model=JSendResponse[TransactionsData])
async def list_transactions(
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(20, ge=1, le=100, description="Items per page"),
    sort_by: str = Query("createdAt", description="Field to sort by"),
    sort_order: str = Query("desc", description="Sort order (asc or desc)"),
    customer_id: Optional[str] = Query(None, description="Customer ID filter"),
    staff_id: Optional[str] = Query(None, description="Staff ID filter"),
    start_date: Optional[str] = Query(None, description="Start date filter (YYYY, YYYY-MM, or YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date filter (YYYY, YYYY-MM, or YYYY-MM-DD)"),
    min_amount: Optional[float] = Query(None, description="Minimum transaction amount"),
    max_amount: Optional[float] = Query(None, description="Maximum transaction amount"),
    payment_method: Optional[PaymentMethod] = Query(None, description="Payment method filter"),
    auth_info: tuple = Depends(get_store_auth)
):
    """
    Get a list of transactions with pagination and optional filters for a specific store.

    Args:
        page: Page number (starts at 1)
        size: Number of transactions per page (max 100)
        sort_by: Field to sort the results by
        sort_order: Sort direction ('asc' or 'desc')
        customer_id: Customer ID filter
        staff_id: Staff ID filter
        start_date: Start date filter (supports YYYY, YYYY-MM, YYYY-MM-DD formats)
        end_date: End date filter (supports YYYY, YYYY-MM, YYYY-MM-DD formats)
        min_amount: Minimum transaction amount
        max_amount: Maximum transaction amount
        payment_method: Payment method filter

    Returns:
        JSendResponse containing transactions data and pagination info
    """
    try:
        user_id, store_info = auth_info
        store_id = store_info['id']

        # Parse flexible date formats
        parsed_start_date = parse_flexible_date(start_date) if start_date else None
        parsed_end_date = parse_flexible_date(end_date, is_end_date=True) if end_date else None

        # Use the search function with filters
        results = await search_transactions(
            store_id=store_id,
            customer_id=customer_id,
            staff_id=staff_id,
            start_date=parsed_start_date,
            end_date=parsed_end_date,
            min_amount=min_amount,
            max_amount=max_amount,
            payment_method=payment_method.value if payment_method else None,
            page=page,
            size=size
        )

        return JSendResponse.success(results)
    except HTTPException as e:
        return JSendResponse.error(
            message=str(e.detail),
            code=e.status_code
        )
    except Exception as e:
        return JSendResponse.error(
            message=str(e),
            code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@router.get("/search", response_model=JSendResponse[TransactionsData])
async def search_transactions_endpoint(
    q: str = Query(..., description="Search query (customer name, staff name, etc.)"),
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(20, ge=1, le=100, description="Items per page"),
    auth_info: tuple = Depends(get_store_auth)
):
    """
    Search for transactions by customer name, staff name, or other criteria within a specific store.

    Args:
        q: The search query
        page: The page number (starts at 1)
        size: Number of transactions per page (max 100)
        auth_info: Authentication and authorization info (injected)

    Returns:
        JSendResponse containing a list of matching transactions
    """
    try:
        user_id, store_info = auth_info
        store_id = store_info['id']

        # Use the search_transactions function with text query
        results = await search_transactions(
            store_id=store_id,
            text_query=q,  # Pass the search query to the service function
            page=page,
            size=size
        )

        return JSendResponse.success(results)
    except HTTPException as e:
        return JSendResponse.error(
            message=str(e.detail),
            code=e.status_code
        )
    except Exception as e:
        return JSendResponse.error(
            message=str(e),
            code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@router.get("/{transaction_id}", response_model=JSendResponse[TransactionItemResponse])
async def get_transaction(
    transaction_id: str = Path(..., description="The ID of the transaction to retrieve"),
    auth_info: tuple = Depends(get_store_auth)
):
    """
    Get a transaction by ID within a specific store.

    Args:
        transaction_id: The unique transaction identifier
        auth_info: Authentication and authorization info (injected)

    Returns:
        JSendResponse containing the transaction data wrapped in item
    """
    try:
        user_id, store_info = auth_info
        store_id = store_info['id']

        transaction = await get_transaction_by_id(transaction_id)
        if not transaction:
            return JSendResponse.error(
                message=f"Transaction with ID {transaction_id} not found",
                code=status.HTTP_404_NOT_FOUND
            )

        # Verify transaction belongs to the store
        if transaction.storeId != store_id:
            return JSendResponse.error(
                message="Transaction not found in this store",
                code=status.HTTP_404_NOT_FOUND
            )

        # Wrap transaction data using the proper schema
        wrapped_transaction = TransactionItemResponse(item=transaction)
        return JSendResponse.success(wrapped_transaction)
    except HTTPException as e:
        return JSendResponse.error(
            message=str(e.detail),
            code=e.status_code
        )
    except Exception as e:
        return JSendResponse.error(
            message=str(e),
            code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@router.post("", response_model=JSendResponse[TransactionItemResponse])
async def create_transaction_endpoint(
    cart: CartRequest,
    background_tasks: BackgroundTasks,
    auth_info: tuple = Depends(get_store_auth)
):
    """
    Create a new transaction from cart data in a specific store.

    Args:
        cart: The cart data including items, customer, etc.
        background_tasks: FastAPI background tasks for inventory updates
        auth_info: Authentication and authorization info (injected)

    Returns:
        JSendResponse containing the created transaction with complete details wrapped in item
    """
    try:
        user_id, store_info = auth_info
        store_id = store_info['id']

        # Inject storeId from auth into cart
        cart.storeId = store_id

        # Process cart to transaction
        transaction = await process_cart_to_transaction(cart)

        # Create transaction
        result = await create_transaction(transaction)

        # Update inventory in background
        for item in cart.items:
            background_tasks.add_task(
                update_product_inventory,
                product_id=item.id,
                quantity=-item.quantity,  # Negative to reduce stock
                store_id=cart.storeId
            )

        # Create the properly wrapped response
        wrapped_result = TransactionItemResponse(item=result)
        return JSendResponse.success(wrapped_result)
    except HTTPException as e:
        return JSendResponse.error(
            message=str(e.detail),
            code=e.status_code
        )
    except Exception as e:
        return JSendResponse.error(
            message=str(e),
            code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

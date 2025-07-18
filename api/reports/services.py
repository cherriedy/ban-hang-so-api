"""
Services for handling reports business logic.
"""
from datetime import datetime
import pytz
from typing import Optional

from firebase_admin import firestore

from .schemas import SummaryResponse


# Set Vietnam timezone
VIETNAM_TZ = pytz.timezone('Asia/Ho_Chi_Minh')

# Firebase collections
TRANSACTIONS_COLLECTION = "transactions"


def get_firestore_client():
    """Get Firestore client instance."""
    return firestore.client()


async def get_transaction_statistics(
    store_id: str,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None
) -> SummaryResponse:
    """
    Calculate transaction summary for a store within a date range.
    If no dates are provided, defaults to today's transactions only.
    """
    db = get_firestore_client()

    # Build query for transactions in the store
    query = db.collection(TRANSACTIONS_COLLECTION).where("storeId", "==", store_id)

    # Get all transactions for the store
    transactions_docs = list(query.stream())

    print(f"DEBUG: Found {len(transactions_docs)} total transactions for store {store_id}")

    total_revenue = 0.0
    transaction_count = 0
    unique_customers = set()

    # If no date filters provided, get today's transactions
    if start_date is None and end_date is None:
        # Get current date in Vietnam timezone
        today_date = datetime.now(VIETNAM_TZ).date()
        print(f"DEBUG: Filtering for today's date: {today_date}")

        for doc in transactions_docs:
            transaction_data = doc.to_dict()
            created_at = transaction_data.get("createdAt")

            if not created_at:
                print(f"DEBUG: Transaction {doc.id} has no createdAt field")
                continue

            # Get transaction date (assume all dates are in Vietnam timezone)
            transaction_date = created_at.date()
            print(f"DEBUG: Transaction {doc.id} date: {transaction_date}, full time: {created_at}")

            # Check if transaction is from today
            if transaction_date == today_date:
                print(f"DEBUG: Including transaction {doc.id}")

                # Add revenue
                revenue = transaction_data.get("totalSellingPrices", 0.0)
                total_revenue += revenue
                transaction_count += 1

                # Add customer
                customer = transaction_data.get("customer", {})
                if customer and customer.get("id"):
                    unique_customers.add(customer["id"])

                print(f"DEBUG: Transaction {doc.id} - Revenue: {revenue}, Customer: {customer.get('id', 'None')}")
            else:
                print(f"DEBUG: Skipping transaction {doc.id} - wrong date (expected: {today_date}, got: {transaction_date})")
    else:
        # Handle custom date ranges
        for doc in transactions_docs:
            transaction_data = doc.to_dict()
            created_at = transaction_data.get("createdAt")

            if not created_at:
                continue

            # Simple date comparison without timezone conversion
            include_transaction = True

            if start_date and created_at < start_date:
                include_transaction = False
            if end_date and created_at > end_date:
                include_transaction = False

            if include_transaction:
                revenue = transaction_data.get("totalSellingPrices", 0.0)
                total_revenue += revenue
                transaction_count += 1

                customer = transaction_data.get("customer", {})
                if customer and customer.get("id"):
                    unique_customers.add(customer["id"])

    print(f"DEBUG: Final summary - Revenue: {total_revenue}, Transactions: {transaction_count}, Customers: {len(unique_customers)}")

    return SummaryResponse(
        revenue=total_revenue,
        transactions=transaction_count,
        customers=len(unique_customers),
        date=datetime.now(VIETNAM_TZ)
    )

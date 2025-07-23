"""
Services for handling reports business logic.
"""
from datetime import datetime, timedelta
import pytz
from typing import Optional
from collections import defaultdict

from firebase_admin import firestore

from .schemas import SummaryResponse, SalesReportResponse, DateRangeSchema, DataPointSchema, RevenueByDateSchema, TransactionsByDateSchema, SummaryStatsSchema


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


async def get_sales_report(
    store_id: str,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None
) -> SalesReportResponse:
    """
    Generate comprehensive sales report for a store within a date range.
    """
    db = get_firestore_client()

    # Default to current month if no dates provided
    if start_date is None or end_date is None:
        now = datetime.now(VIETNAM_TZ)
        start_date = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        end_date = now

    # Build query for transactions in the store
    query = db.collection(TRANSACTIONS_COLLECTION).where("storeId", "==", store_id)
    transactions_docs = list(query.stream())

    # Initialize data structures
    daily_revenue = defaultdict(float)
    daily_transactions = defaultdict(int)
    daily_cost = defaultdict(float)

    total_revenue = 0.0
    total_cost = 0.0
    total_transactions = 0

    # Process transactions
    for doc in transactions_docs:
        transaction_data = doc.to_dict()
        created_at = transaction_data.get("createdAt")

        if not created_at:
            continue

        # Filter by date range
        if created_at < start_date or created_at > end_date:
            continue

        # Get date key for grouping
        date_key = created_at.strftime("%Y-%m-%d")

        # Extract financial data
        revenue = transaction_data.get("totalSellingPrices", 0.0)
        cost = transaction_data.get("totalCostPrices", 0.0)

        # Aggregate data
        daily_revenue[date_key] += revenue
        daily_cost[date_key] += cost
        daily_transactions[date_key] += 1

        total_revenue += revenue
        total_cost += cost
        total_transactions += 1

    # Generate date range for report
    current_date = start_date.date()
    end_date_only = end_date.date()
    date_list = []

    while current_date <= end_date_only:
        date_list.append(current_date.strftime("%Y-%m-%d"))
        current_date += timedelta(days=1)

    # Convert revenue to thousands and prepare data points
    revenue_data_points = []
    transaction_data_points = []
    revenue_values = []

    for date_str in date_list:
        revenue_in_thousands = daily_revenue[date_str] / 1000.0
        revenue_values.append(revenue_in_thousands)

        revenue_data_points.append(DataPointSchema(
            date=date_str,
            value=revenue_in_thousands
        ))

        transaction_data_points.append(DataPointSchema(
            date=date_str,
            value=daily_transactions[date_str]
        ))

    # Calculate summary statistics
    avg_revenue = sum(revenue_values) / len(revenue_values) if revenue_values else 0
    max_revenue = max(revenue_values) if revenue_values else 0

    return SalesReportResponse(
        currency="VND",
        granularity="daily",
        dateRange=DateRangeSchema(
            start=start_date.strftime("%Y-%m-%d"),
            end=end_date.strftime("%Y-%m-%d")
        ),
        revenue=total_revenue,
        cost=total_cost,
        profit=total_revenue - total_cost,
        revenueByDate=RevenueByDateSchema(
            unit="thousand",
            data=revenue_data_points
        ),
        transactionsByDate=TransactionsByDateSchema(
            data=transaction_data_points
        ),
        summary=SummaryStatsSchema(
            averageRevenue=avg_revenue,
            maxRevenue=max_revenue,
            totalTransactions=total_transactions,
            unit="thousand"
        )
    )


"""
Reports management routers.
"""
from typing import Optional
from datetime import datetime
import pytz

from fastapi import APIRouter, Depends, HTTPException, Query, status

from api.auth.dependencies import get_current_user_id
from api.common.schemas import JSendResponse
from .schemas import SummaryResponse
from .services import get_transaction_statistics

router = APIRouter()

# Set Vietnam timezone
VIETNAM_TZ = pytz.timezone('Asia/Ho_Chi_Minh')


def parse_flexible_date(date_str: str, is_end_date: bool = False) -> datetime:
    """
    Parse flexible date formats and return as Vietnam timezone:
    - "2025" -> January 1, 2025 00:00:00 (start) or December 31, 2025 23:59:59 (end)
    - "2025-07" -> July 1, 2025 00:00:00 (start) or July 31, 2025 23:59:59 (end)
    - "2025-07-16" -> July 16, 2025 00:00:00 (start) or July 16, 2025 23:59:59 (end)

    Args:
        date_str: The date string to parse
        is_end_date: If True, returns end of period; if False, returns start of period

    Returns:
        datetime object in Vietnam timezone
    """
    if not date_str:
        return None

    date_str = date_str.strip()

    # Year only (e.g., "2025")
    if len(date_str) == 4 and date_str.isdigit():
        year = int(date_str)
        if is_end_date:
            # End of year: December 31, 23:59:59
            naive_dt = datetime(year, 12, 31, 23, 59, 59)
        else:
            # Start of year: January 1, 00:00:00
            naive_dt = datetime(year, 1, 1, 0, 0, 0)
        return VIETNAM_TZ.localize(naive_dt)

    # Year-Month (e.g., "2025-07")
    elif len(date_str) == 7 and date_str.count('-') == 1:
        try:
            year, month = map(int, date_str.split('-'))
            if is_end_date:
                # End of month: last day of month, 23:59:59
                import calendar
                last_day = calendar.monthrange(year, month)[1]
                naive_dt = datetime(year, month, last_day, 23, 59, 59)
            else:
                # Start of month: first day, 00:00:00
                naive_dt = datetime(year, month, 1, 0, 0, 0)
            return VIETNAM_TZ.localize(naive_dt)
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
                naive_dt = parsed_date.replace(hour=23, minute=59, second=59)
            else:
                # Start of day: 00:00:00
                naive_dt = parsed_date.replace(hour=0, minute=0, second=0)
            return VIETNAM_TZ.localize(naive_dt)
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


# Create a dependency function for store-based auth
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


@router.get("/summary", response_model=JSendResponse[SummaryResponse])
async def get_summary(
    start_date: Optional[str] = Query(None, description="Start date for summary (YYYY, YYYY-MM, or YYYY-MM-DD). Defaults to today if not provided."),
    end_date: Optional[str] = Query(None, description="End date for summary (YYYY, YYYY-MM, or YYYY-MM-DD). Defaults to today if not provided."),
    auth_info: tuple = Depends(get_store_auth)
):
    """
    Get transaction summary statistics for a specific store.

    By default, returns today's transactions only. Use start_date and end_date
    parameters to specify a different date range.

    Returns summary statistics including:
    - revenue: Total selling prices
    - transactions: Total number of transactions 
    - customers: Total number of unique customers who made purchases
    - date: Current local date time

    Args:
        start_date: Start date for the summary (optional, defaults to today)
        end_date: End date for the summary (optional, defaults to today)
        auth_info: Authentication and authorization info (injected)

    Returns:
        JSendResponse containing the summary statistics data for today (or specified date range)
    """
    try:
        user_id, store_info = auth_info
        store_id = store_info['id']

        # Parse dates using flexible format
        parsed_start_date = parse_flexible_date(start_date) if start_date else None
        parsed_end_date = parse_flexible_date(end_date, is_end_date=True) if end_date else None

        # Get statistics
        statistics = await get_transaction_statistics(
            store_id=store_id,
            start_date=parsed_start_date,
            end_date=parsed_end_date
        )

        return JSendResponse.success(statistics)
    except HTTPException as e:
        return JSendResponse.error(
            message=str(e.detail),
            code=e.status_code
        )
    except Exception as e:
        return JSendResponse.error(
            message=f"Failed to get summary: {str(e)}",
            code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

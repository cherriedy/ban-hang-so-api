"""
Schemas for reports operations.
"""
from datetime import datetime

from pydantic import BaseModel, Field


class SummaryResponse(BaseModel):
    """Summary response model."""
    revenue: float = Field(..., description="Total selling prices")
    transactions: int = Field(..., description="Total transactions")
    customers: int = Field(..., description="Total customers who made transactions")
    date: datetime = Field(..., description="Local date time")

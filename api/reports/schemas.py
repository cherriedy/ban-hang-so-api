"""
Schemas for reports operations.
"""
from datetime import datetime
from typing import List

from pydantic import BaseModel, Field


class SummaryResponse(BaseModel):
    """Summary response model."""
    revenue: float = Field(..., description="Total selling prices")
    transactions: int = Field(..., description="Total transactions")
    customers: int = Field(..., description="Total customers who made transactions")
    date: datetime = Field(..., description="Local date time")


class DateRangeSchema(BaseModel):
    """Date range schema for sales report."""
    start: str = Field(..., description="Start date in YYYY-MM-DD format")
    end: str = Field(..., description="End date in YYYY-MM-DD format")


class DataPointSchema(BaseModel):
    """Data point schema for daily data."""
    date: str = Field(..., description="Date in YYYY-MM-DD format")
    value: float = Field(..., description="Value for the date")


class RevenueByDateSchema(BaseModel):
    """Revenue by date schema."""
    unit: str = Field(..., description="Unit of measurement (e.g., 'thousand')")
    data: List[DataPointSchema] = Field(..., description="List of revenue data points by date")


class TransactionsByDateSchema(BaseModel):
    """Transactions by date schema."""
    data: List[DataPointSchema] = Field(..., description="List of transaction count data points by date")


class SummaryStatsSchema(BaseModel):
    """Summary statistics schema."""
    averageRevenue: float = Field(..., description="Average revenue per day")
    maxRevenue: float = Field(..., description="Maximum revenue in a single day")
    totalTransactions: int = Field(..., description="Total number of transactions")
    unit: str = Field(..., description="Unit of measurement (e.g., 'thousand')")


class SalesReportResponse(BaseModel):
    """Sales report response model."""
    currency: str = Field(default="VND", description="Currency code")
    granularity: str = Field(default="daily", description="Data granularity")
    dateRange: DateRangeSchema = Field(..., description="Date range of the report")
    revenue: float = Field(..., description="Total revenue in the period")
    cost: float = Field(..., description="Total cost in the period")
    profit: float = Field(..., description="Total profit in the period")
    revenueByDate: RevenueByDateSchema = Field(..., description="Revenue breakdown by date")
    transactionsByDate: TransactionsByDateSchema = Field(..., description="Transaction count breakdown by date")
    summary: SummaryStatsSchema = Field(..., description="Summary statistics")

import enum
from datetime import datetime, timezone
from typing import Optional, List
from beanie import Document
from pydantic import Field


class KYCStatus(str, enum.Enum):
    PENDING = "pending"
    SUBMITTED = "submitted"
    VERIFIED = "verified"
    REJECTED = "rejected"


class Client(Document):
    user_id: str
    phone: str
    country_code: str
    region: str
    currency: str = "USD"

    full_name: str
    date_of_birth: Optional[str] = None
    nationality: Optional[str] = None
    id_type: Optional[str] = None
    id_number: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None

    kyc_status: KYCStatus = KYCStatus.PENDING
    kyc_data: dict = Field(default_factory=dict)

    credit_score: int = 500
    total_loans: int = 0
    total_repaid: float = 0.0
    total_borrowed: float = 0.0
    default_count: int = 0

    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Settings:
        name = "clients"

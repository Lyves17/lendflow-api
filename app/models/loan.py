import enum
from datetime import datetime, timezone
from typing import Optional
from beanie import Document
from pydantic import Field


class LoanStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    DISBURSED = "disbursed"
    ACTIVE = "active"
    COMPLETED = "completed"
    DEFAULTED = "defaulted"
    REJECTED = "rejected"
    EXTENDED = "extended"


class LoanProduct(Document):
    name: str
    description: str = ""
    country_code: str
    currency: str
    min_amount: float
    max_amount: float
    min_term_days: int
    max_term_days: int
    interest_rate: float
    interest_type: str = "flat"
    processing_fee: float = 0.0
    late_fee: float = 0.0
    early_repayment_discount: float = 0.0
    max_extensions: int = 2
    extension_fee: float = 0.0
    is_active: bool = True
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Settings:
        name = "loan_products"


class Loan(Document):
    client_id: str
    product_id: str
    amount: float
    currency: str
    term_days: int
    interest_rate: float
    interest_amount: float = 0.0
    processing_fee: float = 0.0
    total_amount: float = 0.0
    amount_paid: float = 0.0
    balance: float = 0.0
    status: LoanStatus = LoanStatus.PENDING
    purpose: str = ""
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None
    disbursed_at: Optional[datetime] = None
    due_date: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    extensions_used: int = 0
    extension_history: list = Field(default_factory=list)
    credit_score_at_request: int = 0
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Settings:
        name = "loans"


class RepaymentStatus(str, enum.Enum):
    PENDING = "pending"
    PAID = "paid"
    LATE = "late"
    MISSED = "missed"


class Repayment(Document):
    loan_id: str
    installment_number: int
    amount_due: float
    amount_paid: float = 0.0
    due_date: datetime
    paid_date: Optional[datetime] = None
    status: RepaymentStatus = RepaymentStatus.PENDING
    late_fee: float = 0.0
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Settings:
        name = "repayments"

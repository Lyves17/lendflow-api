import enum
from datetime import datetime, timezone
from typing import Optional
from beanie import Document
from pydantic import Field


class PaymentProvider(str, enum.Enum):
    STRIPE = "stripe"
    FLUTTERWAVE = "flutterwave"
    MTN_MOMO = "mtn_momo"
    ORANGE_MONEY = "orange_money"
    WAVE = "wave"
    RAZORPAY = "razorpay"
    M_PESA = "m_pesa"
    BANK_TRANSFER = "bank_transfer"


class PaymentStatus(str, enum.Enum):
    PENDING = "pending"
    SUCCESS = "success"
    FAILED = "failed"
    REFUNDED = "refunded"


class Payment(Document):
    loan_id: str
    client_id: str
    amount: float
    currency: str
    provider: PaymentProvider
    provider_tx_id: Optional[str] = None
    status: PaymentStatus = PaymentStatus.PENDING
    metadata: dict = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: Optional[datetime] = None

    class Settings:
        name = "payments"

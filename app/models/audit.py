import enum
from datetime import datetime, timezone
from typing import Optional
from beanie import Document
from pydantic import Field


class AuditAction(str, enum.Enum):
    LOAN_CREATED = "loan_created"
    LOAN_APPROVED = "loan_approved"
    LOAN_REJECTED = "loan_rejected"
    LOAN_DISBURSED = "loan_disbursed"
    LOAN_COMPLETED = "loan_completed"
    LOAN_DEFAULTED = "loan_defaulted"
    LOAN_EXTENDED = "loan_extended"
    PAYMENT_RECEIVED = "payment_received"
    EARLY_REPAYMENT = "early_repayment"
    KYC_SUBMITTED = "kyc_submitted"
    KYC_VERIFIED = "kyc_verified"
    KYC_REJECTED = "kyc_rejected"
    CLIENT_CREATED = "client_created"
    CREDIT_SCORE_UPDATED = "credit_score_updated"
    REMINDER_SENT = "reminder_sent"


class AuditLog(Document):
    entity_type: str
    entity_id: str
    action: AuditAction
    actor_id: Optional[str] = None
    actor_name: Optional[str] = None
    details: dict = Field(default_factory=dict)
    ip_address: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Settings:
        name = "audit_logs"

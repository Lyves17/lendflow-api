import enum
from datetime import datetime, timezone
from typing import Optional
from beanie import Document
from pydantic import Field


class NotificationType(str, enum.Enum):
    LOAN_APPROVED = "loan_approved"
    LOAN_REJECTED = "loan_rejected"
    PAYMENT_RECEIVED = "payment_received"
    PAYMENT_FAILED = "payment_failed"
    REMINDER_DUE = "reminder_due"
    REMINDER_OVERDUE = "reminder_overdue"
    KYC_VERIFIED = "kyc_verified"
    LOAN_COMPLETED = "loan_completed"
    EXTENSION_APPROVED = "extension_approved"


class NotificationChannel(str, enum.Enum):
    SMS = "sms"
    EMAIL = "email"
    PUSH = "push"
    WEBHOOK = "webhook"


class Notification(Document):
    client_id: str
    type: NotificationType
    channel: NotificationChannel
    title: str
    message: str
    metadata: dict = Field(default_factory=dict)
    is_read: bool = False
    sent_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Settings:
        name = "notifications"


class WebhookConfig(Document):
    name: str
    url: str
    events: list = Field(default_factory=list)
    secret: str = ""
    is_active: bool = True
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Settings:
        name = "webhook_configs"


class WebhookLog(Document):
    webhook_id: str
    event: str
    payload: dict = Field(default_factory=dict)
    response_status: Optional[int] = None
    response_body: Optional[str] = None
    success: bool = False
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Settings:
        name = "webhook_logs"

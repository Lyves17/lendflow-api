from pydantic import BaseModel
from typing import Optional


class NotificationOut(BaseModel):
    id: str
    client_id: str
    type: str
    channel: str
    title: str
    message: str
    is_read: bool
    sent_at: Optional[str] = None
    created_at: str


class MarkRead(BaseModel):
    notification_id: str


class WebhookConfigCreate(BaseModel):
    name: str
    url: str
    events: list[str]
    secret: str = ""


class WebhookConfigOut(BaseModel):
    id: str
    name: str
    url: str
    events: list[str]
    is_active: bool
    created_at: str

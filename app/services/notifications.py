from datetime import datetime, timezone
from typing import Optional

from app.core.config import settings
from app.models.notification import Notification, NotificationType, NotificationChannel
from app.services.webhooks import dispatch_webhook


async def send_sms(phone: str, message: str) -> bool:
    if not settings.TWILIO_ACCOUNT_SID or not settings.TWILIO_AUTH_TOKEN:
        return False
    try:
        from twilio.rest import Client as TwilioClient
        twilio = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
        twilio.messages.create(body=message, from_=settings.TWILIO_PHONE_NUMBER, to=phone)
        return True
    except Exception:
        return False


async def send_email(to_email: str, subject: str, body: str) -> bool:
    if not settings.SENDGRID_API_KEY:
        return False
    try:
        import httpx
        async with httpx.AsyncClient() as client:
            await client.post(
                "https://api.sendgrid.com/v3/mail/send",
                headers={
                    "Authorization": f"Bearer {settings.SENDGRID_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "personalizations": [{"to": [{"email": to_email}]}],
                    "from": {"email": "noreply@lendflow.com", "name": "LendFlow"},
                    "subject": subject,
                    "content": [{"type": "text/plain", "value": body}],
                },
            )
        return True
    except Exception:
        return False


async def notify_client(
    client_id: str,
    notification_type: NotificationType,
    channel: NotificationChannel,
    title: str,
    message: str,
    phone: Optional[str] = None,
    email: Optional[str] = None,
    metadata: dict = None,
) -> Notification:
    notif = Notification(
        client_id=client_id,
        type=notification_type,
        channel=channel,
        title=title,
        message=message,
        metadata=metadata or {},
    )

    sent = False
    if channel == NotificationChannel.SMS and phone:
        sent = await send_sms(phone, message)
    elif channel == NotificationChannel.EMAIL and email:
        sent = await send_email(email, title, message)

    if sent:
        notif.sent_at = datetime.now(timezone.utc)

    await notif.insert()
    await dispatch_webhook(notification_type.value, {
        "client_id": client_id,
        "type": notification_type.value,
        "title": title,
        "message": message,
    })

    return notif


async def notify_loan_approved(client_id: str, loan_id: str, amount: float, currency: str, phone: str = None, email: str = None):
    return await notify_client(
        client_id=client_id,
        notification_type=NotificationType.LOAN_APPROVED,
        channel=NotificationChannel.SMS if phone else NotificationChannel.EMAIL,
        title="Prêt approuvé",
        message=f"Votre prêt de {amount} {currency} a été approuvé. Réf: {loan_id}",
        phone=phone, email=email,
        metadata={"loan_id": loan_id, "amount": amount, "currency": currency},
    )


async def notify_loan_rejected(client_id: str, loan_id: str, reason: str = "", phone: str = None, email: str = None):
    return await notify_client(
        client_id=client_id,
        notification_type=NotificationType.LOAN_REJECTED,
        channel=NotificationChannel.SMS if phone else NotificationChannel.EMAIL,
        title="Prêt refusé",
        message=f"Votre demande de prêt a été refusée. {reason}".strip(),
        phone=phone, email=email,
        metadata={"loan_id": loan_id, "reason": reason},
    )


async def notify_payment_received(client_id: str, loan_id: str, amount: float, currency: str, phone: str = None, email: str = None):
    return await notify_client(
        client_id=client_id,
        notification_type=NotificationType.PAYMENT_RECEIVED,
        channel=NotificationChannel.SMS if phone else NotificationChannel.EMAIL,
        title="Paiement reçu",
        message=f"Paiement de {amount} {currency} reçu pour le prêt {loan_id}.",
        phone=phone, email=email,
        metadata={"loan_id": loan_id, "amount": amount, "currency": currency},
    )


async def notify_reminder_due(client_id: str, loan_id: str, days_before: int, amount: float, phone: str = None, email: str = None):
    return await notify_client(
        client_id=client_id,
        notification_type=NotificationType.REMINDER_DUE,
        channel=NotificationChannel.SMS if phone else NotificationChannel.EMAIL,
        title="Rappel de paiement",
        message=f"Rappel: votre paiement de {amount} est dû dans {days_before} jour(s). Réf: {loan_id}",
        phone=phone, email=email,
        metadata={"loan_id": loan_id, "days_before": days_before, "amount": amount},
    )


async def notify_reminder_overdue(client_id: str, loan_id: str, days_overdue: int, amount: float, phone: str = None, email: str = None):
    return await notify_client(
        client_id=client_id,
        notification_type=NotificationType.REMINDER_OVERDUE,
        channel=NotificationChannel.SMS if phone else NotificationChannel.EMAIL,
        title="Paiement en retard",
        message=f"ALERTE: Votre paiement de {amount} a {days_overdue} jour(s) de retard. Réf: {loan_id}",
        phone=phone, email=email,
        metadata={"loan_id": loan_id, "days_overdue": days_overdue, "amount": amount},
    )


async def notify_extension_approved(client_id: str, loan_id: str, new_due_date: str, phone: str = None, email: str = None):
    return await notify_client(
        client_id=client_id,
        notification_type=NotificationType.EXTENSION_APPROVED,
        channel=NotificationChannel.SMS if phone else NotificationChannel.EMAIL,
        title="Extension approuvée",
        message=f"Votre prêt {loan_id} a été prolongé. Nouvelle date limite: {new_due_date}",
        phone=phone, email=email,
        metadata={"loan_id": loan_id, "new_due_date": new_due_date},
    )

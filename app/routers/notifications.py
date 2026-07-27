from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Depends, Query
from typing import List

from app.models.user import User, UserRole
from app.models.notification import Notification
from app.schemas.notification import NotificationOut, MarkRead
from app.core.security import get_current_user

router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.get("/", response_model=List[NotificationOut])
async def list_notifications(
    user: User = Depends(get_current_user),
    unread_only: bool = Query(False),
):
    query = {"client_id": str(user.id)}
    if unread_only:
        query["is_read"] = False

    notifs = await Notification.find(query).sort([("created_at", -1)]).limit(50).to_list()
    return [NotificationOut(
        id=str(n.id), client_id=n.client_id, type=n.type.value,
        channel=n.channel.value, title=n.title, message=n.message,
        is_read=n.is_read, sent_at=str(n.sent_at) if n.sent_at else None,
        created_at=str(n.created_at),
    ) for n in notifs]


@router.get("/unread-count")
async def unread_count(user: User = Depends(get_current_user)):
    count = await Notification.find(
        Notification.client_id == str(user.id),
        Notification.is_read == False,
    ).count()
    return {"unread_count": count}


@router.post("/mark-read")
async def mark_read(data: MarkRead, user: User = Depends(get_current_user)):
    notif = await Notification.get(data.notification_id)
    if not notif or notif.client_id != str(user.id):
        raise HTTPException(status_code=404, detail="Notification introuvable")

    notif.is_read = True
    await notif.save()
    return {"message": "Notification marquée comme lue"}


@router.post("/mark-all-read")
async def mark_all_read(user: User = Depends(get_current_user)):
    notifs = await Notification.find(
        Notification.client_id == str(user.id),
        Notification.is_read == False,
    ).to_list()
    for n in notifs:
        n.is_read = True
        await n.save()
    return {"message": f"{len(notifs)} notification(s) marquée(s) comme lue(s)"}

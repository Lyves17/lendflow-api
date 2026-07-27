import hashlib
import hmac
import json
from datetime import datetime, timezone
from typing import List

import httpx

from app.models.notification import WebhookConfig, WebhookLog


async def dispatch_webhook(event: str, payload: dict):
    try:
        configs = await WebhookConfig.find(
            WebhookConfig.is_active == True,
        ).to_list()
        configs = [c for c in configs if event in c.events]
    except Exception:
        return

    if not configs:
        return

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            for config in configs:
                body = json.dumps(payload, default=str)
                headers = {"Content-Type": "application/json"}

                if config.secret:
                    sig = hmac.new(config.secret.encode(), body.encode(), hashlib.sha256).hexdigest()
                    headers["X-Webhook-Signature"] = f"sha256={sig}"

                log = WebhookLog(
                    webhook_id=str(config.id),
                    event=event,
                    payload=payload,
                    success=False,
                )

                try:
                    resp = await client.post(config.url, content=body, headers=headers)
                    log.response_status = resp.status_code
                    log.response_body = resp.text[:2000]
                    log.success = 200 <= resp.status_code < 300
                except Exception as e:
                    log.response_body = str(e)[:2000]
                    log.success = False

                await log.insert()
    except Exception:
        pass

import firebase_admin
from firebase_admin import messaging
from app.core.config import settings
import asyncio
import json


async def send_fcm_notification(
    fcm_token: str,
    title: str,
    body: str,
    notification_id: str,
):
    if not settings.FIREBASE_CREDENTIALS_PATH:
        print("[FCM] Skipping send: FIREBASE_CREDENTIALS_PATH is not configured")
        return False

    try:
        if not firebase_admin._apps:
            cred = firebase_admin.credentials.Certificate(settings.FIREBASE_CREDENTIALS_PATH)
            firebase_admin.initialize_app(cred)

        message = messaging.Message(
            notification=messaging.Notification(
                title=title,
                body=body,
            ),
            data={
                "notification_id": notification_id,
                "event": "student_notification",
            },
            token=fcm_token,
        )

        response = await asyncio.to_thread(messaging.send, message)
        print(json.dumps({
            "event": "fcm_accepted",
            "notification_id": notification_id,
            "firebase_message_id": response,
            "token_prefix": fcm_token[:12],
        }))
        return True
    except Exception as e:
        print(json.dumps({
            "event": "fcm_send_failed",
            "notification_id": notification_id,
            "token_prefix": fcm_token[:12],
            "error": str(e),
        }))
        return False

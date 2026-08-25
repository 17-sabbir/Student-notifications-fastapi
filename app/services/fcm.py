import firebase_admin
from firebase_admin import messaging
from app.core.config import settings
import asyncio


async def send_fcm_notification(fcm_token: str, title: str, body: str):
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
            token=fcm_token,
        )

        response = await asyncio.to_thread(messaging.send, message)
        print(f"[FCM] Sent to {fcm_token[:20]}... message_id={response}")
        return True
    except Exception as e:
        print(f"[FCM] Error sending to {fcm_token[:20]}...: {e}")
        return False

"""Push notification routes using Firebase Cloud Messaging."""

import logging
import os
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter()

# In-memory token storage (use Redis/database in production)
FCM_TOKENS: dict[str, dict] = {}

# Firebase Admin SDK (lazy loaded)
_firebase_app = None


def get_firebase_app():
    """Initialize Firebase Admin SDK."""
    global _firebase_app
    if _firebase_app is not None:
        return _firebase_app

    try:
        import firebase_admin
        from firebase_admin import credentials

        # Check if already initialized
        try:
            _firebase_app = firebase_admin.get_app()
            return _firebase_app
        except ValueError:
            pass

        # Try to initialize with service account
        cred_path = os.getenv("FIREBASE_SERVICE_ACCOUNT_PATH")
        if cred_path and os.path.exists(cred_path):
            cred = credentials.Certificate(cred_path)
            _firebase_app = firebase_admin.initialize_app(cred)
        else:
            # Try to use application default credentials (for Azure/GCP)
            cred = credentials.ApplicationDefault()
            _firebase_app = firebase_admin.initialize_app(cred)

        return _firebase_app
    except Exception as e:
        logger.warning(f"Firebase Admin SDK not initialized: {e}")
        return None


class TokenRegistration(BaseModel):
    """FCM token registration request."""
    token: str
    user_id: Optional[str] = None
    device_info: Optional[dict] = None


class NotificationRequest(BaseModel):
    """Send notification request."""
    title: str
    body: str
    token: Optional[str] = None  # Send to specific token
    topic: Optional[str] = None  # Send to topic
    data: Optional[dict] = None  # Custom data payload


@router.post("/register")
async def register_token(request: TokenRegistration):
    """Register an FCM token for push notifications."""
    token_id = request.token[:20]  # Use first 20 chars as ID

    FCM_TOKENS[token_id] = {
        "token": request.token,
        "user_id": request.user_id,
        "device_info": request.device_info,
        "registered_at": __import__("datetime").datetime.utcnow().isoformat(),
    }

    logger.info(f"Registered FCM token: {token_id}...")
    return {"status": "registered", "token_id": token_id}


@router.delete("/unregister/{token_id}")
async def unregister_token(token_id: str):
    """Unregister an FCM token."""
    if token_id in FCM_TOKENS:
        del FCM_TOKENS[token_id]
        return {"status": "unregistered"}
    raise HTTPException(status_code=404, detail="Token not found")


@router.post("/send")
async def send_notification(request: NotificationRequest):
    """Send a push notification via Firebase Cloud Messaging."""
    firebase_app = get_firebase_app()

    if not firebase_app:
        raise HTTPException(
            status_code=503,
            detail="Firebase not configured. Set FIREBASE_SERVICE_ACCOUNT_PATH.",
        )

    try:
        from firebase_admin import messaging

        # Build notification
        notification = messaging.Notification(
            title=request.title,
            body=request.body,
        )

        # Build message
        if request.token:
            # Send to specific device
            message = messaging.Message(
                notification=notification,
                data=request.data or {},
                token=request.token,
            )
            response = messaging.send(message)
        elif request.topic:
            # Send to topic
            message = messaging.Message(
                notification=notification,
                data=request.data or {},
                topic=request.topic,
            )
            response = messaging.send(message)
        else:
            raise HTTPException(
                status_code=400,
                detail="Either token or topic must be provided",
            )

        logger.info(f"Notification sent: {response}")
        return {"status": "sent", "message_id": response}

    except Exception as e:
        logger.error(f"Failed to send notification: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/send-to-all")
async def send_to_all_tokens(request: NotificationRequest):
    """Send notification to all registered tokens."""
    firebase_app = get_firebase_app()

    if not firebase_app:
        raise HTTPException(
            status_code=503,
            detail="Firebase not configured.",
        )

    if not FCM_TOKENS:
        return {"status": "no_tokens", "sent": 0}

    try:
        from firebase_admin import messaging

        notification = messaging.Notification(
            title=request.title,
            body=request.body,
        )

        messages = []
        for token_data in FCM_TOKENS.values():
            messages.append(
                messaging.Message(
                    notification=notification,
                    data=request.data or {},
                    token=token_data["token"],
                )
            )

        response = messaging.send_all(messages)

        return {
            "status": "sent",
            "success_count": response.success_count,
            "failure_count": response.failure_count,
        }

    except Exception as e:
        logger.error(f"Failed to send notifications: {e}")
        raise HTTPException(status_code=500, detail=str(e))


async def notify_render_complete(
    project_id: str,
    job_id: str,
    project_name: str,
    render_url: Optional[str] = None,
):
    """Send notification when a render job completes."""
    firebase_app = get_firebase_app()
    if not firebase_app:
        logger.warning("Firebase not configured, skipping notification")
        return

    try:
        from firebase_admin import messaging

        notification = messaging.Notification(
            title="Render Complete",
            body=f"Your render for '{project_name}' is ready!",
        )

        data = {
            "type": "render_complete",
            "project_id": project_id,
            "job_id": job_id,
            "url": render_url or "",
        }

        # Send to all registered tokens
        for token_data in FCM_TOKENS.values():
            try:
                message = messaging.Message(
                    notification=notification,
                    data=data,
                    token=token_data["token"],
                )
                messaging.send(message)
            except Exception as e:
                logger.warning(f"Failed to send to token: {e}")

    except Exception as e:
        logger.error(f"Failed to send render notification: {e}")


@router.get("/status")
async def get_notification_status():
    """Check notification service status."""
    firebase_app = get_firebase_app()

    return {
        "firebase_configured": firebase_app is not None,
        "registered_tokens": len(FCM_TOKENS),
    }

import hmac
import hashlib
import time
from typing import Optional

class WebhookSignatureError(Exception):
    pass

def verify_webhook_signature(
    body: bytes,
    signature_header: str,
    secret: bytes,
    timestamp_header: Optional[str] = None,
    max_age_seconds: int = 300
) -> bool:
    """
    Secure HMAC-SHA256 webhook signature verification.
    """
    # 1. Validate signature header format
    if not signature_header or not signature_header.startswith("sha256="):
        raise WebhookSignatureError("Invalid signature header format")

    provided_signature = signature_header.split("=", 1)[1]

    # 2. Optional replay protection
    if timestamp_header:
        try:
            request_time = int(timestamp_header)
            if abs(int(time.time()) - request_time) > max_age_seconds:
                raise WebhookSignatureError("Request timestamp too old or from future")
        except (ValueError, TypeError):
            raise WebhookSignatureError("Invalid timestamp")

    # 3. Compute expected signature from raw body
    expected_signature = hmac.new(
        secret,
        body,
        hashlib.sha256
    ).hexdigest()

    # 4. Constant-time comparison (very important)
    if not hmac.compare_digest(provided_signature, expected_signature):
        raise WebhookSignatureError("Signature verification failed")

    return True

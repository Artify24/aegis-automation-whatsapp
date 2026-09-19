"""AegisBot Enterprise Security, Rate Limiting & Webhook Authentication.

Features:
  1. Per-phone sliding window rate limiting (DoS & credit drain protection)
  2. Meta Cloud API HMAC-SHA256 signature validation (X-Hub-Signature-256)
  3. Prompt injection detection & input sanitization
  4. PII masking for GDPR / privacy compliance in logs
"""
from __future__ import annotations

import hashlib
import hmac
import logging
import re
import time
from collections import defaultdict
from typing import Dict, List, Optional, Tuple

import config

logger = logging.getLogger("aegisbot.security")

# Rate limit settings: 20 messages per 60 seconds per phone number
RATE_LIMIT_WINDOW = 60  # seconds
RATE_LIMIT_MAX_REQUESTS = 20

# In-memory sliding window: wa_id -> list of timestamps
_rate_limits: Dict[str, List[float]] = defaultdict(list)


def check_rate_limit(wa_id: str) -> Tuple[bool, int]:
    """Check if wa_id is within allowed rate limit.
    
    Returns (is_allowed, remaining_requests).
    """
    now = time.time()
    cutoff = now - RATE_LIMIT_WINDOW
    # Purge expired timestamps
    _rate_limits[wa_id] = [t for t in _rate_limits[wa_id] if t > cutoff]

    if len(_rate_limits[wa_id]) >= RATE_LIMIT_MAX_REQUESTS:
        logger.warning("Rate limit exceeded for wa_id: %s (%d requests in 60s)",
                       mask_phone(wa_id), len(_rate_limits[wa_id]))
        return False, 0

    _rate_limits[wa_id].append(now)
    remaining = RATE_LIMIT_MAX_REQUESTS - len(_rate_limits[wa_id])
    return True, remaining


def verify_meta_signature(payload_bytes: bytes, signature_header: Optional[str]) -> bool:
    """Verify X-Hub-Signature-256 header from Meta Cloud API."""
    if not config.WA_APP_SECRET:
        # If secret not configured in local testing, allow through
        return True

    if not signature_header or not signature_header.startswith("sha256="):
        logger.warning("Missing or malformed Meta X-Hub-Signature-256 header")
        return False

    expected_sig = signature_header.split("sha256=")[1].strip()
    computed_sig = hmac.new(
        config.WA_APP_SECRET.encode("utf-8"),
        payload_bytes,
        hashlib.sha256,
    ).hexdigest()

    is_valid = hmac.compare_digest(computed_sig, expected_sig)
    if not is_valid:
        logger.error("Meta webhook signature verification failed!")
    return is_valid


# Known prompt injection & jailbreak patterns
_INJECTION_PATTERNS = [
    r"ignore\s+(all\s+)?(previous|prior|above|existing)?\s*(instructions|rules|prompts|guidelines)",
    r"you\s+are\s+now\s+(DAN|unfiltered|jailbroken)",
    r"(reveal|give|show|print|display|tell)\s+(me\s+)?(your\s+)?(system\s+prompt|instructions|secret\s+key|initial\s+prompt)",
    r"override\s+(all\s+)?(safety\s+guidelines|rules|instructions)",
    r"<\|\s*im_start\s*\|>",
    r"<\|\s*im_end\s*\|>",
]


def detect_prompt_injection(text: str) -> bool:
    """Detect common adversarial prompt injection and jailbreak attempts."""
    lower = text.lower()
    for pattern in _INJECTION_PATTERNS:
        if re.search(pattern, lower, re.IGNORECASE):
            logger.warning("Potential prompt injection pattern detected: '%s'", pattern)
            return True
    return False


def sanitize_input(text: str, max_length: int = 2000) -> str:
    """Clean and truncate customer input to prevent buffer overflows and prompt attacks."""
    if not text:
        return ""
    # Strip null bytes and excessive unprintable controls
    cleaned = "".join(ch for ch in text if ch == "\n" or ch == "\t" or ord(ch) >= 32)
    # Truncate
    return cleaned[:max_length].strip()


def mask_phone(phone: str) -> str:
    """Mask phone number for privacy-compliant logging (e.g. 919876543210 -> 9198****3210)."""
    p = str(phone or "").strip()
    if len(p) <= 6:
        return p
    prefix = p[:4]
    suffix = p[-4:]
    return f"{prefix}****{suffix}"

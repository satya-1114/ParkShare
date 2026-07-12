import secrets
import string
from datetime import datetime, timezone

_ALPHABET = string.ascii_uppercase + string.digits


def generate_booking_reference() -> str:
    year = datetime.now(timezone.utc).year
    suffix = "".join(secrets.choice(_ALPHABET) for _ in range(6))
    return f"PS-{year}-{suffix}"

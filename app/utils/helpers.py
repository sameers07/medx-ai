"""Small shared helpers with no other natural home."""
import uuid


def new_request_id() -> str:
    return str(uuid.uuid4())

import secrets
import string


def generate_token(length: int = 32) -> str:
    """Generate a cryptographically safe URL-safe token."""
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))

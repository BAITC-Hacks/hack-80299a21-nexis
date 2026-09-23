import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")


def env_int(name: str, default: int, minimum: int = 1, maximum: int = 100000) -> int:
    return max(minimum, min(maximum, int(os.getenv(name, str(default)))))


PUBLIC_URL = os.getenv("BACKEND_PUBLIC_URL", "http://localhost:8000").rstrip("/")
DB_PATH = os.getenv("NEXIS_DB_PATH", str(ROOT / "database" / "nexis.sqlite3"))
SESSION_TTL = env_int("SESSION_TTL_SECONDS", 86400, 600, 604800)
OFFER_TTL = env_int("OFFER_TTL_SECONDS", 600, 30, 3600)


class ServiceError(Exception):
    def __init__(self, message: str, code: str = "unavailable", status: int = 503):
        super().__init__(message)
        self.message, self.code, self.status = message, code, status

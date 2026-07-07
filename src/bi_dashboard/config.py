import os


class Config:
    REDIS_URL = os.environ.get("REDIS_URL", "")
    BI_REDIS_DB = int(os.environ.get("BI_REDIS_DB", "5"))

    COOKIE_SESSION_SECRET = os.environ.get("COOKIE_SESSION_SECRET", "")
    SESSION_COOKIE = os.environ.get("SESSION_COOKIE", "bi_session")
    SESSION_TTL_SECONDS = int(os.environ.get("SESSION_TTL_SECONDS", "43200"))
    COOKIE_SECURE = os.environ.get("COOKIE_SECURE", "true").lower() == "true"

    LOGIN_MAX_FAILURES = int(os.environ.get("LOGIN_MAX_FAILURES", "8"))
    LOGIN_LOCKOUT_SECONDS = int(os.environ.get("LOGIN_LOCKOUT_SECONDS", "900"))
    LOGIN_FAILURE_WINDOW_SECONDS = int(os.environ.get("LOGIN_FAILURE_WINDOW_SECONDS", "900"))

    SECRET_STORE_PATH = os.environ.get("SECRET_STORE_PATH", "/app/data/secrets.json")
    ADMIN_PW_HASH = os.environ.get("ADMIN_PW_HASH", "")
    ADMIN_TOTP_SECRET = os.environ.get("ADMIN_TOTP_SECRET", "")
    BI_USER_NAME = os.environ.get("BI_USER_NAME", "admin")


config = Config()

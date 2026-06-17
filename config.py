import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


class Config:
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL", f"sqlite:///{os.path.join(BASE_DIR, 'dayquest.db')}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key")

    # IANA timezone the scheduler treats as "local". All wall-clock reasoning
    # (the 8-22 window, "now", deadlines, soft targets) happens in this zone.
    # Configurable via env so it isn't hardcoded; defaults to US Eastern.
    LOCAL_TIMEZONE = os.environ.get("DAYQUEST_TIMEZONE", "America/New_York")

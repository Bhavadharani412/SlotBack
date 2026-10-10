import os
from urllib.parse import urlsplit, urlunsplit
import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from backend.app.core.config import settings
from backend.app.db.session import Base, get_db
from backend.app.main import app
import backend.app.models  # noqa: F401


def get_test_database_url() -> str:
    url = os.environ.get("TEST_DATABASE_URL") or settings.test_database_url
    if not url:
        dev_url = settings.database_url
        parts = urlsplit(dev_url)
        # Replace only the database name path, keeping the username and password intact
        new_path = "/slotback_test" if parts.path in ("/slotback", "", "/") else parts.path + "_test"
        url = urlunsplit((parts.scheme, parts.netloc, new_path, parts.query, parts.fragment))

    # Invariant: Never allow tests to run against the main development database
    parsed = urlsplit(url)
    if parsed.path.rstrip("/") == "/slotback":
        raise RuntimeError(
            "CRITICAL SAFETY VIOLATION: Refusing to run tests against the main development database ('slotback'). "
            "Please configure TEST_DATABASE_URL pointing to 'slotback_test'."
        )
    return url


test_db_url = get_test_database_url()
test_engine = create_engine(test_db_url, pool_pre_ping=True)
TestingSessionLocal = sessionmaker(bind=test_engine, autoflush=False, expire_on_commit=False)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(autouse=True, scope="session")
def setup_test_db():
    # Verify connection
    try:
        with test_engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception as exc:
        pytest.fail(f"Could not connect to isolated test database ({test_db_url}): {exc}")

    # Ensure schema exists on test database
    Base.metadata.create_all(bind=test_engine)

    # Override FastAPI DB dependency
    app.dependency_overrides[get_db] = override_get_db

    yield

    app.dependency_overrides.pop(get_db, None)


@pytest.fixture(autouse=True)
def clean_test_tables():
    """Clean all tables before each test to ensure test isolation."""
    with TestingSessionLocal() as session:
        # Clean in reverse foreign key order
        session.execute(text("DELETE FROM notification_logs"))
        session.execute(text("DELETE FROM recovery_offers"))
        session.execute(text("DELETE FROM waitlist_entries"))
        session.execute(text("DELETE FROM appointments"))
        session.execute(text("DELETE FROM services"))
        session.execute(text("DELETE FROM business_settings"))
        session.commit()
    yield

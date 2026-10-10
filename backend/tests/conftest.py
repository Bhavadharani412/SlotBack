import os
from urllib.parse import urlsplit, urlunsplit

import backend.app.models  # noqa: F401
import pytest
from backend.app.core.auth import ensure_initial_admin
from backend.app.core.config import settings
from backend.app.core.rate_limit import limiter
from backend.app.core.security import create_access_token, hash_password
from backend.app.db.session import Base, get_db
from backend.app.main import app
from backend.app.models.domain import User
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker


def get_test_database_url() -> str:
    url = os.environ.get("TEST_DATABASE_URL") or settings.test_database_url
    if not url:
        dev_url = settings.database_url
        parts = urlsplit(dev_url)
        new_path = (
            "/slotback_test" if parts.path in ("/slotback", "", "/") else parts.path + "_test"
        )
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
def clean_test_tables(request):
    """Clean all tables before each test to ensure test isolation."""
    # Reset rate limiter
    limiter.reset()

    # Skip function-level wiping for e2e browser tests which manage their own module-level state
    if "e2e" in request.node.nodeid:
        yield
        return

    with TestingSessionLocal() as session:
        # Clean in reverse foreign key order
        session.execute(text("DELETE FROM notification_logs"))
        session.execute(text("DELETE FROM recovery_offers"))
        session.execute(text("DELETE FROM waitlist_entries"))
        session.execute(text("DELETE FROM appointments"))
        session.execute(text("DELETE FROM services"))
        session.execute(text("DELETE FROM business_settings"))
        session.execute(text("DELETE FROM users"))
        session.commit()

        # Seed initial admin user for tests
        ensure_initial_admin(session)

    yield


@pytest.fixture
def admin_token() -> str:
    """Return a valid JWT access token for the test admin user."""
    with TestingSessionLocal() as session:
        admin = session.query(User).filter(User.email == settings.initial_admin_email).first()
        if not admin:
            admin = ensure_initial_admin(session)
        assert admin is not None
        return create_access_token(
            data={
                "sub": admin.id,
                "email": admin.email,
                "role": admin.role,
                "business_id": admin.business_id,
            }
        )


@pytest.fixture
def admin_headers(admin_token: str) -> dict[str, str]:
    """HTTP headers with admin Authorization Bearer token."""
    return {"Authorization": f"Bearer {admin_token}"}


@pytest.fixture
def staff_token() -> str:
    """Create and return a valid JWT access token for a non-admin staff member."""
    with TestingSessionLocal() as session:
        staff_user = User(
            email="staff.test@slotback.com",
            hashed_password=hash_password("StaffPass123!"),
            full_name="Regular Staff",
            role="staff",
            business_id="1",
            is_active=True,
        )
        session.add(staff_user)
        session.commit()
        session.refresh(staff_user)
        return create_access_token(
            data={
                "sub": staff_user.id,
                "email": staff_user.email,
                "role": staff_user.role,
                "business_id": staff_user.business_id,
            }
        )


@pytest.fixture
def staff_headers(staff_token: str) -> dict[str, str]:
    """HTTP headers with staff Authorization Bearer token."""
    return {"Authorization": f"Bearer {staff_token}"}

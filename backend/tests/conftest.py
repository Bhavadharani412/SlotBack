import pytest
from backend.app.db.session import Base, engine
import backend.app.models  # noqa: F401

@pytest.fixture(autouse=True, scope="session")
def setup_test_db():
    Base.metadata.create_all(bind=engine)
    yield

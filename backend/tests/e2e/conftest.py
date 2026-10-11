import os
import socket
import threading
import time
from collections.abc import Generator

import httpx
import pytest
import uvicorn
from backend.app.main import app
from backend.tests.conftest import get_test_database_url


def get_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


class UvicornTestServer(uvicorn.Server):
    def install_signal_handlers(self):
        pass


class ServerThread(threading.Thread):
    def __init__(self, host: str, port: int):
        super().__init__(daemon=True)
        self.host = host
        self.port = port
        self.server = None

    def run(self):
        config = uvicorn.Config(
            app=app,
            host=self.host,
            port=self.port,
            log_level="warning",
            loop="asyncio",
        )
        self.server = UvicornTestServer(config=config)
        self.server.run()

    def stop(self):
        if self.server:
            self.server.should_exit = True


@pytest.fixture(scope="session")
def live_server_url() -> Generator[str, None, None]:
    """
    Dedicated test server fixture for Playwright E2E tests.
    Guarantees that E2E tests always run against the isolated test database
    and never target or pollute the development database.
    """
    # 1. Enforce strict database safety:
    # get_test_database_url() raises RuntimeError if the database URL points to /slotback (the dev DB).
    test_db_url = get_test_database_url()
    assert "/slotback" != test_db_url.split("/")[-1].split("?")[0], (
        "CRITICAL SAFETY VIOLATION: E2E tests cannot target the dev database."
    )

    # 2. Check if a custom test server URL was explicitly provided (e.g., in CI or staging)
    env_url = os.environ.get("SLOTBACK_BASE_URL")
    if env_url:
        yield env_url
        return

    # 3. Otherwise, spawn an ephemeral FastAPI test server bound to a free port
    port = get_free_port()
    host = "127.0.0.1"
    server_thread = ServerThread(host, port)
    server_thread.start()

    url = f"http://{host}:{port}"

    # Poll /health until server is responsive (up to 10 seconds)
    start_time = time.time()
    ready = False
    while time.time() - start_time < 10:
        try:
            res = httpx.get(f"{url}/health", timeout=1.0)
            if res.status_code == 200:
                ready = True
                break
        except Exception:
            time.sleep(0.1)

    if not ready:
        server_thread.stop()
        raise RuntimeError(f"Failed to start isolated E2E test server on {url}")

    yield url

    server_thread.stop()

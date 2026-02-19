import pytest
import subprocess
import time
import socket
from contextlib import closing
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright


# ##################################################################
# find free port
# binds to port 0 to let the os assign an available port
def find_free_port():
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
        s.bind(("", 0))
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        return s.getsockname()[1]


# ##################################################################
# server port fixture
# provides a free port for the test server session
@pytest.fixture(scope="session")
def server_port():
    return find_free_port()


# ##################################################################
# server fixture
# starts fastapi server as subprocess and yields url when ready
@pytest.fixture(scope="session")
def server(server_port):
    project_root = Path(__file__).parent.parent

    proc = subprocess.Popen(
        [
            sys.executable, "-m", "uvicorn",
            "src.server:app",
            "--host", "127.0.0.1",
            "--port", str(server_port),
        ],
        cwd=project_root,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    server_url = f"http://127.0.0.1:{server_port}"
    max_attempts = 30
    for _ in range(max_attempts):
        try:
            import httpx
            response = httpx.get(f"{server_url}/health", timeout=1.0)
            if response.status_code == 200:
                break
        except Exception:
            pass
        time.sleep(0.5)
    else:
        proc.terminate()
        raise RuntimeError(f"Server failed to start on port {server_port}")

    yield server_url

    proc.terminate()
    try:
        proc.wait(timeout=3)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait(timeout=2)


# ##################################################################
# shared browser fixture
# single chromium instance reused across all tests (WASM compile cache)
@pytest.fixture(scope="session")
def shared_browser():
    pw = sync_playwright().start()
    browser = pw.chromium.launch(
        headless=True,
        args=["--enable-webgl", "--use-gl=angle", "--enable-gpu"]
    )
    yield browser
    browser.close()
    pw.stop()


# ##################################################################
# cad page fixture
# session-scoped page with OC.js loaded for evaluate-only CAD tests
@pytest.fixture(scope="session")
def cad_page(server, shared_browser):
    page = shared_browser.new_page()
    page.goto(f"{server}/")
    page.wait_for_function(
        """() => {
            const statusText = document.getElementById('status-text');
            return statusText && statusText.textContent === 'Ready' && window.Workplane;
        }""",
        timeout=90000
    )
    yield page
    page.close()


# ##################################################################
# init page fixture
# session-scoped page on /init-test with OC.js loaded
@pytest.fixture(scope="session")
def init_page(server, shared_browser):
    page = shared_browser.new_page()
    page.goto(f"{server}/init-test")
    page.wait_for_function(
        """() => {
            const status = document.getElementById('status');
            return status && status.classList.contains('success');
        }""",
        timeout=60000
    )
    yield page
    page.close()

import socket
import subprocess
import sys
import time
from contextlib import closing
from pathlib import Path

import httpx
import pytest
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
def server(server_port, tmp_path_factory):
    project_root = Path(__file__).parent.parent

    # isolate the test server's ONE persistent agentd3 chat conversation from
    # the deployment state: each test session gets its own state file and a
    # test source/model via test-harness variables, so tests never touch the
    # production conversation at local/agentd3-chat.json
    import os

    state_path = tmp_path_factory.mktemp("agentd3-state") / "agentd3-chat.json"
    proc = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "src.server:app",
            "--host",
            "127.0.0.1",
            "--port",
            str(server_port),
        ],
        cwd=project_root,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env={
            **os.environ,
            "DAZCAD_AGENTD3_STATE": str(state_path),
            "DAZCAD_AGENTD3_SOURCE": "daz-cad-test",
            "DAZCAD_AGENTD3_MODEL": "agentic-low",
        },
    )

    server_url = f"http://127.0.0.1:{server_port}"
    max_attempts = 30
    last_error = "health endpoint has not returned success"
    for _ in range(max_attempts):
        try:
            response = httpx.get(f"{server_url}/health", timeout=1.0)
            if response.status_code == 200:
                break
        except httpx.RequestError as error:
            last_error = str(error)
        time.sleep(0.5)
    else:
        proc.terminate()
        raise RuntimeError(f"Server failed to start on port {server_port}: {last_error}")

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
    browser = pw.chromium.launch(headless=True, args=["--enable-webgl", "--use-gl=angle", "--enable-gpu"])
    yield browser
    browser.close()
    pw.stop()


# ##################################################################
# cad page fixture
# session-scoped page with OC.js loaded for evaluate-only CAD tests
@pytest.fixture(scope="session")
def cad_page(server, shared_browser):
    page = shared_browser.new_page()
    failures = []
    messages = []
    page.on("requestfailed", lambda request: failures.append(f"{request.url}: {request.failure}"))
    page.on("pageerror", lambda error: failures.append(str(error)))
    page.on("console", lambda message: messages.append(message.text))
    page.goto(f"{server}/")
    try:
        page.wait_for_function(
            """() => {
                const statusText = document.getElementById('status-text');
                return statusText && statusText.textContent === 'Ready' && window.Workplane;
            }""",
            timeout=90000,
        )
    except Exception as error:
        status = page.locator("#status-text").inner_text()
        page.close()
        raise RuntimeError(f"CAD startup failed: status={status}; requests={failures}; console={messages[-15:]}") from error
    yield page
    page.close()


# ##################################################################
# init page fixture
# session-scoped page on /init-test with OC.js loaded
@pytest.fixture(scope="session")
def init_page(server, shared_browser):
    page = shared_browser.new_page()
    failures = []
    page.on("requestfailed", lambda request: failures.append(f"{request.url}: {request.failure}"))
    page.on("pageerror", lambda error: failures.append(str(error)))
    page.goto(f"{server}/init-test")
    try:
        page.wait_for_function(
            """() => {
                const status = document.getElementById('status');
                return status && status.classList.contains('success');
            }""",
            timeout=60000,
        )
    except Exception as error:
        diagnostics = page.locator("body").inner_text()
        page.close()
        raise RuntimeError(f"OpenCascade startup failed: {failures}\n{diagnostics}") from error
    yield page
    page.close()

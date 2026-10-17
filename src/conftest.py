import re
import socket
import subprocess
import sys
import time
from contextlib import closing
from pathlib import Path

import httpx
import pytest
from playwright.sync_api import sync_playwright

from src.cdn_cache import RecordedBrowser, recorded_resource


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
    models_path = tmp_path_factory.mktemp("cad-models") / "models"
    log_path = project_root / "output" / "testing" / f"server-{server_port}.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_stream = log_path.open("w")
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
        stdout=log_stream,
        stderr=subprocess.STDOUT,
        env={
            **os.environ,
            "DAZCAD_MODELS_DIR": str(models_path),
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
        log_stream.close()
        raise RuntimeError(f"Server failed to start on port {server_port}: {last_error}; log={log_path}")

    yield server_url

    proc.terminate()
    try:
        proc.wait(timeout=3)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait(timeout=2)
    log_stream.close()


# ##################################################################
# shared playwright runtime
# all browser integrations use one sync event loop per pytest process,
# including cache transport checks after session-scoped CAD pages
@pytest.fixture(scope="session")
def playwright_runtime():
    with sync_playwright() as runtime:
        yield runtime


# ##################################################################
# shared browser fixture
# fresh browser contexts have no shared HTTP cache; record the pinned 50MB OC
# dependency once, under a cross-process lock, instead of downloading per heap
@pytest.fixture(scope="session")
def shared_browser(playwright_runtime):
    root = Path(__file__).resolve().parents[1]
    common = subprocess.check_output(
        ["git", "rev-parse", "--path-format=absolute", "--git-common-dir"], cwd=root, text=True,
    ).strip()
    cache = Path(common) / "greenline" / "cdn-cache"
    source = (root / "static/opencascade.js").read_text()
    version = re.search(r'OPENCASCADE_VERSION = "([^"]+)"', source).group(1)
    base = f"https://cdn.jsdelivr.net/npm/opencascade.js@{version}/dist"
    recordings = {
        url: recorded_resource(cache, url)
        for url in (f"{base}/opencascade.full.js", f"{base}/opencascade.full.wasm")
    }
    browser = playwright_runtime.chromium.launch(
        headless=True, args=["--enable-webgl", "--use-gl=angle", "--enable-gpu"],
    )
    recorded = RecordedBrowser(browser, recordings)
    try:
        yield recorded
    finally:
        recorded.close()


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

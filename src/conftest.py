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
    log_path = tmp_path_factory.mktemp("server-logs") / "uvicorn.log"
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
        # Undrained PIPEs can block the server when a gallery generates many
        # requests. Retain genuine logs on disk without an output backpressure trap.
        stdout=log_stream,
        stderr=subprocess.STDOUT,
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
        proc.wait(timeout=3)
        log_stream.close()
        raise RuntimeError(f"Server failed to start on port {server_port}: {last_error}; log: {log_path}")

    yield server_url

    proc.terminate()
    try:
        proc.wait(timeout=3)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait(timeout=2)
    log_stream.close()


# ##################################################################
# shared browser fixture
# single chromium instance reused across all tests (WASM compile cache)
@pytest.fixture(scope="session")
def shared_browser():
    pw = sync_playwright().start()
    # Use Playwright's supported headless defaults. Forcing legacy ANGLE/GPU
    # flags significantly increased measured OC initialization on this host.
    browser = pw.chromium.launch(headless=True)
    yield browser
    browser.close()
    pw.stop()


# ##################################################################
# cad page fixture
# session-scoped, one-engine CAD API page for evaluate-only geometry tests.
# /init-test owns the real main-thread OpenCascade instance; the editor's worker
# is intentionally never started here.
@pytest.fixture(scope="session")
def cad_page(init_page):
    init_page.evaluate("""async () => {
        const cad = await import('/static/cad.js');
        const gridfinity = await import('/static/gridfinity.js');
        await import('/static/patterns.js');
        await import('/static/naming.js');
        await import('/static/joinery.js');
        cad.initCAD(window.oc);
        window.Gridfinity = gridfinity.Gridfinity;
        await new Promise((resolve, reject) => {
            const script = document.createElement('script');
            script.src = '/static/cad-tests.js';
            script.onload = resolve;
            script.onerror = () => reject(new Error('Failed to load CADTests'));
            document.head.appendChild(script);
        });
    }""")
    yield init_page


# ##################################################################
# editor page fixture
# session-scoped real editor page whose readiness is supplied by its primary
# rendering worker. Main-thread OpenCascade is deliberately not a prerequisite:
# editor rendering and recovery use the worker, while direct CAD API checks use
# the legacy cad_page fixture above.
@pytest.fixture(scope="session")
def editor_page(server, shared_browser):
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
                const filename = document.getElementById('filename-display');
                const exportButton = document.getElementById('download-3mf-btn');
                return statusText && statusText.textContent === 'Ready' &&
                    window.cadEditor && window.cadEditor._workerReady &&
                    filename && filename.textContent !== 'loading...' &&
                    exportButton && !exportButton.disabled;
            }""",
            timeout=90000,
        )
    except Exception as error:
        diagnostics = page.evaluate("""() => {
            const editor = window.cadEditor;
            const overlay = document.getElementById('error-overlay');
            const errorMessage = document.getElementById('error-message');
            const exportButton = document.getElementById('download-3mf-btn');
            return {
                status: document.getElementById('status-text')?.textContent,
                errorVisible: overlay?.classList.contains('visible'),
                errorMessage: errorMessage?.textContent,
                exportDisabled: exportButton?.disabled,
                currentFile: editor?._currentFile,
                source: editor?.editor?.getValue(),
                isRendering: editor?._isRendering,
                renderRequestId: editor?._renderRequestId,
                pendingCode: editor?._pendingCode,
                isDirty: editor?._isDirty,
                workerReady: editor?._workerReady,
                spareWorkerReady: editor?._spareWorkerReady,
                mainOCReady: editor?.isReady,
                mainOCPresent: Boolean(editor?.oc),
                globalWorkplane: Boolean(window.Workplane),
            };
        }""")
        page.close()
        raise RuntimeError(
            f"Editor worker startup failed: diagnostics={diagnostics}; requests={failures}; "
            f"console={messages[-15:]}"
        ) from error
    yield page
    page.close()


# ##################################################################
# bare page fixture
# a same-origin document without editor or OpenCascade startup. Tests which
# instantiate their own real worker use this to avoid preloading extra engines.
@pytest.fixture(scope="session")
def bare_page(server, shared_browser):
    page = shared_browser.new_page()
    page.goto(f"{server}/health")
    yield page
    page.close()


# ##################################################################
# module page fixture
# loads real CAD modules and their prototype extensions without initializing
# OpenCascade. This supports API/type-shape checks that do not create geometry.
@pytest.fixture(scope="session")
def module_page(bare_page):
    bare_page.evaluate("""async () => {
        const cad = await import('/static/cad.js');
        const gridfinity = await import('/static/gridfinity.js');
        await import('/static/patterns.js');
        await import('/static/naming.js');
        await import('/static/joinery.js');
        window.Workplane = cad.Workplane;
        window.Assembly = cad.Assembly;
        window.Profiler = cad.Profiler;
        window.Gridfinity = gridfinity.Gridfinity;
    }""")
    yield bare_page


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
            timeout=90000,
        )
    except Exception as error:
        diagnostics = page.locator("body").inner_text()
        page.close()
        raise RuntimeError(f"OpenCascade startup failed: {failures}\n{diagnostics}") from error
    yield page
    page.close()

import hashlib
import json
import threading
from concurrent.futures import ThreadPoolExecutor
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError

import pytest

from src.cdn_cache import RecordedBrowser, recorded_resource


# ##################################################################
# real immutable asset server
# serve actual files over an OS-assigned HTTP port, not a substituted client
@pytest.fixture
def asset_server(tmp_path):
    source = tmp_path / "origin"
    source.mkdir()
    body = bytes(range(256)) * 4096
    (source / "kernel.wasm").write_bytes(body)
    handler = partial(SimpleHTTPRequestHandler, directory=str(source))
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_port}", source, body
    server.shutdown()
    thread.join()
    server.server_close()


# ##################################################################
# persistent exact recording
# cache remains usable when its real upstream file no longer exists and a new
# reader starts, with original MIME and no stale transfer/compression headers
def test_recording_survives_missing_upstream(asset_server, tmp_path):
    base, source, body = asset_server
    cache = tmp_path / "recordings"
    url = f"{base}/kernel.wasm"
    content, headers = recorded_resource(cache, url)
    assert content.name == hashlib.sha256(body).hexdigest()
    assert content.read_bytes() == body
    assert {k.lower(): v for k, v in headers.items()}["content-type"] == "application/wasm"
    assert not {"content-encoding", "content-length", "transfer-encoding"} & {k.lower() for k in headers}
    (source / "kernel.wasm").unlink()
    reused, reused_headers = recorded_resource(Path(str(cache)), url)
    assert reused == content
    assert reused_headers == headers
    assert reused.read_bytes() == body


# ##################################################################
# concurrent cold readers
# independent callers publish one valid URL record and one content-addressed blob
def test_parallel_recording_is_atomic(asset_server, tmp_path):
    base, _, body = asset_server
    cache = tmp_path / "recordings"
    url = f"{base}/kernel.wasm"
    with ThreadPoolExecutor(max_workers=4) as executor:
        results = list(executor.map(lambda _: recorded_resource(cache, url), range(4)))
    assert all(result == results[0] for result in results)
    assert results[0][0].read_bytes() == body
    assert len(list(cache.glob("*.json"))) == 1
    assert len([path for path in cache.iterdir() if path.suffix not in (".json", ".lock")]) == 1


# ##################################################################
# fail closed recordings
# changed bodies and mismatched URL identities are errors, not silent refetches
@pytest.mark.parametrize("corruption", ["body", "identity"])
def test_corrupt_recording_is_rejected(asset_server, tmp_path, corruption):
    base, _, _ = asset_server
    cache = tmp_path / "recordings"
    url = f"{base}/kernel.wasm"
    content, _ = recorded_resource(cache, url)
    if corruption == "body":
        content.write_bytes(b"corrupt")
    else:
        metadata = next(cache.glob("*.json"))
        record = json.loads(metadata.read_text())
        record["url"] = "http://wrong.invalid/"
        metadata.write_text(json.dumps(record))
    with pytest.raises(ValueError, match="CDN recording"):
        recorded_resource(cache, url)


# ##################################################################
# failed acquisition
# HTTP failures never become successful immutable recordings
def test_failed_download_does_not_publish(asset_server, tmp_path):
    base, _, _ = asset_server
    cache = tmp_path / "recordings"
    with pytest.raises(HTTPError):
        recorded_resource(cache, f"{base}/missing.wasm")
    assert not list(cache.glob("*.json"))


# ##################################################################
# actual browser replay
# Chromium receives the exact recorded file under its original URL after the
# origin file disappears, proving handler bindings and MIME survive replay

def test_browser_replays_recorded_bytes(asset_server, tmp_path, playwright_runtime):
    base, source, body = asset_server
    url = f"{base}/kernel.wasm"
    recording = recorded_resource(tmp_path / "recordings", url)
    (source / "kernel.wasm").unlink()
    browser = playwright_runtime.chromium.launch(headless=True)
    recorded = RecordedBrowser(browser, {url: recording})
    try:
        page = recorded.new_page()
        page.goto(f"{base}/")
        response = page.request.get(f"{base}/kernel.wasm")
        assert response.status == 404  # the real origin is unavailable, not replaced
        actual = page.evaluate(
            """async url => {
                const r = await fetch(url);
                return {mime: r.headers.get('content-type'), bytes: r.ok
                    ? Array.from(new Uint8Array(await r.arrayBuffer())) : null};
            }""", url,
        )
        assert actual["mime"] == "application/wasm"
        assert bytes(actual["bytes"]) == body
    finally:
        recorded.close()
    assert not recorded.thread.is_alive()
    assert recorded.server.socket.fileno() == -1


# ##################################################################
# real worker module replay
# an actual module worker imports recorded JavaScript after the real origin file
# is removed; application/octet-stream would reject this dynamic module import

def test_worker_imports_recorded_javascript(asset_server, tmp_path, playwright_runtime):
    base, source, _ = asset_server
    (source / "dependency.js").write_text("export const answer = 42;")
    (source / "worker.js").write_text(
        "import('./dependency.js').then(m => postMessage(m.answer)).catch(e => postMessage(String(e)));"
    )
    url = f"{base}/dependency.js"
    recording = recorded_resource(tmp_path / "recordings", url)
    (source / "dependency.js").unlink()
    browser = playwright_runtime.chromium.launch(headless=True)
    recorded = RecordedBrowser(browser, {url: recording})
    try:
        page = recorded.new_page()
        page.goto(f"{base}/")
        answer = page.evaluate("""() => new Promise((resolve, reject) => {
            const worker = new Worker('/worker.js', {type: 'module'});
            worker.onmessage = e => { worker.terminate(); resolve(e.data); };
            worker.onerror = e => { worker.terminate(); reject(e.message); };
        })""")
        assert answer == 42
    finally:
        recorded.close()


# ##################################################################
# real browser and worker replay
# the exact recorded WASM response is delivered to both fetch paths even after
# removal from the upstream file server, preserving status and response bytes
def test_real_browser_and_worker_read_recorded_response(asset_server, tmp_path, playwright_runtime):

    base, source, body = asset_server
    url = f"{base}/kernel.wasm"
    recording = recorded_resource(tmp_path / "recordings", url)
    (source / "kernel.wasm").unlink()
    browser = playwright_runtime.chromium.launch(headless=True)
    recorded = RecordedBrowser(browser, {url: recording})
    try:
        page = recorded.new_page()
        page.goto(base)
        with page.expect_response(url) as response:
            length = page.evaluate("async url => (await (await fetch(url)).arrayBuffer()).byteLength", url)
        assert length == len(body)
        assert response.value.status == 200
        assert response.value.body() == body
        worker = page.evaluate("""url => new Promise((resolve, reject) => {
            const script = `onmessage = async () => {
                try {
                    const r = await fetch(${JSON.stringify(url)});
                    postMessage({status: r.status, length: (await r.arrayBuffer()).byteLength});
                } catch (error) { postMessage({error: String(error)}); }
            };`;
            const worker = new Worker(URL.createObjectURL(new Blob([script], {type: 'text/javascript'})));
            worker.onerror = reject;
            worker.onmessage = event => { worker.terminate(); resolve(event.data); };
            worker.postMessage('read');
        })""", url)
        assert worker == {"status": 200, "length": len(body)}
    finally:
        recorded.close()

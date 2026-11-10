import fcntl
import hashlib
import json
import os
import threading
from functools import partial
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from tempfile import NamedTemporaryFile
from urllib.request import Request, urlopen


# ##################################################################
# atomic bytes
# readers see either a complete immutable recording or no recording
def _atomic_bytes(path: Path, body: bytes) -> None:
    with NamedTemporaryFile(dir=path.parent, delete=False) as stream:
        temporary = Path(stream.name)
        try:
            stream.write(body)
            stream.flush()
            os.fsync(stream.fileno())
            stream.close()
            temporary.replace(path)
        finally:
            temporary.unlink(missing_ok=True)


# ##################################################################
# recorded resource
# record the real response once per versioned URL across concurrent gate lanes;
# verify content on every reuse rather than accepting an empty/corrupt fixture
def recorded_resource(directory: Path, url: str) -> tuple[Path, dict[str, str]]:
    directory.mkdir(parents=True, exist_ok=True)
    key = hashlib.sha256(url.encode()).hexdigest()
    metadata = directory / f"{key}.json"
    with (directory / f"{key}.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        if metadata.exists():
            record = json.loads(metadata.read_text())
            digest = record["sha256"]
            if record["url"] != url or len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
                raise ValueError(f"Invalid CDN recording: {metadata}")
            content = directory / digest
            body = content.read_bytes()
            if not body or hashlib.sha256(body).hexdigest() != digest:
                raise ValueError(f"Corrupt CDN recording: {content}")
            return content, record["headers"]
        # No shorter network deadline than the aggregate release budget.
        # Only the two immutable, version-pinned OC URLs are used by the fixture.
        with urlopen(Request(url, headers={"Accept-Encoding": "identity"})) as response:
            if response.status != 200:
                raise ValueError(f"Cannot record CDN HTTP {response.status}: {url}")
            body = response.read()
            length = response.headers.get("Content-Length")
            if not body or (length is not None and len(body) != int(length)):
                raise ValueError(f"Incomplete CDN response: {url}")
            if response.headers.get("Content-Encoding", "identity") != "identity":
                raise ValueError(f"Unexpected encoded CDN response: {url}")
            headers = {name: value for name, value in response.headers.items() if name.lower() in (
                "content-type", "access-control-allow-origin", "cache-control", "etag",
            )}
        digest = hashlib.sha256(body).hexdigest()
        content = directory / digest
        _atomic_bytes(content, body)
        record = {"url": url, "sha256": digest, "headers": headers}
        _atomic_bytes(metadata, json.dumps(record, sort_keys=True).encode())
        return content, headers


# ##################################################################
# recorded prefix
# monaco's AMD loader discovers content-hashed chunk URLs at runtime, so the
# exact-URL recorder cannot pre-enumerate them. Record/replay every GET under a
# pinned immutable prefix instead: first lane to ask for a chunk records the
# real response under its own content hash; every later lane (and every later
# release) replays those exact bytes with zero network.
def recorded_prefix_handler(directory: Path, prefix: str, fetch_timeout_ms: int = 30000):
    """Route handler recording/replaying any GET under prefix from the CDN.

    Contention rules, learned from a deadlocked gate release: never hold the
    cross-process lock across network I/O, and never let a slow or failed CDN
    fetch stall the page. A lane that misses in cache fetches upstream with a
    bounded deadline (a miss may always re-fetch later), takes the lock only
    for the atomic metadata/content write, and any fetch failure falls back
    to passing the request straight through to the real network.
    """
    directory.mkdir(parents=True, exist_ok=True)

    def _recorded(url: str):
        key = hashlib.sha256(url.encode()).hexdigest()
        metadata = directory / f"{key}.json"
        if not metadata.exists():
            return None
        try:
            record = json.loads(metadata.read_text())
            content = directory / record["sha256"]
            body = content.read_bytes()
            if body and hashlib.sha256(body).hexdigest() == record["sha256"]:
                return record["headers"], body
        except (KeyError, ValueError, OSError):
            pass  # corrupt entry: treat as a miss and re-record below
        return None

    def _store(url: str, headers: dict, body: bytes) -> None:
        key = hashlib.sha256(url.encode()).hexdigest()
        with (directory / f"{key}.lock").open("a") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            digest = hashlib.sha256(body).hexdigest()
            _atomic_bytes(directory / digest, body)
            _atomic_bytes(directory / f"{key}.json", json.dumps(
                {"url": url, "sha256": digest, "headers": headers}, sort_keys=True,
            ).encode())

    def handler(route):
        request = route.request
        url = request.url
        if request.method != "GET":
            return route.continue_()
        hit = _recorded(url)
        if hit is not None:
            headers, body = hit
            content_type = next((v for k, v in headers.items() if k.lower() == "content-type"), None)
            return route.fulfill(status=200, headers=headers, content_type=content_type, body=body)
        try:
            upstream = route.fetch(url=url, timeout=fetch_timeout_ms)
            try:
                body = upstream.body()
            finally:
                upstream.dispose()
            if not body:
                raise ValueError(f"empty recorded-prefix response: {url}")
            headers = {name: value for name, value in upstream.headers.items() if name.lower() in (
                "content-type", "access-control-allow-origin", "cache-control", "etag",
            )}
        except (OSError, ValueError, RuntimeError):
            # a recording miss must never break the live page: pass through
            return route.continue_()
        _store(url, headers, body)
        content_type = next((v for k, v in headers.items() if k.lower() == "content-type"), None)
        route.fulfill(status=200, headers=headers, content_type=content_type, body=body)

    return handler


# ##################################################################
# driver-side replay
# fulfill from the driver's response UID, then release its large buffer promptly

def _replay_recording(route, *, local_url, headers, content_type):
    response = route.fetch(url=local_url, timeout=0)
    try:
        route.fulfill(response=response, headers=headers, content_type=content_type)
    finally:
        response.dispose()


# ##################################################################
# recorded browser
# replay only exact immutable CDN bytes; contexts, workers, kernel execution,
# WebGL and all app/API traffic remain real and independently isolated
class RecordedBrowser:
    def __init__(self, browser, recordings, prefix_handlers=()):
        self.browser = browser
        self.recordings = recordings
        self.prefix_handlers = list(prefix_handlers)
        paths = {f"/{path.name}": path for path, _ in recordings.values()}

        class AssetHandler(BaseHTTPRequestHandler):
            def do_GET(self):
                path = paths.get(self.path)
                if path is None:
                    self.send_error(404)
                    return
                self.send_response(200)
                self.send_header("Content-Length", str(path.stat().st_size))
                self.end_headers()
                with path.open("rb") as stream:
                    while chunk := stream.read(1024 * 1024):
                        self.wfile.write(chunk)

            def log_message(self, *_):
                pass

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), AssetHandler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def close(self):
        self.browser.close()
        self.server.shutdown()
        self.thread.join()
        self.server.server_close()

    def new_page(self, **options):
        page = self.browser.new_page(**options)
        for prefix, handler in self.prefix_handlers:
            # a bare string pattern matches one exact URL; extend it to the
            # whole subtree so every content-hashed chunk under the pinned
            # prefix is recorded/replayed
            glob = prefix if prefix.endswith("**") else f"{prefix}**"
            page.context.route(glob, handler)
        for url, (path, headers) in self.recordings.items():
            # Playwright guesses MIME from path even when headers contain it;
            # content-addressed filenames have no suffix, so pass MIME explicitly.
            content_type = next(value for name, value in headers.items() if name.lower() == "content-type")
            local_url = f"http://127.0.0.1:{self.server.server_port}/{path.name}"
            # Keep the 50MB body inside Playwright's driver. Passing a file/body
            # instead would base64-serialize it through Python for every heap.
            page.context.route(
                url,
                partial(_replay_recording, local_url=local_url, headers=headers, content_type=content_type),
            )
        return page



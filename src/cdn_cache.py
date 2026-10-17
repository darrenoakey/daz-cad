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
    def __init__(self, browser, recordings):
        self.browser = browser
        self.recordings = recordings
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



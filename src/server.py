import setproctitle
import asyncio
import threading
import time
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, StreamingResponse
import uvicorn
from pathlib import Path

PORT = 8765
BASE_DIR = Path(__file__).parent.parent
WATCH_DIR = BASE_DIR / "static"

# global state for hot reload
reload_event = asyncio.Event()
last_change_time = 0.0
DEBOUNCE_SECONDS = 0.5


# ##################################################################
# file watcher
# watches static directory for changes and triggers reload events
class FileWatcher:
    def __init__(self, watch_path: Path, debounce: float = 0.5):
        self.watch_path = watch_path
        self.debounce = debounce
        self.last_trigger = 0.0
        self.running = False
        self.file_times: dict[str, float] = {}
        self._init_file_times()

    def _init_file_times(self):
        for f in self.watch_path.rglob("*"):
            if f.is_file():
                self.file_times[str(f)] = f.stat().st_mtime

    def check_changes(self) -> bool:
        changed = False
        current_files = set()

        for f in self.watch_path.rglob("*"):
            if f.is_file():
                path_str = str(f)
                current_files.add(path_str)
                mtime = f.stat().st_mtime

                if path_str not in self.file_times:
                    self.file_times[path_str] = mtime
                    changed = True
                elif self.file_times[path_str] != mtime:
                    self.file_times[path_str] = mtime
                    changed = True

        # check for deleted files
        deleted = set(self.file_times.keys()) - current_files
        if deleted:
            for d in deleted:
                del self.file_times[d]
            changed = True

        return changed

    def run(self, loop: asyncio.AbstractEventLoop):
        global last_change_time
        self.running = True
        while self.running:
            if self.check_changes():
                now = time.time()
                if now - self.last_trigger > self.debounce:
                    self.last_trigger = now
                    last_change_time = now
                    loop.call_soon_threadsafe(reload_event.set)
            time.sleep(0.2)

    def stop(self):
        self.running = False


file_watcher: FileWatcher | None = None
watcher_thread: threading.Thread | None = None


# ##################################################################
# start file watcher
# initializes the file watcher in a background thread
def start_file_watcher():
    global file_watcher, watcher_thread
    loop = asyncio.get_event_loop()
    file_watcher = FileWatcher(WATCH_DIR)
    watcher_thread = threading.Thread(target=file_watcher.run, args=(loop,), daemon=True)
    watcher_thread.start()


# ##################################################################
# lifespan
# manages startup and shutdown events for the application
@asynccontextmanager
async def lifespan(_app: FastAPI):
    start_file_watcher()
    yield
    if file_watcher:
        file_watcher.stop()


app = FastAPI(title="CAD Editor", lifespan=lifespan)

# mount static files for javascript and css assets
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")


# ##################################################################
# root endpoint
# serves the main cad editor page with monaco and three.js
@app.get("/")
async def root():
    return FileResponse(BASE_DIR / "static" / "editor.html")


# ##################################################################
# init test endpoint
# serves the opencascade initialization test page
@app.get("/init-test")
async def init_test():
    return FileResponse(BASE_DIR / "static" / "index.html")


# ##################################################################
# health endpoint
# returns simple status for health checks and test fixtures
@app.get("/health")
async def health():
    return {"status": "ok"}


# ##################################################################
# hot reload sse endpoint
# streams server-sent events when files change for browser hot reload
@app.get("/hot-reload")
async def hot_reload():
    async def event_stream():
        global last_change_time
        client_time = 0.0

        while True:
            try:
                await asyncio.wait_for(reload_event.wait(), timeout=30.0)
                reload_event.clear()

                if last_change_time > client_time:
                    client_time = last_change_time
                    yield "data: reload\n\n"
            except asyncio.TimeoutError:
                # send keepalive
                yield ": keepalive\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


# ##################################################################
# main
# starts the uvicorn server with configured host and port
def main():
    setproctitle.setproctitle("cad-editor-server")
    uvicorn.run(app, host="127.0.0.1", port=PORT)


# ##################################################################
# entry point
# standard python dispatch for main
if __name__ == "__main__":
    main()

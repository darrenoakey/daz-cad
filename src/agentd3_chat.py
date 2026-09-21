import asyncio
import json
import os
import time
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

import httpx
import tomllib


# ##################################################################
# agentd3 chat client
# owns the app's ONE real agentd3 assistant conversation: created lazily on
# first chat, seeded once with the CAD docs and the correct working directory,
# then durably reused across server restarts. identity is fail-closed - a
# stored conversation that is missing, archived, or mismatched remotely is a
# hard error, never a silent replacement.
class Agentd3ChatError(Exception):
    pass


# ##################################################################
# defaults
# stable base configuration; machine-local overrides live in local/config.toml
DEFAULT_BASE_URL = "http://127.0.0.1:8620"
DEFAULT_MODEL = "agentic-high"
DEFAULT_POLICY = "yolo"
DEFAULT_PRIORITY = True
DEFAULT_TIMEOUT_SECONDS = 300.0
DEFAULT_SETTLE_TIMEOUT_SECONDS = 300.0
EVENT_POLL_WAIT_SECONDS = 25.0
SETTLE_POLL_WAIT_SECONDS = 10.0
STATE_FILE_NAME = "agentd3-chat.json"
STATE_SCHEMA_VERSION = 1
CONVERSATION_SOURCE = "daz-cad"
SETTLED_STATUSES = ("idle", "sleeping")


# ##################################################################
# load overrides
# reads optional machine-local non-secret config from local/config.toml
def load_overrides(config_path: Path) -> dict:
    if not config_path.exists():
        return {}
    with open(config_path, "rb") as config_file:
        data = tomllib.load(config_file)
    section = data.get("agentd3", {})
    if not isinstance(section, dict):
        return {}
    return section


# ##################################################################
# read state
# loads the durable conversation identity; a corrupt file is a hard error
# because guessing here could silently fork the assistant conversation
def read_state(state_path: Path) -> dict:
    if not state_path.exists():
        return {}
    try:
        raw = json.loads(state_path.read_text())
    except (json.JSONDecodeError, OSError) as err:
        raise Agentd3ChatError(
            f"agentd3 chat state file {state_path} is unreadable or corrupt ({err}); "
            f"fix or deliberately remove it before chatting again"
        ) from err
    if not isinstance(raw, dict) or raw.get("schema_version") != STATE_SCHEMA_VERSION:
        raise Agentd3ChatError(
            f"agentd3 chat state file {state_path} has an unexpected format; "
            f"fix or deliberately remove it before chatting again"
        )
    return raw


# ##################################################################
# write state
# persists the identity atomically so a crash mid-write can never truncate it
def write_state(state_path: Path, state: dict) -> None:
    state_path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = state_path.with_name(state_path.name + f".tmp-{os.getpid()}")
    temp_path.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n")
    os.replace(temp_path, state_path)


# ##################################################################
# build seed system prompt
# the complete CAD documentation is embedded ONCE at conversation creation;
# later chats never re-seed, so doc edits after creation do not leak in
def build_seed_system_prompt(base_dir: Path, library_spec: str) -> str:
    doc_paths = [
        Path("docs/library-reference.md"),
        Path("docs/user-guide.md"),
        Path("docs/perf-test-results.md"),
    ]
    doc_sections = []
    for relative in doc_paths:
        absolute = base_dir / relative
        if absolute.exists():
            doc_sections.append(f"### {relative}\n\n{absolute.read_text()}")
    docs_block = "\n\n".join(doc_sections) if doc_sections else "(no additional docs found)"

    return f"""You are the CAD assistant inside the daz-cad browser editor. You help users create and modify 3D models written in a JavaScript CAD library.

WORKING DIRECTORY
The daz-cad repository lives at {base_dir}. The daemon runs your turns from a
git worktree COPY of that repository - files inside your working directory are
a reference copy, not the live app. The user's LIVE model files are NOT in
your worktree copy (that directory is untracked and never copied): they live
at {base_dir}/local/models/*.js. Every user message names the exact absolute
path of the file to edit. Always Read and Edit THAT exact absolute path -
never a copy inside your working directory, and never a relative path.
- Example models (reference only): {base_dir}/examples/*.js
- Web app source (reference only): {base_dir}/static/*.js

EDITING RULES
1. When asked to modify a model, edit the actual .js file directly using the Write or Edit tool.
2. Read the file first to see current contents before making changes.
3. Preserve the overall structure: define shapes, combine them, assign to `result`.
4. The file must end with `result;` so the editor evaluates the final shape.
5. Make minimal, targeted changes - do not rewrite the entire file unless necessary.
6. After editing, briefly explain what you changed.
7. Never touch anything outside the named model file unless explicitly asked.

Here is the CAD library specification (the sole API reference):

{library_spec}

Here are the additional CAD docs:

{docs_block}
"""


# ##################################################################
# load library spec
# reads the cad library spec that anchors the seed prompt
def load_library_spec(spec_path: Path) -> str:
    if spec_path.exists():
        return spec_path.read_text()
    return "CAD library for creating 3D shapes using Workplane and Assembly classes."


# ##################################################################
# turn reply tracker
# pure correlation of one chat turn's event stream: learns the turn id from
# this message's user.message event, keeps the last assistant text for that
# turn, and finishes on that turn's turn.completed. scoped error events
# (auto-title, memory recall, and other daemon background work) never fail
# the turn - only unscoped turn-level errors do
class TurnReplyTracker:
    def __init__(self, message_id: str) -> None:
        self.message_id = message_id
        self.turn_id = ""
        self.reply_text = ""
        self.completed_data: dict | None = None
        self.failure: Agentd3ChatError | None = None

    # ##################################################################
    # feed
    # folds one event into the tracker state
    def feed(self, event: dict) -> None:
        event_type = event.get("type", "")
        data = event.get("data") or {}
        if event_type == "user.message" and data.get("message_id") == self.message_id:
            if not self.turn_id:
                self.turn_id = str(data.get("turn_id", ""))
        elif event_type == "message.completed" and self.turn_id and data.get("turn_id") == self.turn_id:
            self.reply_text = str(data.get("text", self.reply_text))
        elif event_type == "turn.completed" and self.turn_id and data.get("turn_id") == self.turn_id:
            self.completed_data = data
        elif event_type == "error":
            self.consume_error_event(data)

    # ##################################################################
    # consume error event
    # scoped errors belong to background daemon work (auto-title, memory
    # recall) and must not fail a turn that can still complete cleanly;
    # unscoped errors are turn-level failures, but only when they name OUR
    # turn - an unrelated turn's error (someone chatting in the daemon UI)
    # must not abort our wait, and our own turn's failure is always also
    # signalled by turn.completed stop_reason=error as the backstop
    def consume_error_event(self, data: dict) -> None:
        if data.get("scope"):
            return
        if self.turn_id and data.get("turn_id") == self.turn_id:
            detail = data.get("message") or data.get("error") or "unknown error"
            self.failure = Agentd3ChatError(f"agentd3 turn failed: {detail}")

    # ##################################################################
    # result
    # returns the finished reply or raises the turn failure
    def result(self) -> str:
        if self.failure:
            raise self.failure
        if self.completed_data is None:
            raise Agentd3ChatError("turn ended without a completion event")
        stop_reason = self.completed_data.get("stop_reason", "")
        if stop_reason == "error":
            raise Agentd3ChatError("the assistant turn failed on the agentd3 daemon (stop_reason=error)")
        if stop_reason == "interrupted":
            raise Agentd3ChatError("the assistant turn was interrupted on the agentd3 daemon")
        return self.reply_text


# ##################################################################
# agentd3 chat
# one instance per app process; concurrent callers are serialized per chat
# turn so every reply stays paired with its own question
class Agentd3Chat:
    def __init__(
        self,
        base_dir: Path,
        state_path: Path | None = None,
        config_path: Path | None = None,
        overrides: dict | None = None,
    ) -> None:
        merged = dict(load_overrides(config_path)) if config_path else {}
        if overrides:
            merged.update(overrides)
        self.base_url = str(merged.get("base_url", DEFAULT_BASE_URL)).rstrip("/")
        self.model = str(merged.get("model", DEFAULT_MODEL))
        self.policy = str(merged.get("policy", DEFAULT_POLICY))
        self.priority = bool(merged.get("priority", DEFAULT_PRIORITY))
        self.timeout_seconds = float(merged.get("timeout_seconds", DEFAULT_TIMEOUT_SECONDS))
        self.settle_timeout_seconds = float(merged.get("settle_timeout_seconds", DEFAULT_SETTLE_TIMEOUT_SECONDS))
        self.source = str(merged.get("source", CONVERSATION_SOURCE))
        self.base_dir = base_dir.resolve()
        self.state_path = state_path if state_path else base_dir / "local" / STATE_FILE_NAME
        self.create_lock = asyncio.Lock()
        # chats are serialized per process and the lock is EXPOSED to the app
        # so it can hold it across saving the model file, running the agent
        # turn, and reading the result back - without that, a second request
        # could overwrite the model file before the first turn even reads it
        self.chat_lock = asyncio.Lock()
        self.http = httpx.AsyncClient(timeout=httpx.Timeout(EVENT_POLL_WAIT_SECONDS + 10.0, connect=10.0))

    # ##################################################################
    # close
    # releases the underlying http client when the app shuts down
    async def close(self) -> None:
        await self.http.aclose()

    # ##################################################################
    # exclusive turn
    # holds the chat lock across the caller's whole turn - the app saves the
    # model file, sends the message, and reads the file back inside this
    # context so concurrent chats on the same file cannot interleave
    @asynccontextmanager
    async def exclusive_turn(self):
        async with self.chat_lock:
            yield self

    # ##################################################################
    # request json
    # one place for agentd3 http calls with agentd3-specific failure context
    async def request_json(self, method: str, path: str, body: dict | None = None) -> tuple[int, dict]:
        try:
            response = await self.http.request(method, self.base_url + path, json=body)
        except httpx.HTTPError as err:
            raise Agentd3ChatError(f"cannot reach the agentd3 daemon at {self.base_url}: {err}") from err
        try:
            payload = response.json()
        except ValueError as err:
            raise Agentd3ChatError(
                f"agentd3 daemon returned a non-JSON response for {method} {path} (HTTP {response.status_code})"
            ) from err
        return response.status_code, payload

    # ##################################################################
    # fetch conversation
    # gets the remote conversation row, mapping absence to None
    async def fetch_conversation(self, conversation_id: str) -> dict | None:
        status, payload = await self.request_json("GET", f"/v1/conversations/{conversation_id}")
        if status == 404:
            return None
        if status != 200:
            raise Agentd3ChatError(
                f"agentd3 daemon error checking conversation {conversation_id}: "
                f"HTTP {status} {payload.get('error', '')}"
            )
        return payload

    # ##################################################################
    # fetch conversation required
    # fetch plus fail-closed absence handling for a stored identity
    async def fetch_conversation_required(self, conversation_id: str) -> dict:
        conversation = await self.fetch_conversation(conversation_id)
        if conversation is None:
            raise Agentd3ChatError(
                f"stored agentd3 conversation {conversation_id} no longer exists on the daemon "
                f"(daemon datastore reset?); refusing to silently replace it - deliberately "
                f"remove {self.state_path} to start a fresh assistant"
            )
        return conversation

    # ##################################################################
    # validate conversation identity
    # fail closed: the remote conversation must exist, carry our source, and
    # be bound to our working directory - a missing or mismatched binding is
    # an identity problem we surface, never silently repair by creating a new
    # conversation. the daemon gives git-backed conversations their own
    # isolated worktree, so the binding lives in original_cwd (the directory
    # we asked for) while cwd points at that per-conversation worktree copy
    def validate_conversation(self, conversation: dict, conversation_id: str) -> None:
        if conversation.get("id") != conversation_id:
            raise Agentd3ChatError(
                f"agentd3 conversation identity mismatch: asked for {conversation_id}, "
                f"daemon returned {conversation.get('id')}"
            )
        if conversation.get("source") != self.source:
            raise Agentd3ChatError(
                f"agentd3 conversation {conversation_id} has source {conversation.get('source')!r}, "
                f"expected {self.source!r}"
            )
        remote_cwd = conversation.get("original_cwd") or conversation.get("cwd")
        if not remote_cwd:
            raise Agentd3ChatError(
                f"agentd3 conversation {conversation_id} reports no working directory binding; "
                f"refusing to use it (expected {self.base_dir})"
            )
        if Path(remote_cwd) != self.base_dir:
            raise Agentd3ChatError(
                f"agentd3 conversation {conversation_id} is bound to working directory {remote_cwd}, "
                f"expected {self.base_dir}"
            )
        if conversation.get("archived"):
            raise Agentd3ChatError(
                f"agentd3 conversation {conversation_id} is archived on the daemon; unarchive it in "
                f"the daemon UI or deliberately remove {self.state_path} to start a new assistant"
            )

    # ##################################################################
    # create conversation request
    # posts the creation request, absorbing the daemon's concurrent-create
    # race: two writers replaying the same idempotency key can both miss the
    # replay lookup and race the insert, and the loser gets a 500 duplicate
    # key error. the loser then either adopts the winner's persisted identity
    # or retries into the now-committed replay path
    async def create_conversation_request(self, request_body: dict) -> tuple[int, dict]:
        for attempt in range(3):
            status, payload = await self.request_json("POST", "/v1/conversations", request_body)
            if status in (200, 201):
                return status, payload
            duplicate_race = status == 500 and "duplicate key" in str(payload.get("error", "")).lower()
            if not duplicate_race or attempt == 2:
                raise Agentd3ChatError(
                    f"agentd3 daemon refused conversation creation: HTTP {status} {payload.get('error', '')}"
                )
            raced = read_state(self.state_path)
            if raced.get("conversation_id"):
                conversation = await self.fetch_conversation_required(raced["conversation_id"])
                self.validate_conversation(conversation, raced["conversation_id"])
                return 200, {"conversation_id": raced["conversation_id"], "replayed": True}
            await asyncio.sleep(0.5 * (attempt + 1))
        raise Agentd3ChatError("agentd3 daemon conversation creation retried out")

    # ##################################################################
    # create conversation
    # posts the creation request seeded with the system prompt and cwd; the
    # idempotency key written to state first makes crash-retries replay the
    # same conversation instead of forking a second one
    async def create_conversation(self, state: dict) -> str:
        state.setdefault("idempotency_key", f"{self.source}-{uuid.uuid4().hex}")
        state["schema_version"] = STATE_SCHEMA_VERSION
        state["source"] = self.source
        state["cwd"] = str(self.base_dir)
        write_state(self.state_path, state)

        system_prompt = build_seed_system_prompt(
            self.base_dir, load_library_spec(self.base_dir / "static" / "cad-library-spec.md")
        )
        request_body = {
            "model": self.model,
            "cwd": str(self.base_dir),
            "source": self.source,
            "policy": self.policy,
            "priority": self.priority,
            "title": "daz-cad CAD assistant",
            "system_prompt": system_prompt,
            "idempotency_key": state["idempotency_key"],
            "origin": {
                "kind": "user_interactive",
                "actor": "daz-cad",
                "ref": "daz-cad:chat",
                "detail": "in-editor CAD assistant chat",
            },
        }
        payload = (await self.create_conversation_request(request_body))[1]
        conversation_id = payload.get("conversation_id", "")
        if not conversation_id:
            raise Agentd3ChatError("agentd3 daemon returned an empty conversation_id on creation")

        conversation = await self.fetch_conversation_required(conversation_id)
        self.validate_conversation(conversation, conversation_id)

        state["conversation_id"] = conversation_id
        state["created_at"] = conversation.get("created_at", "")
        write_state(self.state_path, state)
        return conversation_id

    # ##################################################################
    # get or create conversation
    # returns the one persistent conversation id; serialized so concurrent
    # first chats cannot race two conversations into existence
    async def get_or_create_conversation(self) -> str:
        async with self.create_lock:
            state = read_state(self.state_path)
            conversation_id = state.get("conversation_id", "")
            if conversation_id:
                conversation = await self.fetch_conversation_required(conversation_id)
                self.validate_conversation(conversation, conversation_id)
                return conversation_id
            return await self.create_conversation(state)

    # ##################################################################
    # settle outstanding turn
    # a previous chat that timed out on our side may have left a turn running
    # or queued on the daemon; posting a new message onto that would steer or
    # stack behind a stale turn, so cancel any queued work, interrupt the
    # live turn, and wait (bounded) for the conversation to go idle before
    # the app saves new model code and sends the next question
    async def settle_outstanding_turn(self, conversation_id: str) -> None:
        conversation = await self.fetch_conversation_required(conversation_id)
        self.validate_conversation(conversation, conversation_id)
        if conversation.get("status") in SETTLED_STATUSES:
            return

        cursor = await self.latest_event_seq(conversation_id)
        # one cancel + one interrupt is all the daemon needs: repeats only
        # pile up interrupt.requested events without speeding the model call
        await self.cancel_queued_work(conversation_id)
        await self.interrupt_conversation(conversation_id)
        deadline = time.monotonic() + self.settle_timeout_seconds
        while time.monotonic() < deadline:
            # drain events while the interrupt lands; the tombstone turn for
            # the old turn and the resulting conversation.idle flow through
            # here and are irrelevant except as proof the turn finished
            _, cursor = await self.poll_events(conversation_id, cursor, wait_seconds=SETTLE_POLL_WAIT_SECONDS)
            conversation = await self.fetch_conversation_required(conversation_id)
            if conversation.get("status") in SETTLED_STATUSES:
                return
        raise Agentd3ChatError(
            f"agentd3 conversation {conversation_id} still has an unfinished turn from an earlier chat "
            f"after {self.settle_timeout_seconds:.0f}s waiting out an interrupt; the daemon may be "
            f"stuck or saturated - check it in the daemon UI before chatting again"
        )

    # ##################################################################
    # cancel queued work
    # clears messages parked behind a live or wedged turn; "no queued work"
    # is an expected answer, not an error
    async def cancel_queued_work(self, conversation_id: str) -> None:
        status, payload = await self.request_json("POST", f"/v1/conversations/{conversation_id}/cancel-queued")
        if status not in (200, 409):
            raise Agentd3ChatError(f"agentd3 daemon refused cancel-queued: HTTP {status} {payload.get('error', '')}")

    # ##################################################################
    # interrupt conversation
    # asks the live turn to stop; "not running" is an expected answer
    async def interrupt_conversation(self, conversation_id: str) -> None:
        status, payload = await self.request_json("POST", f"/v1/conversations/{conversation_id}/interrupt")
        if status not in (202, 409):
            raise Agentd3ChatError(f"agentd3 daemon refused interrupt: HTTP {status} {payload.get('error', '')}")

    # ##################################################################
    # ensure ready
    # resolves the persistent conversation and guarantees no stale turn is
    # outstanding; the app calls this INSIDE exclusive_turn() before it
    # saves the user's current model code, then sends via send_message_locked
    async def ensure_ready(self) -> str:
        conversation_id = await self.get_or_create_conversation()
        await self.settle_outstanding_turn(conversation_id)
        return conversation_id

    # ##################################################################
    # latest event seq
    # establishes the event cursor BEFORE posting so replies from earlier
    # turns can never be mistaken for this message's answer
    async def latest_event_seq(self, conversation_id: str) -> int:
        status, payload = await self.request_json("GET", f"/v1/conversations/{conversation_id}/events?tail=1")
        if status != 200:
            raise Agentd3ChatError(f"agentd3 events cursor fetch failed: HTTP {status} {payload.get('error', '')}")
        return int(payload.get("next_after", 0))

    # ##################################################################
    # post message
    # sends the user turn; the daemon appends it or queues it behind a
    # settling turn, so the turn id is learned from the user.message event
    async def post_message(self, conversation_id: str, text: str) -> dict:
        status, payload = await self.request_json(
            "POST", f"/v1/conversations/{conversation_id}/messages", {"text": text}
        )
        if status != 202:
            raise Agentd3ChatError(
                f"agentd3 daemon rejected the chat message: HTTP {status} {payload.get('error', '')}"
            )
        message_id = payload.get("message_id", "")
        if not message_id:
            raise Agentd3ChatError("agentd3 daemon accepted the message but returned no message_id")
        return payload

    # ##################################################################
    # poll events
    # long-polls one page of events after the cursor, returning them plus the
    # advanced cursor
    async def poll_events(
        self, conversation_id: str, after: int, wait_seconds: float = EVENT_POLL_WAIT_SECONDS
    ) -> tuple[list[dict], int]:
        status, payload = await self.request_json(
            "GET",
            f"/v1/conversations/{conversation_id}/events?after={after}&wait={int(wait_seconds)}",
        )
        if status != 200:
            raise Agentd3ChatError(f"agentd3 event poll failed: HTTP {status} {payload.get('error', '')}")
        events = payload.get("events", [])
        next_after = int(payload.get("next_after", after))
        return events, next_after

    # ##################################################################
    # send message
    # standalone entry point: one question, one answer, serialized against
    # every other chat on this client
    async def send_message(self, text: str) -> str:
        async with self.exclusive_turn():
            return await self.send_message_locked(text)

    # ##################################################################
    # send message locked
    # post-then-wait body of one chat turn; the caller MUST already hold the
    # chat lock (directly or via exclusive_turn) so the app can keep its
    # save-model-file / send / read-back sequence atomic
    async def send_message_locked(self, text: str, conversation_id: str | None = None) -> str:
        if conversation_id is None:
            conversation_id = await self.ensure_ready()
        cursor = await self.latest_event_seq(conversation_id)
        post = await self.post_message(conversation_id, text)
        tracker = TurnReplyTracker(post["message_id"])

        deadline = time.monotonic() + self.timeout_seconds
        while time.monotonic() < deadline:
            events, cursor = await self.poll_events(conversation_id, cursor)
            for event in events:
                tracker.feed(event)
                if tracker.failure:
                    raise tracker.failure
                if tracker.completed_data is not None:
                    return tracker.result()
        # our caller gave up, but the daemon turn keeps running unless we ask
        # it to stop; interrupt now so the NEXT chat usually finds an idle
        # conversation instead of waiting out the settle path
        await self.interrupt_conversation(conversation_id)
        raise Agentd3ChatError(
            f"timed out after {self.timeout_seconds:.0f}s waiting for the assistant reply "
            f"(conversation {conversation_id}); an interrupt was requested - retry your message"
        )

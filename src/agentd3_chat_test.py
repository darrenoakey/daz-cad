import asyncio
import json
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

import httpx
import pytest

from src.agentd3_chat import STATE_SCHEMA_VERSION, Agentd3Chat, Agentd3ChatError, TurnReplyTracker

# real daemon - every test here creates and talks to REAL agentd3 conversations
DAEMON_BASE_URL = "http://127.0.0.1:8620"
WORKTREE_ROOT = Path(__file__).parent.parent
TEST_SOURCE = "daz-cad-test"


# ##################################################################
# make chat
# builds a client bound to a fresh state file and optional overrides; tests
# pin the fast tier because every turn here is a real model call on the
# daemon, while production defaults to the heavier agentic-high assistant
def make_chat(
    state_path: Path,
    base_dir: Path = WORKTREE_ROOT,
    source: str = TEST_SOURCE,
    timeout_seconds: float = 240.0,
) -> Agentd3Chat:
    config_path = state_path.parent / "config.toml"
    config_path.write_text(
        f"[agentd3]\n"
        f'base_url = "{DAEMON_BASE_URL}"\n'
        f'source = "{source}"\n'
        f'model = "agentic-low"\n'
        f"timeout_seconds = {timeout_seconds}\n"
    )
    return Agentd3Chat(base_dir=base_dir, state_path=state_path, config_path=config_path)


# ##################################################################
# archive conversation
# closes out a test conversation so the daemon never re-prompts it
def archive_conversation(conversation_id: str) -> None:
    if not conversation_id:
        return
    with httpx.Client(timeout=15.0) as client:
        client.patch(f"{DAEMON_BASE_URL}/v1/conversations/{conversation_id}", json={"archived": True})


# ##################################################################
# conversation id of
# reads the persisted identity from a state file
def conversation_id_of(state_path: Path) -> str:
    return json.loads(state_path.read_text()).get("conversation_id", "")


# ##################################################################
# endpoint app config
# points the app's [agentd3] config at the test daemon settings around a
# lifespan-driven endpoint test, restoring whatever was there before
@asynccontextmanager
async def endpoint_app_config():
    from src import server

    config_path = server.BASE_DIR / "local" / "config.toml"
    config_existed = config_path.exists()
    prior_config = config_path.read_text() if config_existed else None
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(
        f"[agentd3]\n"
        f'base_url = "{DAEMON_BASE_URL}"\n'
        f'source = "{TEST_SOURCE}"\n'
        f'model = "agentic-low"\n'
        f"timeout_seconds = 240.0\n"
    )
    state_path = server.BASE_DIR / "local" / "agentd3-chat.json"
    prior_state = state_path.read_text() if state_path.exists() else None
    try:
        yield server, state_path
    finally:
        if prior_state is None:
            state_path.unlink(missing_ok=True)
        else:
            state_path.write_text(prior_state)
        if config_existed:
            config_path.write_text(prior_config)
        else:
            config_path.unlink(missing_ok=True)


# ##################################################################
# test lazy create, reuse, and reply correlation
# the first chat creates the conversation, the second reuses it, and each
# reply matches its own question - a zero-cursor bug would replay the first
# answer for the second message
async def test_lazy_create_reuse_and_reply_correlation(tmp_path: Path):
    state_path = tmp_path / "agentd3-chat.json"
    chat = make_chat(state_path)
    conversation_id = ""
    try:
        first_reply = await chat.send_message("Reply with exactly the word BANANA and nothing else.")
        assert "BANANA" in first_reply.upper()
        conversation_id = conversation_id_of(state_path)
        assert conversation_id.startswith("conv-")

        second_reply = await chat.send_message("Reply with exactly the word CHERRY and nothing else.")
        assert "CHERRY" in second_reply.upper()
        assert "BANANA" not in second_reply.upper()
        assert conversation_id_of(state_path) == conversation_id

        with httpx.Client(timeout=15.0) as client:
            remote = client.get(f"{DAEMON_BASE_URL}/v1/conversations/{conversation_id}").json()
        assert remote["original_cwd"] == str(WORKTREE_ROOT)
        assert remote["source"] == TEST_SOURCE
        assert remote["archived"] is False
    finally:
        await chat.close()
        archive_conversation(conversation_id)


# ##################################################################
# test reuse across restart
# a brand-new client instance with the same state file keeps the same
# conversation - persistence across app restarts
async def test_reuse_across_restart(tmp_path: Path):
    state_path = tmp_path / "agentd3-chat.json"
    conversation_id = ""
    try:
        first_client = make_chat(state_path)
        await first_client.send_message("Reply with exactly the word BANANA and nothing else.")
        await first_client.close()
        conversation_id = conversation_id_of(state_path)

        second_client = make_chat(state_path)
        try:
            reply = await second_client.send_message("Reply with exactly the word CHERRY and nothing else.")
            assert "CHERRY" in reply.upper()
        finally:
            await second_client.close()
        assert conversation_id_of(state_path) == conversation_id
    finally:
        archive_conversation(conversation_id)


# ##################################################################
# test fail closed when stored identity is absent remotely
# a stored conversation that no longer exists on the daemon must raise, never
# silently create a replacement
async def test_fail_closed_on_absent_remote_identity(tmp_path: Path):
    state_path = tmp_path / "agentd3-chat.json"
    bogus_id = "conv-0000000000000000dead"
    state_path.write_text(
        json.dumps(
            {
                "schema_version": STATE_SCHEMA_VERSION,
                "conversation_id": bogus_id,
                "idempotency_key": f"{TEST_SOURCE}-recovery-check",
                "source": TEST_SOURCE,
                "cwd": str(WORKTREE_ROOT),
            }
        )
    )
    chat = make_chat(state_path)
    try:
        with pytest.raises(Agentd3ChatError, match="no longer exists"):
            await chat.send_message("Reply with exactly the word BANANA.")
    finally:
        await chat.close()
    assert conversation_id_of(state_path) == bogus_id


# ##################################################################
# test fail closed on identity binding problems
# validate_conversation must reject a remote row (a real snapshot) whose
# working directory binding is MISSING, mismatched, or whose source is wrong;
# a missing cwd must fail closed, never pass silently
async def test_fail_closed_on_identity_binding(tmp_path: Path):
    state_path = tmp_path / "agentd3-chat.json"
    chat = make_chat(state_path)
    conversation_id = ""
    try:
        conversation_id = await chat.get_or_create_conversation()
        with httpx.Client(timeout=15.0) as client:
            snapshot = client.get(f"{DAEMON_BASE_URL}/v1/conversations/{conversation_id}").json()

        missing_cwd = dict(snapshot)
        missing_cwd.pop("original_cwd", None)
        missing_cwd.pop("cwd", None)
        with pytest.raises(Agentd3ChatError, match="no working directory binding"):
            chat.validate_conversation(missing_cwd, conversation_id)

        mismatched = dict(snapshot, original_cwd="/tmp")
        with pytest.raises(Agentd3ChatError, match="working directory"):
            chat.validate_conversation(mismatched, conversation_id)

        wrong_source = dict(snapshot, source="somebody-else")
        with pytest.raises(Agentd3ChatError, match="source"):
            chat.validate_conversation(wrong_source, conversation_id)

        archived = dict(snapshot, archived=True)
        with pytest.raises(Agentd3ChatError, match="archived"):
            chat.validate_conversation(archived, conversation_id)
    finally:
        await chat.close()
        archive_conversation(conversation_id)


# ##################################################################
# test fail closed on working directory mismatch
# a stored conversation running in a different working directory is an
# identity mismatch, not something to quietly adopt
async def test_fail_closed_on_cwd_mismatch(tmp_path: Path):
    state_path = tmp_path / "agentd3-chat.json"
    conversation_id = ""
    try:
        chat = make_chat(state_path)
        try:
            await chat.get_or_create_conversation()
        finally:
            await chat.close()
        conversation_id = conversation_id_of(state_path)
        assert conversation_id.startswith("conv-")

        other_root = tmp_path / "elsewhere"
        other_root.mkdir()
        moved_chat = make_chat(state_path, base_dir=other_root)
        try:
            with pytest.raises(Agentd3ChatError, match="working directory"):
                await moved_chat.send_message("Reply with exactly the word BANANA.")
        finally:
            await moved_chat.close()
    finally:
        archive_conversation(conversation_id)


# ##################################################################
# test concurrent create yields one conversation
# two clients racing the same fresh state file must end up with the same
# conversation - the persisted idempotency key collapses the race
async def test_concurrent_create_yields_single_conversation(tmp_path: Path):
    state_path = tmp_path / "agentd3-chat.json"
    conversation_id = ""
    try:
        first = make_chat(state_path)
        second = make_chat(state_path)
        try:
            first_id, second_id = await asyncio.gather(
                first.get_or_create_conversation(),
                second.get_or_create_conversation(),
            )
        finally:
            await first.close()
            await second.close()
        assert first_id.startswith("conv-")
        assert first_id == second_id
        conversation_id = first_id
        assert conversation_id_of(state_path) == first_id
    finally:
        archive_conversation(conversation_id)


# ##################################################################
# test concurrent sends each get their own reply
# two chats racing on one client must not steer into one shared turn and
# return the same answer twice - serialization plus turn correlation keeps
# every question paired with its own reply
async def test_concurrent_sends_get_distinct_replies(tmp_path: Path):
    state_path = tmp_path / "agentd3-chat.json"
    conversation_id = ""
    try:
        chat = make_chat(state_path)
        try:
            first_reply, second_reply = await asyncio.gather(
                chat.send_message("Reply with exactly the word BANANA and nothing else."),
                chat.send_message("Reply with exactly the word CHERRY and nothing else."),
            )
        finally:
            await chat.close()
        conversation_id = conversation_id_of(state_path)
        assert "BANANA" in first_reply.upper()
        assert "BANANA" not in second_reply.upper()
        assert "CHERRY" in second_reply.upper()
        assert "CHERRY" not in first_reply.upper()
    finally:
        archive_conversation(conversation_id)


# ##################################################################
# test scoped error events never fail a turn
# the daemon emits scoped error events for background work (auto-title,
# memory recall) while a turn is running; the tracker must ignore them and
# still deliver the turn's reply, while an unscoped error naming our turn
# fails it
def test_scoped_error_events_never_fail_a_turn():
    tracker = TurnReplyTracker("msg-1")
    tracker.feed({"type": "user.message", "data": {"message_id": "msg-1", "turn_id": "turn-1", "text": "hi"}})
    tracker.feed({"type": "error", "data": {"scope": "auto_title", "message": "titling failed"}})
    tracker.feed({"type": "error", "data": {"scope": "memory_recall", "message": "recall degraded"}})
    tracker.feed({"type": "message.completed", "data": {"turn_id": "turn-1", "role": "assistant", "text": "DONE"}})
    tracker.feed({"type": "turn.completed", "data": {"turn_id": "turn-1", "stop_reason": "end_turn"}})
    assert tracker.result() == "DONE"

    failing = TurnReplyTracker("msg-2")
    failing.feed({"type": "user.message", "data": {"message_id": "msg-2", "turn_id": "turn-2", "text": "hi"}})
    failing.feed({"type": "error", "data": {"turn_id": "turn-2", "message": "provider exploded"}})
    assert failing.failure is not None
    assert "provider exploded" in str(failing.failure)


# ##################################################################
# test tracker ignores other turns' events
# on a reused conversation the poll window can carry events belonging to a
# different turn (someone chatting in the daemon UI); those must never be
# mistaken for this message's reply
def test_tracker_ignores_other_turns_events():
    tracker = TurnReplyTracker("msg-9")
    tracker.feed({"type": "user.message", "data": {"message_id": "msg-8", "turn_id": "turn-8", "text": "other"}})
    tracker.feed({"type": "message.completed", "data": {"turn_id": "turn-8", "role": "assistant", "text": "NOT OURS"}})
    tracker.feed({"type": "turn.completed", "data": {"turn_id": "turn-8", "stop_reason": "end_turn"}})
    assert tracker.completed_data is None
    assert tracker.reply_text == ""

    tracker.feed({"type": "user.message", "data": {"message_id": "msg-9", "turn_id": "turn-9", "text": "ours"}})
    tracker.feed({"type": "message.completed", "data": {"turn_id": "turn-9", "role": "assistant", "text": "OURS"}})
    tracker.feed({"type": "turn.completed", "data": {"turn_id": "turn-9", "stop_reason": "end_turn"}})
    assert tracker.result() == "OURS"


# ##################################################################
# test crash recovery via persisted idempotency key
# a crash between persisting the key and persisting the conversation id
# recovers into the same conversation instead of forking a second one
async def test_state_key_recovery(tmp_path: Path):
    state_path = tmp_path / "agentd3-chat.json"
    state_path.write_text(
        json.dumps(
            {
                "schema_version": STATE_SCHEMA_VERSION,
                "idempotency_key": f"{TEST_SOURCE}-recovery-{uuid.uuid4().hex}",
                "source": TEST_SOURCE,
                "cwd": str(WORKTREE_ROOT),
            }
        )
    )
    conversation_id = ""
    try:
        chat = make_chat(state_path)
        try:
            conversation_id = await chat.get_or_create_conversation()
        finally:
            await chat.close()

        replay_chat = make_chat(state_path)
        replay_chat.state_path.write_text(
            json.dumps(
                {
                    "schema_version": STATE_SCHEMA_VERSION,
                    "idempotency_key": json.loads(state_path.read_text())["idempotency_key"],
                    "source": TEST_SOURCE,
                    "cwd": str(WORKTREE_ROOT),
                }
            )
        )
        try:
            replayed_id = await replay_chat.get_or_create_conversation()
        finally:
            await replay_chat.close()
        assert replayed_id == conversation_id
    finally:
        archive_conversation(conversation_id)


# ##################################################################
# test next chat settles a turn left outstanding by a timeout
# a client-side timeout leaves the daemon turn running; the next chat must
# interrupt that stale turn before proceeding, then answer its own question
async def test_next_chat_settles_outstanding_turn(tmp_path: Path):
    state_path = tmp_path / "agentd3-chat.json"
    conversation_id = ""
    try:
        hasty = make_chat(state_path, timeout_seconds=1.0)
        try:
            with pytest.raises(Agentd3ChatError, match="timed out"):
                await hasty.send_message("Reply with exactly the word BANANA and nothing else.")
        finally:
            await hasty.close()
        conversation_id = conversation_id_of(state_path)

        patient = make_chat(state_path)
        try:
            reply = await patient.send_message("Reply with exactly the word CHERRY and nothing else.")
        finally:
            await patient.close()
        assert "CHERRY" in reply.upper()
        assert conversation_id_of(state_path) == conversation_id
    finally:
        archive_conversation(conversation_id)


# ##################################################################
# test chat endpoint round trip
# drives the real fastapi chat endpoint (lifespan included) against the real
# daemon: first chat lazily creates the conversation, the reply comes back
# through the same /api/chat/message contract the editor ui uses, and the
# endpoint's own state file pins the conversation for reuse
async def test_chat_endpoint_round_trip(tmp_path: Path):
    conversation_id = ""
    async with endpoint_app_config() as (server, state_path):
        model_file = server.MODELS_DIR / "endpoint-chat-test.js"
        try:
            async with server.lifespan(server.app):
                transport = httpx.ASGITransport(app=server.app)
                async with httpx.AsyncClient(transport=transport, base_url="http://daz-cad-test") as client:
                    first = await client.post(
                        "/api/chat/message",
                        json={
                            "message": "Reply with exactly the word BANANA and nothing else. Do not modify the file.",
                            "current_file": "endpoint-chat-test.js",
                            "current_code": "const box = new Workplane().box(10, 10, 10);\nresult;",
                        },
                    )
                    assert first.status_code == 200, first.text
                    assert "BANANA" in first.json()["response"].upper()
                    assert first.json()["file_changed"] is False

                    conversation_id = conversation_id_of(state_path)
                    assert conversation_id.startswith("conv-")

                    second = await client.post(
                        "/api/chat/message",
                        json={
                            "message": "Reply with exactly the word CHERRY and nothing else. Do not modify the file.",
                            "current_file": "endpoint-chat-test.js",
                            "current_code": "const box = new Workplane().box(10, 10, 10);\nresult;",
                        },
                    )
                    assert second.status_code == 200, second.text
                    assert "CHERRY" in second.json()["response"].upper()
                    assert conversation_id_of(state_path) == conversation_id
        finally:
            model_file.unlink(missing_ok=True)
            archive_conversation(conversation_id)


# ##################################################################
# test endpoint serializes same-file chats
# two concurrent chat requests on the SAME model file must run as indivisible
# save -> agent turn -> read-back units: each agent turn must see exactly the
# code its own request saved. without the widened lock, request B's save
# lands between A's save and A's turn, so A's agent would read B's code
async def test_endpoint_serializes_same_file_chats(tmp_path: Path):
    conversation_id = ""
    async with endpoint_app_config() as (server, state_path):
        model_file = server.MODELS_DIR / "endpoint-serialization-test.js"
        base_code = "const box = new Workplane().box(10, 10, 10);\nresult;"
        version_one = f"// version-one marker alpha\n{base_code}"
        version_two = f"// version-two marker beta\n{base_code}"
        question = (
            "Read the model file named in this message and reply with ONLY the exact text of its first line "
            "comment - do not modify the file in any way."
        )
        try:
            async with server.lifespan(server.app):
                transport = httpx.ASGITransport(app=server.app)
                async with httpx.AsyncClient(transport=transport, base_url="http://daz-cad-test") as client:
                    first, second = await asyncio.gather(
                        client.post(
                            "/api/chat/message",
                            json={
                                "message": f"The file is {model_file}. {question}",
                                "current_file": model_file.name,
                                "current_code": version_one,
                            },
                        ),
                        client.post(
                            "/api/chat/message",
                            json={
                                "message": f"The file is {model_file}. {question}",
                                "current_file": model_file.name,
                                "current_code": version_two,
                            },
                        ),
                    )
                    conversation_id = conversation_id_of(state_path)
                    assert first.status_code == 200, first.text
                    assert second.status_code == 200, second.text
                    first_reply = first.json()["response"]
                    second_reply = second.json()["response"]
                    # each turn must have read exactly its own request's code
                    assert "version-one" in first_reply, first_reply
                    assert "version-two" not in first_reply, first_reply
                    assert "version-two" in second_reply, second_reply
                    # neither agent edited the file
                    assert first.json()["file_changed"] is False
                    assert second.json()["file_changed"] is False
                    assert model_file.read_text() == version_two
        finally:
            model_file.unlink(missing_ok=True)
            archive_conversation(conversation_id)

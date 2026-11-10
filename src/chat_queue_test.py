import json
import time
import uuid

import httpx
import pytest

# Records the stage line the editor shows while a turn runs, without its
# elapsed-seconds suffix, so the test can assert which stages a real turn passed.
STAGE_RECORDER_JS = """() => {
    window.__chatStages = [];
    new MutationObserver(() => {
        const text = document.querySelector('#chat-typing-indicator .chat-typing-text')?.textContent;
        if (!text) return;
        const stage = text.replace(/ \\(\\d+s\\)$/, '');
        if (window.__chatStages[window.__chatStages.length - 1] !== stage) window.__chatStages.push(stage);
    }).observe(document.getElementById('chat-messages'), { subtree: true, childList: true, characterData: true });
}"""


# ##################################################################
# chat page
# one editor page for the module, on the server that talks to the test daemon;
# read-only questions keep the scenario from depending on render timing
@pytest.fixture(scope="module")
def chat_page(server, shared_browser):
    page = shared_browser.new_page()
    page.add_init_script("window.DAZ_CAD_TEST_DISABLE_SPARE = true")
    page.add_init_script("window.DAZ_CAD_TEST_DISABLE_INITIAL_RENDER = true")
    page.set_default_timeout(120000)
    page.goto(f"{server}/", wait_until="domcontentloaded")
    page.wait_for_function("() => window.cadEditor !== undefined", timeout=90000)
    page.wait_for_function(
        """() => document.getElementById('status-text')?.textContent === 'Ready' &&
            window.cadEditor?._currentFile""",
        timeout=480000,
    )
    yield page
    page.unroute_all(behavior="ignoreErrors")
    page.close()


# ##################################################################
# send
# types one chat message and presses Enter, exactly as a user would
def _send(page, text):
    page.locator("#chat-input").fill(text)
    page.locator("#chat-input").press("Enter")


# ##################################################################
# test queued messages send as one concatenated message
# messages typed while a turn runs must not be posted; they wait in the queue,
# stay usable (the input is never disabled), and go out together as one message
# after the turn finishes, in the order they were typed
def test_messages_queued_during_a_turn_send_as_one_message(chat_page):
    page = chat_page
    posted: list[dict] = []

    def on_request(request):
        if request.method == "POST" and request.url.endswith("/api/chat/message"):
            posted.append(request.post_data_json)

    page.on("request", on_request)
    try:
        page.evaluate(STAGE_RECORDER_JS)
        _send(page, "Describe this model in one short sentence.")
        page.wait_for_function("() => window.cadEditor._isProcessing === true")
        assert page.locator("#chat-input").is_enabled(), "input must stay usable while a turn runs"

        _send(page, "Then list the parameters it uses.")
        _send(page, "Keep the answer under ten words.")
        assert page.locator(".chat-message.queued").count() == 2
        assert page.locator("#chat-queue-status").is_visible()
        assert "2 messages queued" in page.locator("#chat-queue-status").inner_text()
        assert len(posted) == 1, "queued messages must not be posted while the turn runs"

        page.wait_for_function(
            "() => !window.cadEditor._isProcessing && window.cadEditor._chatQueue.length === 0",
            timeout=900000,
        )
        transcript = page.locator("#chat-messages").inner_text()
        assert len(posted) == 2, f"expected the first turn plus one batch, got {len(posted)}: {posted}"
        assert posted[0]["message"] == "Describe this model in one short sentence."
        assert posted[1]["message"] == "Then list the parameters it uses.\n\nKeep the answer under ten words.", posted[1]
        assert page.locator(".chat-message.queued").count() == 0
        assert page.locator("#chat-queue-status").is_hidden()
        assert page.locator(".chat-message.error").count() == 0, transcript
        assert page.locator(".chat-message.assistant").count() >= 2, transcript
        assert page.locator("#chat-input").is_enabled()

        # the stage line is sampled once per poll, so a short stage can be skipped;
        # what must show is that the turn reported at least one stage of its own
        stages = page.evaluate("() => window.__chatStages")
        own_stages = [s for s in stages if s not in ("Sending to the assistant", "Connecting to the assistant")]
        assert own_stages, stages
    finally:
        page.remove_listener("request", on_request)


# ##################################################################
# test failed turn shows its error and releases the chat
# a real turn is interrupted on the test daemon while the editor waits on it.
# the editor must show the failure and re-enable the input, not hang on the
# job. this is the path a stalled or failed assistant turn takes to the user
def test_failed_turn_shows_error_and_releases_chat(chat_page, agentd3_state_path):
    page = chat_page
    daemon = "http://127.0.0.1:18620"
    # the module shares one daemon conversation, which can still be running a
    # follow-up turn from an earlier scenario; the marker identifies this turn
    marker = f"FAILTURN-{uuid.uuid4().hex[:8]}"
    # a shell sleep keeps the turn running for a fixed time, so the interrupt
    # lands on a live turn; a short counting reply can finish before the test acts
    _send(page, f"Use the shell tool to run exactly `sleep 90`, wait for it to finish, then reply DONE. {marker}")
    page.wait_for_function("() => window.cadEditor._isProcessing === true")

    conversation_id = ""
    deadline = time.monotonic() + 120
    while not conversation_id and time.monotonic() < deadline:
        if agentd3_state_path.exists():
            conversation_id = json.loads(agentd3_state_path.read_text()).get("conversation_id", "")
        time.sleep(0.5)
    assert conversation_id, "the chat never recorded its conversation"
    turn_id = _await_turn_running_tool(daemon, conversation_id, marker)
    interrupted = httpx.post(f"{daemon}/v1/conversations/{conversation_id}/interrupt", timeout=10.0)
    assert interrupted.status_code == 202, interrupted.text

    page.wait_for_function("() => !window.cadEditor._isProcessing", timeout=180000)
    errors = page.locator(".chat-message.error").all_inner_texts()
    transcript = page.locator("#chat-messages").inner_text()
    assert any("could not finish" in text and "interrupted" in text for text in errors), (turn_id, transcript)
    assert page.locator("#chat-typing-indicator").count() == 0
    assert page.locator("#chat-input").is_enabled()
    assert page.locator("#chat-send-btn").is_enabled()


# ##################################################################
# daemon events
# every event of a conversation, following the cursor page by page
def _daemon_events(daemon: str, conversation_id: str) -> list[dict]:
    events: list[dict] = []
    cursor = 0
    while True:
        page = httpx.get(
            f"{daemon}/v1/conversations/{conversation_id}/events?after={cursor}&wait=0", timeout=20.0
        ).json()
        if not page["events"]:
            return events
        events.extend(page["events"])
        cursor = int(page["next_after"])


# ##################################################################
# await turn running tool
# returns the daemon turn that answers the message carrying marker, once that
# turn has a tool call open. user.message carries the turn id; turn.started does
# not carry the message id, so the marker is the only link between them
def _await_turn_running_tool(daemon: str, conversation_id: str, marker: str) -> str:
    deadline = time.monotonic() + 240
    turn_id = ""
    while time.monotonic() < deadline:
        events = _daemon_events(daemon, conversation_id)
        if not turn_id:
            for event in events:
                data = event.get("data") or {}
                if event["type"] == "user.message" and marker in str(data.get("text", "")):
                    turn_id = str(data.get("turn_id", ""))
        if turn_id and any(
            event["type"] == "tool.started" and (event.get("data") or {}).get("turn_id") == turn_id
            for event in events
        ):
            return turn_id
        time.sleep(0.5)
    raise AssertionError(f"no running tool call for marker {marker} (turn {turn_id or 'not admitted'})")

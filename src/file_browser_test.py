import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import unquote
from uuid import uuid4

import pytest
from playwright.sync_api import expect

PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = PROJECT_ROOT / "output" / "testing"
PERF_PATH = PROJECT_ROOT / "tests" / "bdd" / "perf.json"
FEATURE_NAME = "file_browser.feature"
PANEL_MIN_WIDTH = 480
SORT_OPTIONS = ["recent", "name", "name-desc"]
WRITE_METHODS = ("POST", "PUT", "PATCH", "DELETE")

CYLINDER_SOURCE = 'const result = new Workplane("XY").cylinder(8, 24);\nresult;'
INVALID_SOURCE = 'const result = new Workplane("XY").cylinder(8, 24\nresult;'

# every model created through the UI this run, reused by later read-only tests
_created_models = []

# maps each test to the Gherkin scenarios it fulfills in file_browser.feature
SCENARIO_NAMES = {
    "test_editor_header_opens_wide_scrollable_file_browser": [
        "Reach the CAD editor from the application root",
        "Open the file browser panel",
    ],
    "test_example_models_without_previews_invite_render": ["Example models without previews invite a render"],
    "test_successful_render_caches_transparent_thumbnail": [
        "Create a new model from the browser",
        "A successful render caches a transparent thumbnail",
        "Editing a model refreshes its cached thumbnail once",
    ],
    "test_sorting_by_name_reverse_and_recent": [
        "Sort by name uses natural alphabetical order",
        "Reverse name sort lists Z to A",
        "Sort by recent lists newest modified first",
    ],
    "test_sort_preference_persists_across_reload": ["Sort preference persists across reload"],
    "test_search_filters_filenames_and_updates_the_count": ["Search filters filenames and updates the count"],
    "test_panel_dismissal_via_escape_and_outside_click": [
        "Escape closes the panel and refocuses the selector",
        "Clicking outside closes the panel",
    ],
    "test_selecting_card_loads_model_and_persists_across_reload": [
        "Selecting a card loads the model and persists across reload"
    ],
    "test_failed_render_preserves_saved_preview_and_source": [
        "A failed render keeps the last saved preview and source"
    ],
    "test_revisiting_unchanged_model_reuses_cached_preview": ["Reopening an unchanged model reuses its cached preview"],
    "test_browsing_and_sorting_never_rerenders": ["Browsing and sorting never re-render models"],
}

_run_durations = {}


# ##################################################################
# browser page
# one page per module so OpenCascade compiles once and every scenario
# drives the same running editor in browser order
@pytest.fixture(scope="module")
def browser_page(server, shared_browser):
    page = shared_browser.new_page()
    diagnostics = []
    page._fb_diagnostics = diagnostics
    page.on("requestfailed", lambda request: diagnostics.append(f"{request.url}: {request.failure}"))
    page.on("pageerror", lambda error: diagnostics.append(str(error)))
    page.on("console", lambda message: diagnostics.append(message.text))
    _attach_recorders(page)
    page.goto(f"{server}/", wait_until="domcontentloaded")
    try:
        _await_editor_ready(page)
    except Exception as error:
        status = page.locator("#status-text").inner_text()
        page.close()
        raise RuntimeError(f"Browser startup status={status}; diagnostics={diagnostics[-25:]}") from error
    yield page
    page.close()


# ##################################################################
# attach recorders
# tracks every api request lifecycle plus model writes and thumbnail cache
# writes so tests can wait for quiescence and prove what never happened
def _attach_recorders(page):
    page._fb_pending = set()
    page._fb_writes = []
    page._fb_thumbnails = []

    def on_request(request):
        if "/api/" not in request.url:
            return
        page._fb_pending.add(request)
        if request.method in WRITE_METHODS:
            page._fb_writes.append(f"{request.method} {request.url}")

    def on_settled(request):
        if "/api/" in request.url:
            page._fb_pending.discard(request)

    def on_response(response):
        request = response.request
        if request.method == "PUT" and "/api/models/" in request.url and "/thumbnail" in request.url:
            filename = re.search(r"/api/models/([^/?]+)/thumbnail", request.url)
            revision = re.search(r"revision=([0-9a-f]{64})", request.url)
            page._fb_thumbnails.append(
                (unquote(filename.group(1)) if filename else "?", revision.group(1) if revision else "?")
            )

    page.on("request", on_request)
    page.on("requestfinished", on_settled)
    page.on("requestfailed", on_settled)
    page.on("response", on_response)


# ##################################################################
# record duration
# times every test so the perf report can attribute milliseconds to scenarios
@pytest.fixture(autouse=True)
def record_duration(request):
    start = time.monotonic()
    yield
    _run_durations[request.node.name] = round((time.monotonic() - start) * 1000)


# ##################################################################
# write perf
# publishes timings into tests/bdd/perf.json with a ten run history per scenario
@pytest.fixture(scope="module", autouse=True)
def write_perf(browser_page):
    yield
    scenarios = {}
    if PERF_PATH.exists():
        scenarios = json.loads(PERF_PATH.read_text(encoding="utf-8")).get("scenarios", {})
    for test_name, duration in _run_durations.items():
        for scenario in SCENARIO_NAMES[test_name]:
            key = f"{FEATURE_NAME}::{scenario}"
            entry = scenarios.get(key, {"duration_ms": duration, "history": []})
            entry["duration_ms"] = duration
            entry["history"] = (entry["history"] + [duration])[-10:]
            scenarios[key] = entry
    payload = {
        "last_run": datetime.now(timezone.utc).isoformat(),
        "total_duration_ms": sum(_run_durations.values()),
        "scenarios": scenarios,
    }
    PERF_PATH.parent.mkdir(parents=True, exist_ok=True)
    PERF_PATH.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


# ##################################################################
# await editor ready
# the editor status text flips to Ready once OpenCascade compiled the script
def _await_editor_ready(page):
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
        diagnostics = getattr(page, "_fb_diagnostics", [])
        raise RuntimeError(f"Editor status={status}; browser diagnostics={diagnostics[-35:]}") from error


# ##################################################################
# await quiet
# waits until every api request this page made has settled so a later
# assertion never attributes an earlier render's write to browsing
def _await_quiet(page, timeout_ms=30000):
    deadline = time.monotonic() + timeout_ms / 1000
    while time.monotonic() < deadline:
        if not page._fb_pending:
            return
        page.wait_for_timeout(50)
    pending = [request.url for request in page._fb_pending]
    raise AssertionError(f"api requests never settled: {pending}")


# ##################################################################
# open panel
# the selector button toggles the wide dropdown panel, so only click it
# when the panel is currently closed
def _open_panel(page):
    dropdown = page.locator("#file-dropdown")
    if not dropdown.is_visible():
        with page.expect_response(
            lambda response: response.request.method == "GET" and response.url.endswith("/api/models")
        ) as listing:
            page.locator("#file-selector-btn").click()
        assert listing.value.ok
        filenames = listing.value.json()["files"]
        expect(page.locator("#file-list .file-item")).to_have_count(len(filenames))
        for filename in _created_models:
            expect(page.locator(f"#file-list .file-item[data-filename='{filename}']")).to_be_attached()
    expect(dropdown).to_be_visible()


# ##################################################################
# create model
# creates a uniquely named model through the visible browser controls and
# waits for the editor to load and render it
def _create_model(page, filename):
    _open_panel(page)
    page.locator("#new-file-input").fill(filename)
    with page.expect_response(_thumbnail_put(filename), timeout=30000) as preview:
        page.locator("#create-file-btn").click()
        expect(page.locator("#filename-display")).to_contain_text(filename, timeout=15000)
        expect(page.locator("#file-dropdown")).not_to_be_visible()
        _await_editor_ready(page)
    assert preview.value.ok
    _created_models.append(filename)


# ##################################################################
# reload the document
# scope in-flight observations to the new document while preserving the full
# write and preview history, including requests owned by the replaced document.
def _reload_page(page):
    page._fb_pending.clear()
    page.reload(wait_until="domcontentloaded")


# ##################################################################
# type source
# replaces the whole script through the Monaco surface and waits for the
# render that follows the debounce to finish
def _type_source(page, source):
    page.locator(".monaco-editor .view-lines").click(position={"x": 20, "y": 10})
    page.keyboard.press("Meta+A")
    page.keyboard.insert_text(source)
    page.wait_for_function(
        "() => document.getElementById('status-text')?.textContent === 'Ready'",
        timeout=90000,
    )


# ##################################################################
# card names
# reads the rendered card order straight from the grid, a DOM read only
def _card_names(page):
    return page.locator("#file-list .file-item").evaluate_all("items => items.map(item => item.dataset.filename)")


# ##################################################################
# expect order
# asserts the relative listing order of the files this run created, ignoring
# every other model that may exist in the shared models root
def _expect_order(names, *expected):
    positions = {name: names.index(name) for name in expected}
    ordered = sorted(expected, key=lambda name: positions[name])
    assert ordered == list(expected), f"expected {expected} in this order, got {names}"


# ##################################################################
# thumbnail put predicate
# matches the preview cache write the editor makes after a successful render;
# filenames only contain letters, digits, dashes and underscores so the URL
# quoting used by the app is the identity for them
def _thumbnail_put(filename):
    def predicate(response):
        request = response.request
        return request.method == "PUT" and f"/api/models/{filename}/thumbnail" in request.url

    return predicate


# ##################################################################
# model save predicate
# matches a source save POST for exactly this model, not its thumbnail route
def _model_save(filename):
    def predicate(response):
        request = response.request
        return request.method == "POST" and request.url.endswith(f"/api/models/{filename}")

    return predicate


# ##################################################################
# thumbnail revisions for
# the recorded preview cache revisions written for one model
def _thumbnail_revisions(page, filename):
    return [revision for name, revision in page._fb_thumbnails if name == filename]


# ##################################################################
# writes for
# the recorded model writes touching one model this run owns
def _writes_for(page, filename):
    marker = f"/api/models/{filename}"
    return [write for write in page._fb_writes if marker in write]


# ##################################################################
# test editor header opens wide scrollable file browser
# covers reaching the editor from root and the panel exposing sort, search,
# count, a wide layout and a genuinely scrollable list
def test_editor_header_opens_wide_scrollable_file_browser(browser_page):
    page = browser_page
    expect(page.locator("#file-selector-btn")).to_be_visible()
    _open_panel(page)

    sort = page.locator("#file-sort")
    assert sort.locator("option").evaluate_all("options => options.map(option => option.value)") == SORT_OPTIONS
    expect(page.locator("#file-search")).to_be_visible()
    expect(page.locator("#file-count")).to_have_text(re.compile(r"^\d+ of \d+ models$"))

    panel_width = page.evaluate("() => document.getElementById('file-dropdown').offsetWidth")
    assert panel_width >= PANEL_MIN_WIDTH, f"file browser panel should be wide, got {panel_width}px"
    list_overflow = page.evaluate("() => getComputedStyle(document.getElementById('file-list')).overflowY")
    assert list_overflow in ("auto", "scroll"), f"file list should scroll, got overflow-y {list_overflow}"

    for _ in range(6):
        _create_model(page, f"test-fb-{uuid4().hex}.js")
    _open_panel(page)
    metrics = page.evaluate(
        """() => {
            const list = document.getElementById('file-list');
            return { scrollHeight: list.scrollHeight, clientHeight: list.clientHeight };
        }"""
    )
    assert metrics["scrollHeight"] > metrics["clientHeight"], "file list should overflow and scroll"

    page.locator("#file-list").hover()
    page.mouse.wheel(0, 300)
    page.wait_for_function("() => document.getElementById('file-list').scrollTop > 0", timeout=15000)


# ##################################################################
# test example models without previews invite render
# example models that were never rendered have no cached preview, so their
# cards carry the render invitation and no image; the startup model was
# rendered when the editor opened, so it is excluded from the assertion
def test_example_models_without_previews_invite_render(browser_page):
    page = browser_page
    _open_panel(page)
    example = page.locator("#file-list .file-item[data-filename='gridfinity-demo.js']")
    expect(example).to_be_visible()
    expect(example.locator(".file-preview-area")).to_contain_text("Render to preview")
    assert example.locator("img.file-preview").count() == 0
    stats = page.evaluate(
        """() => {
            const cards = [...document.querySelectorAll('#file-list .file-item')];
            const invited = cards.filter(item =>
                !item.querySelector('img.file-preview')
                && item.querySelector('.file-preview-area')?.textContent.includes('Render to preview'));
            return { cards: cards.length, invited: invited.length };
        }"""
    )
    assert stats["invited"] >= 5, f"seeded example models should start without cached previews: {stats}"


# ##################################################################
# test successful render caches transparent thumbnail
# creating a model loads it through the browser, a real edit from the box
# template to a cylinder renders once and caches exactly one new preview, and
# the card then shows a loaded image whose pixels genuinely carry transparency
def test_successful_render_caches_transparent_thumbnail(browser_page):
    page = browser_page
    filename = f"test-fb-{uuid4().hex}.js"
    page._fb_thumbnails.clear()
    with page.expect_response(_thumbnail_put(filename), timeout=90000) as put_info:
        _create_model(page, filename)
        first_put = put_info.value
    assert first_put.ok
    with page.expect_response(_thumbnail_put(filename), timeout=90000) as put_info:
        _type_source(page, CYLINDER_SOURCE)
        second_put = put_info.value
    assert second_put.ok

    revisions = _thumbnail_revisions(page, filename)
    assert len(revisions) == 2, f"expected the box then the cylinder preview, got {revisions}"
    assert revisions[0] != revisions[1], "editing the model must cache a new revision"

    _open_panel(page)
    image = page.locator(f"#file-list .file-item[data-filename='{filename}'] img.file-preview")
    expect(image).to_be_visible()
    handle = image.element_handle()
    page.wait_for_function("img => img.complete && img.naturalWidth > 0", arg=handle, timeout=15000)
    assert revisions[1] in image.get_attribute("src")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    page.locator("#file-dropdown").screenshot(path=str(OUTPUT_DIR / "file-browser.png"))

    pixels = page.evaluate(
        """(img) => {
            const canvas = document.createElement('canvas');
            canvas.width = img.naturalWidth;
            canvas.height = img.naturalHeight;
            const context = canvas.getContext('2d');
            context.drawImage(img, 0, 0);
            const data = context.getImageData(0, 0, canvas.width, canvas.height).data;
            let transparent = 0;
            let visible = 0;
            for (let index = 3; index < data.length; index += 4) {
                if (data[index] < 255) transparent += 1;
                if (data[index] > 0) visible += 1;
            }
            return { width: canvas.width, height: canvas.height, transparent, visible };
        }""",
        handle,
    )
    assert pixels["width"] > 0 and pixels["height"] > 0
    assert pixels["transparent"] > 0, "thumbnail should contain transparent pixels"
    assert pixels["visible"] > 0, "thumbnail should contain rendered geometry pixels"


# ##################################################################
# test sorting by name reverse and recent
# natural collation orders -2 before -10, descending exactly reverses that,
# and recency puts the model that was just re-saved first
def test_sorting_by_name_reverse_and_recent(browser_page):
    page = browser_page
    token = uuid4().hex
    first = f"test-fb-{token}-1.js"
    second = f"test-fb-{token}-2.js"
    tenth = f"test-fb-{token}-10.js"
    for filename in (first, second, tenth):
        _create_model(page, filename)

    _open_panel(page)
    sort = page.locator("#file-sort")
    sort.select_option("name")
    _expect_order(_card_names(page), first, second, tenth)
    sort.select_option("name-desc")
    _expect_order(_card_names(page), tenth, second, first)

    with page.expect_response(_model_save(first), timeout=30000) as loaded:
        page.locator(f"#file-list .file-item[data-filename='{first}']").click()
        expect(page.locator("#filename-display")).to_contain_text(first)
        _await_editor_ready(page)
    assert loaded.value.ok
    with page.expect_response(_thumbnail_put(first), timeout=30000) as edited:
        _type_source(page, CYLINDER_SOURCE + "\n// refreshed so this model is the newest")
    assert edited.value.ok

    _open_panel(page)
    sort.select_option("recent")
    order = _card_names(page)
    assert order.index(first) < order.index(second), f"{first} should be newest first, got {order}"
    assert order.index(first) < order.index(tenth), f"{first} should be newest first, got {order}"


# ##################################################################
# test sort preference persists across reload
# the chosen sort survives a full page reload through local storage
def test_sort_preference_persists_across_reload(browser_page):
    page = browser_page
    _open_panel(page)
    page.locator("#file-sort").select_option("name-desc")
    expect(page.locator("#file-sort")).to_have_value("name-desc")
    _reload_page(page)
    _await_editor_ready(page)
    _open_panel(page)
    expect(page.locator("#file-sort")).to_have_value("name-desc")
    page.locator("#file-sort").select_option("recent")
    expect(page.locator("#file-sort")).to_have_value("recent")


# ##################################################################
# test search filters filenames and updates the count
# the search field narrows the grid to matches and the live count agrees
# with the visible cards at every step
def test_search_filters_filenames_and_updates_the_count(browser_page):
    page = browser_page
    token = f"test-fb-{uuid4().hex}"
    _create_model(page, f"{token}.js")
    _open_panel(page)

    page.locator("#file-search").fill(token)
    expect(page.locator("#file-list .file-item").first).to_be_visible()
    names = _card_names(page)
    assert names and all(token in name for name in names)
    count_text = page.locator("#file-count").inner_text()
    match = re.match(r"^(\d+) of (\d+) models$", count_text)
    assert match, f"unexpected file count text: {count_text}"
    assert int(match.group(1)) == len(names)

    page.locator("#file-search").fill("")
    page.wait_for_function(
        r"""() => {
            const count = document.getElementById('file-count').textContent.match(/^(\d+) of/);
            const cards = document.querySelectorAll('#file-list .file-item').length;
            return count && Number(count[1]) === cards && cards > 1;
        }""",
        timeout=15000,
    )


# ##################################################################
# test panel dismissal via escape and outside click
# escape dismisses the panel and lands focus back on the toggle, and a click
# anywhere on the editor outside the panel dismisses it too
def test_panel_dismissal_via_escape_and_outside_click(browser_page):
    page = browser_page
    _open_panel(page)
    page.keyboard.press("Escape")
    expect(page.locator("#file-dropdown")).not_to_be_visible()
    expect(page.locator("#file-selector-btn")).to_be_focused()

    _open_panel(page)
    viewport = page.viewport_size
    page.mouse.click(viewport["width"] - 20, viewport["height"] - 20)
    expect(page.locator("#file-dropdown")).not_to_be_visible()


# ##################################################################
# test selecting card loads model and persists across reload
# clicking a card selects that model, closes the panel, and the choice
# survives a reload
def test_selecting_card_loads_model_and_persists_across_reload(browser_page):
    page = browser_page
    token = uuid4().hex
    first = f"test-fb-{token}-a.js"
    second = f"test-fb-{token}-b.js"
    _create_model(page, first)
    _create_model(page, second)

    _open_panel(page)
    page.locator(f"#file-list .file-item[data-filename='{first}']").click()
    expect(page.locator("#filename-display")).to_contain_text(first)
    expect(page.locator("#file-dropdown")).not_to_be_visible()

    _reload_page(page)
    _await_editor_ready(page)
    expect(page.locator("#filename-display")).to_contain_text(first, timeout=15000)


# ##################################################################
# test failed render preserves saved preview and source
# an invalid edit fails to render, leaves the last cached preview on the
# card, writes no new preview, and the last saved source comes back on reload
def test_failed_render_preserves_saved_preview_and_source(browser_page):
    page = browser_page
    filename = f"test-fb-{uuid4().hex}.js"
    page._fb_thumbnails.clear()
    page._fb_writes.clear()
    _create_model(page, filename)
    _await_quiet(page)
    revisions = _thumbnail_revisions(page, filename)
    assert len(revisions) == 1, f"the box render should cache one preview, got {revisions}"

    page.locator(".monaco-editor .view-lines").click(position={"x": 20, "y": 10})
    page.keyboard.press("Meta+A")
    page.keyboard.insert_text(INVALID_SOURCE)
    expect(page.locator("#status-text")).to_have_text("Error", timeout=90000)
    expect(page.locator("#error-overlay")).to_be_visible()
    _await_quiet(page)

    assert _thumbnail_revisions(page, filename) == revisions, "a failed render must not cache a new preview"
    _open_panel(page)
    image = page.locator(f"#file-list .file-item[data-filename='{filename}'] img.file-preview")
    expect(image).to_be_visible()
    page.wait_for_function("img => img.complete && img.naturalWidth > 0", arg=image.element_handle(), timeout=15000)

    _reload_page(page)
    _await_editor_ready(page)
    expect(page.locator("#filename-display")).to_contain_text(filename, timeout=15000)
    expect(page.locator(".monaco-editor .view-lines")).to_contain_text("box(20, 20, 20)", use_inner_text=True)
    expect(page.locator(".monaco-editor .view-lines")).not_to_contain_text("cylinder", use_inner_text=True)


# ##################################################################
# test revisiting unchanged model reuses cached preview
# switching between two rendered models through their cards makes no new
# preview write for the model that was only reopened, not edited
def test_revisiting_unchanged_model_reuses_cached_preview(browser_page):
    page = browser_page
    first, second = _created_models[0], _created_models[1]
    page._fb_writes.clear()
    page._fb_thumbnails.clear()
    _await_quiet(page)

    _open_panel(page)
    with page.expect_response(_model_save(second), timeout=30000) as saved:
        page.locator(f"#file-list .file-item[data-filename='{second}']").click()
        expect(page.locator("#filename-display")).to_contain_text(second)
        _await_editor_ready(page)
    assert saved.value.json()["thumbnail"]

    _open_panel(page)
    with page.expect_response(_model_save(first), timeout=30000) as saved:
        page.locator(f"#file-list .file-item[data-filename='{first}']").click()
        expect(page.locator("#filename-display")).to_contain_text(first)
        _await_editor_ready(page)
    assert saved.value.json()["thumbnail"]
    _await_quiet(page)

    assert _thumbnail_revisions(page, first) == [], "reopening an unchanged model must not cache a new preview"

    _open_panel(page)
    image = page.locator(f"#file-list .file-item[data-filename='{first}'] img.file-preview")
    expect(image).to_be_visible()
    page.wait_for_function("img => img.complete && img.naturalWidth > 0", arg=image.element_handle(), timeout=15000)


# ##################################################################
# test browsing and sorting never rerenders
# opening the panel, switching every sort and searching must not write any
# model or preview; renders are observed as real network events only
def test_browsing_and_sorting_never_rerenders(browser_page):
    page = browser_page
    _open_panel(page)
    _await_quiet(page)
    page._fb_writes.clear()

    sort = page.locator("#file-sort")
    for option in SORT_OPTIONS:
        sort.select_option(option)
        expect(page.locator("#file-list .file-item").first).to_be_visible()
    page.locator("#file-search").fill("test-fb")
    expect(page.locator("#file-list .file-item").first).to_be_visible()
    page.locator("#file-search").fill("")

    _await_quiet(page)
    assert page._fb_writes == [], f"browsing must not write models or previews: {page._fb_writes}"

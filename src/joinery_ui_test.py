import json
from pathlib import Path
from uuid import uuid4

from playwright.sync_api import expect

METHOD_IDS = [
    "snap-key",
    "butterfly-key",
    "dovetail",
    "jigsaw",
    "cantilever-snap",
    "snap-dowel",
    "cross-key",
    "scarf-wedge",
    "bayonet",
    "bridge-clip",
]


# ##################################################################
# prepare a single-solid model through the visible editor controls
# creates a uniquely owned model through the UI; cleanup removes only that
# model and never changes the shared default template.
def _create_single_solid_model(page):
    expect(page.locator("#filename-display")).to_contain_text("default.js", timeout=90000)
    filename = f"test-joinery-{uuid4().hex}.js"
    page._joinery_test_filename = filename
    page.locator("#file-selector-btn").click()
    page.locator("#new-file-input").fill(filename)
    page.locator("#create-file-btn").click()
    expect(page.locator("#filename-display")).to_contain_text(filename, timeout=15000)
    source = 'const result = new Workplane("XY").box(60, 40, 20);\nresult;'
    editor_surface = page.locator(".monaco-editor .view-lines")
    editor_surface.click(position={"x": 20, "y": 10})
    page.keyboard.press("Meta+A")
    page.keyboard.insert_text(source)
    page.wait_for_function(
        """() => document.getElementById('status-text')?.textContent === 'Ready'""",
        timeout=90000,
    )
    return source


# ##################################################################
# clean up the test-owned model after stopping browser autosave timers
# teardown is fixture housekeeping, never a substitute for a UI test action.
def _cleanup_model(page):
    filename = getattr(page, "_joinery_test_filename", None)
    output = Path(__file__).resolve().parents[1] / 'output' / 'testing'
    output.mkdir(parents=True, exist_ok=True)
    diagnostics = {
        'messages': getattr(page, '_joinery_messages', []),
        'body': page.locator('body').inner_text(),
    }
    (output / f'ui-{filename or uuid4().hex}.json').write_text(json.dumps(diagnostics, indent=2), encoding='utf-8')
    page.screenshot(path=str(output / f'ui-{filename or uuid4().hex}.png'))
    page.close()
    if filename:
        model = Path(__file__).resolve().parents[1] / "local" / "models" / filename
        model.unlink(missing_ok=True)


# ##################################################################
# open cut join panel through visible toolbar
# starts at the application root and makes the BDD panel reachable using clicks.
def _open_joinery_panel(page, server):
    page._joinery_messages = []
    page.on('console', lambda message: page._joinery_messages.append(message.text))
    page.on('pageerror', lambda error: page._joinery_messages.append(str(error)))
    page.goto(f"{server}/")
    page.wait_for_function(
        """() => document.getElementById('status-text')?.textContent === 'Ready'""",
        timeout=90000,
    )
    _create_single_solid_model(page)
    page.get_by_title("Split a Workplane and add printable joinery").click()
    panel = page.locator("#joinery-panel")
    expect(panel).to_be_visible()
    return panel


# ##################################################################
# test every joinery mechanism is reachable from root through the UI
# exercises the populated method picker, dimensional controls, axis controls,
# and real cut-plane preview without calling application APIs.
def test_cut_join_panel_exposes_all_methods_and_plane_controls(server, shared_browser):
    page = shared_browser.new_page()
    try:
        panel = _open_joinery_panel(page, server)
        method = panel.locator("#joinery-method")
        expect(method.locator("option")).to_have_count(len(METHOD_IDS))
        assert method.locator("option").evaluate_all("options => options.map(option => option.value)") == METHOD_IDS

        for method_id in METHOD_IDS:
            method.select_option(method_id)
            expect(method).to_have_value(method_id)
            assert method.locator(f"option[value='{method_id}']").inner_text().strip()

        for control, value in {
            "#joinery-size": "8",
            "#joinery-depth": "6",
            "#joinery-clearance": "0.2",
            "#joinery-count": "2",
            "#joinery-wall": "1.2",
            "#joinery-x": "0",
            "#joinery-y": "0",
            "#joinery-z": "10",
            "#joinery-nx": "1",
            "#joinery-ny": "1",
            "#joinery-nz": "1",
            "#joinery-ux": "0",
            "#joinery-uy": "0",
            "#joinery-uz": "1",
        }.items():
            page.locator(control).fill(value)
            expect(page.locator(control)).to_have_value(value)

        page.get_by_role("button", name="X plane").click()
        expect(page.locator("#joinery-nx")).to_have_value("1")
        expect(page.locator("#joinery-ny")).to_have_value("0")
        expect(page.locator("#joinery-nz")).to_have_value("0")
        page.get_by_role("button", name="Y plane").click()
        expect(page.locator("#joinery-ny")).to_have_value("1")
        expect(page.locator("#joinery-uy")).to_have_value("0")
        expect(page.locator("#joinery-uz")).to_have_value("1")
        page.get_by_role("button", name="Z plane").click()
        expect(page.locator("#joinery-diagnostics")).to_contain_text("Shift-drag")
    finally:
        _cleanup_model(page)


# ##################################################################
# test invalid UI generation preserves editable source then valid flow exports
# uses only user-facing controls: a real Monaco edit, panel inputs, Apply, and
# browser download; no model injection or backend shortcut is used.
def test_cut_join_ui_rejects_invalid_plane_preserves_source_and_exports_3mf(server, shared_browser):
    page = shared_browser.new_page(accept_downloads=True)
    try:
        _open_joinery_panel(page, server)
        editor_lines = page.locator(".monaco-editor .view-lines")
        source_before = editor_lines.inner_text()

        for control in ("#joinery-nx", "#joinery-ny", "#joinery-nz"):
            page.locator(control).fill("0")
        page.locator("#joinery-apply").click()
        expect(page.locator("#joinery-diagnostics")).to_contain_text("non-zero")
        expect(editor_lines).to_have_text(source_before, use_inner_text=True)

        page.locator("#joinery-nz").fill("1")
        page.locator("#joinery-ux").fill("0")
        page.locator("#joinery-uy").fill("0")
        page.locator("#joinery-uz").fill("1")
        page.locator("#joinery-apply").click()
        expect(page.locator("#joinery-diagnostics")).to_contain_text("must not be parallel")
        expect(editor_lines).to_have_text(source_before, use_inner_text=True)
        page.locator("#joinery-uy").fill("1")
        page.locator("#joinery-preview").select_option("print")
        page.locator("#joinery-method").select_option("dovetail")
        page.locator("#joinery-apply").click()
        expect(editor_lines).to_contain_text("splitAndJoin", timeout=90000)
        expect(page.locator("#status-text")).to_have_text("Ready", timeout=90000)
        expect(page.locator("#download-3mf-btn")).to_be_enabled(timeout=30000)

        with page.expect_download(timeout=90000) as download_info:
            page.locator("#download-3mf-btn").click()
        download = download_info.value
        assert download.suggested_filename.lower().endswith(".3mf")
        page.reload(wait_until="domcontentloaded")
        expect(page.locator("#filename-display")).to_contain_text(page._joinery_test_filename, timeout=90000)
        expect(page.locator(".monaco-editor .view-lines")).to_contain_text("splitAndJoin", timeout=90000)
        page.locator("#cut-join-btn").click()
        expect(page.locator("#joinery-method")).to_have_value("dovetail")
        expect(page.locator("#joinery-preview")).to_have_value("print")
        page.locator("#joinery-preview").select_option("exploded")
        page.locator("#joinery-apply").click()
        expect(page.locator("#joinery-panel")).not_to_be_visible(timeout=90000)
        expect(page.locator("#status-text")).to_have_text("Ready", timeout=90000)
    finally:
        _cleanup_model(page)


# Rapid real geometry edits must leave the latest model exportable. A separate
# worker lifecycle integration test deterministically exercises no-spare recovery.
def test_editor_replays_latest_model_after_worker_replacement(server, shared_browser):
    page = shared_browser.new_page()
    try:
        _open_joinery_panel(page, server)
        page.locator('#joinery-close').click()
        expect(page.locator('#download-3mf-btn')).to_be_enabled(timeout=90000)
        surface = page.locator('.monaco-editor .view-lines')
        heavy = '''let body = new Workplane('XY').box(80,60,20);
for (let i=0; i<80; i++) {
    body = body.cut(new Workplane('XY').cylinder(1,20).translate((i%10)*5-25, Math.floor(i/10)*5-20, 0));
}
const result = body;
result;'''
        for source in [heavy, heavy + '\n// Recalculate the current model']:
            surface.click(position={'x':20, 'y':10})
            page.keyboard.press('Meta+A')
            page.keyboard.insert_text(source)
            expect(page.locator('#status-text')).to_have_text('Compiling...', timeout=90000)
        final_source = 'const result = new Workplane("XY").box(27, 29, 31);\nresult;'
        surface.click(position={'x':20, 'y':10})
        page.keyboard.press('Meta+A')
        page.keyboard.insert_text(final_source)
        expect(page.locator('#download-3mf-btn')).to_be_enabled(timeout=90000)
        expect(page.locator('#status-text')).to_have_text('Ready')
        expect(surface).to_contain_text('box(27, 29, 31)', use_inner_text=True)
    finally:
        _cleanup_model(page)

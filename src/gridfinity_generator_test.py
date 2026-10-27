import json
import re
import time
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import pytest
from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import expect

ROOT = Path(__file__).resolve().parents[1]
PERF_PATH = ROOT / "tests" / "bdd" / "perf.json"
FEATURE_NAME = "gridfinity-generator.feature"
SCENARIO_NAMES = {
    "test_generator_ui_creates_segmented_model_and_one_complete_3mf": [
        "Reach the generator menu from the CAD editor",
        "Open the Gridfinity baseplate generator",
        "Plan balanced segments and reject invalid dimensions",
        "Generate balanced baseplate segments and export every part",
    ],
}
_run_durations = {}


@pytest.fixture(autouse=True)
def record_duration(request):
    started = time.monotonic()
    try:
        yield
    finally:
        if getattr(request.node, "_bdd_succeeded", False):
            _run_durations[request.node.name] = round((time.monotonic() - started) * 1000)


@pytest.fixture(scope="module", autouse=True)
def write_perf():
    yield
    if not _run_durations:
        return
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
    PERF_PATH.write_text(
        json.dumps(
            {
                "last_run": datetime.now(timezone.utc).isoformat(),
                "total_duration_ms": sum(_run_durations.values()),
                "scenarios": scenarios,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def _start_generator_model(page, server, diagnostics):
    page.goto(f"{server}/")
    try:
        page.wait_for_function(
            """() => {
                const editor = window.cadEditor;
                const status = document.getElementById('status-text')?.textContent;
                const filename = document.getElementById('filename-display')?.textContent;
                const exportButton = document.getElementById('download-3mf-btn');
                return editor?.editor && editor._currentFile === 'default.js' &&
                    filename === 'default.js' && status === 'Ready' && window.Workplane &&
                    exportButton && !exportButton.disabled;
            }""",
            timeout=240000,
        )
    except Exception as error:
        try:
            state = page.evaluate("""() => ({
                status: document.getElementById('status-text')?.textContent,
                filename: document.getElementById('filename-display')?.textContent,
                editorReady: Boolean(window.cadEditor?.editor),
                currentFile: window.cadEditor?._currentFile ?? null,
            })""")
        except PlaywrightError as state_error:
            state = f"<page unavailable: {state_error}>"
        raise AssertionError(f"CAD editor startup did not load default model: {state}; browser diagnostics={diagnostics[-30:]}") from error
    expect(page.locator("#filename-display")).to_contain_text("default.js", timeout=15000)
    # The server fixture uses a temporary model directory, so default.js is isolated to this test.
    # Keep this scenario focused on the generator menu/preview/export path, not file-browser creation.
    return "default.js"


def _cleanup_generator_model(page):
    page.close()


def test_generator_ui_creates_segmented_model_and_one_complete_3mf(server, shared_browser, request):
    page = shared_browser.new_page(accept_downloads=True)
    diagnostics = []
    page.on("console", lambda message: diagnostics.append(message.text))
    page.on("pageerror", lambda error: diagnostics.append(str(error)))
    page.on("requestfailed", lambda request: diagnostics.append(f"{request.url}: {request.failure}"))
    page.on("close", lambda: diagnostics.append("page closed"))
    try:
        _start_generator_model(page, server, diagnostics)
        expect(page.get_by_role("button", name="Generators")).to_be_visible()
        page.get_by_role("button", name="Generators").click()
        panel = page.locator("#generator-panel")
        expect(panel).to_be_visible()
        expect(panel.locator("#generator-kind")).to_have_value("segmented-gridfinity")
        assert panel.locator("#generator-kind option").all_text_contents() == ["Segmented Gridfinity baseplate"]
        page.evaluate("""async () => {
            const fields = document.createElement('div');
            fields.className = 'generator-fields';
            fields.dataset.generatorFields = 'future-gridfinity-probe';
            fields.hidden = true;
            fields.textContent = 'Future generator fields';
            document.getElementById('generator-panel').append(fields);
            const { registerGenerator } = await import('/static/generator-ui.js');
            registerGenerator({
                id: 'future-gridfinity-probe',
                label: 'Future generator probe',
                fieldsId: 'future-gridfinity-probe',
                readOptions: () => ({}),
                summarize: () => 'Future generator selection works.',
                generate: () => ({ source: '// future generator', summary: 'Future generator generated.' })
            });
        }""")
        assert panel.locator("#generator-kind option").all_text_contents() == [
            "Segmented Gridfinity baseplate", "Future generator probe"
        ]
        page.locator("#generator-kind").select_option("future-gridfinity-probe")
        expect(page.locator("#generator-summary")).to_have_text("Future generator selection works.")
        expect(page.locator('[data-generator-fields="future-gridfinity-probe"]')).to_be_visible()
        page.locator("#generator-kind").select_option("segmented-gridfinity")
        expect(page.locator('[data-generator-fields="future-gridfinity-probe"]')).to_be_hidden()
        expect(page.locator("#generator-mouse-ears")).to_be_checked()
        expect(panel.locator("#generator-snap-connectors")).to_be_checked()

        for control, value in {
            "#generator-x": "5",
            "#generator-y": "6",
            "#generator-bed-area": "200",
        }.items():
            page.locator(control).fill(value)
        expect(page.locator("#generator-summary")).to_contain_text("4 balanced segments")
        expect(page.locator("#generator-summary")).to_contain_text("3 + 2 wide × 3 + 3 deep")
        expect(page.locator("#generator-summary")).to_contain_text("8 snap connectors (5 for seams, 3 spare)")
        page.locator("#generator-x").fill("0")
        expect(page.locator("#generator-summary")).to_have_class(re.compile("error"))
        expect(page.locator("#generator-summary")).to_contain_text("must be a positive integer")

        for control, value in {
            "#generator-x": "2",
            "#generator-y": "1",
            "#generator-bed-area": "100",
        }.items():
            page.locator(control).fill(value)
        expect(page.locator("#generator-summary")).to_contain_text("2 balanced segments")

        page.get_by_role("button", name="Generate baseplate").click()
        source = page.locator(".monaco-editor .view-lines")
        expect(source).to_contain_text("Gridfinity.segmentedBaseplate", timeout=15000)
        expect(page.locator("#generator-summary")).to_contain_text("Generated 2 baseplate segments")
        try:
            page.wait_for_function(
                """() => {
                    const status = document.getElementById('status-text')?.textContent;
                    const exportButton = document.getElementById('download-3mf-btn');
                    return status === 'Error' || (status === 'Ready' && exportButton && !exportButton.disabled);
                }""",
                timeout=240000,
            )
        except PlaywrightTimeoutError as error:
            try:
                status = page.locator("#status-text").inner_text()
                message = page.locator("#error-message").inner_text()
            except PlaywrightError as state_error:
                status = f"<page unavailable: {state_error}>"
                message = ""
            raise AssertionError(
                f"Gridfinity preview did not finish: status={status}; error={message}; "
                f"browser diagnostics={diagnostics[-30:]}"
            ) from error
        status = page.locator("#status-text").inner_text()
        if status != "Ready":
            raise AssertionError(
                f"Gridfinity generation ended in {status}: {page.locator('#error-message').inner_text()}\n"
                f"Browser diagnostics: {diagnostics[-20:]}"
            )
        expect(page.locator("#viewer-container canvas")).to_be_visible()
        expect(page.locator("#download-3mf-btn")).to_be_enabled(timeout=30000)

        try:
            with page.expect_download(timeout=180000) as download_info:
                page.get_by_role("button", name=re.compile("3MF")).click()
            download = download_info.value
        except PlaywrightTimeoutError as error:
            status = page.locator("#status-text").inner_text()
            message = page.locator("#error-message").inner_text()
            raise AssertionError(
                f"3MF export produced no download: status={status}; error={message}; "
                f"browser diagnostics={diagnostics[-30:]}"
            ) from error
        assert "[Worker] Reusing the rendered CAD result for export" in diagnostics
        assert download.suggested_filename.lower().endswith(".3mf")
        archive_path = download.path()
        assert archive_path is not None
        with zipfile.ZipFile(archive_path) as archive:
            objects_model = archive.read("3D/Objects/objects.model").decode("utf-8")
            model_settings = archive.read("Metadata/model_settings.config").decode("utf-8")
        assert len(re.findall(r"<mesh>", objects_model)) == 6, "expected two plate segments, one seam snap, and three spare snaps"
        assert "Gridfinity baseplate 1x1 section 1-1" in model_settings
        assert "Gridfinity baseplate 1x1 section 2-1" in model_settings
        assert "Gridfinity snap connector 4" in model_settings
        mesh_vertices = {
            mesh_id: [
                tuple(float(value) for value in vertex)
                for vertex in re.findall(
                    r'<vertex x="([-+0-9.eE]+)" y="([-+0-9.eE]+)" z="([-+0-9.eE]+)"', vertex_xml
                )
            ]
            for mesh_id, vertex_xml in re.findall(
                r'<object id="(\d+)" type="model">\s*<mesh>\s*<vertices>(.*?)</vertices>',
                objects_model,
                re.DOTALL,
            )
        }
        plate_bounds = []
        for mesh_id, part_xml in re.findall(
            r'<part id="(\d+)" subtype="[^"]+">(.*?)</part>', model_settings, re.DOTALL
        ):
            name = re.search(r'<metadata key="name" value="([^"]+)"/>', part_xml)
            if not name or not name.group(1).startswith("Gridfinity baseplate"):
                continue
            vertices = mesh_vertices[mesh_id]
            assert vertices, f"baseplate mesh {mesh_id} has no vertices"
            plate_bounds.append(
                {
                    "name": name.group(1),
                    "min_x": min(vertex[0] for vertex in vertices),
                    "max_x": max(vertex[0] for vertex in vertices),
                    "min_y": min(vertex[1] for vertex in vertices),
                    "max_y": max(vertex[1] for vertex in vertices),
                    "min_z": min(vertex[2] for vertex in vertices),
                }
            )
        assert len(plate_bounds) == 2
        left_plate, right_plate = sorted(plate_bounds, key=lambda bounds: bounds["min_x"])
        assert left_plate["min_x"] < -43.9 and right_plate["max_x"] > 43.9, "mouse ears must protrude beyond outer plate edges"
        for bounds in plate_bounds:
            assert bounds["min_y"] < -22.9 and bounds["max_y"] > 22.9, "mouse ears must protrude beyond front and rear edges"
            assert abs(bounds["min_z"] + 2.325) < 1e-5, "mouse ears must touch the plate's bed-facing surface"
    finally:
        _cleanup_generator_model(page)
    request.node._bdd_succeeded = True

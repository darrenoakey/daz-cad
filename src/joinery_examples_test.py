import importlib.util
import json
import math
import runpy
from pathlib import Path
from uuid import uuid4

from playwright.sync_api import Error as BrowserError
from playwright.sync_api import expect

ROOT = Path(__file__).resolve().parent.parent
EXAMPLES = [
    ("joinery_01_robot_chest.js", "snap-key", 1),
    ("joinery_02_mountain_sculpture.js", "butterfly-key", 1),
    ("joinery_03_cable_comb.js", "dovetail", 0),
    ("joinery_04_arch_bridge.js", "jigsaw", 0),
    ("joinery_05_hex_lantern.js", "cantilever-snap", 0),
    ("joinery_06_rocket_pencil_pot.js", "snap-dowel", 1),
    ("joinery_07_toolbox_handle.js", "cross-key", 1),
    ("joinery_08_bridge_girder.js", "scarf-wedge", 1),
    ("joinery_09_twist_canister.js", "bayonet", 0),
    ("joinery_10_picture_frame.js", "bridge-clip", 2),
]


# Compile the real checked-in projects with OC, not hand-built substitutes;
# every object must render, retain valid components, and export all loose keys.
def test_connector_projects_render_and_export(init_page):
    assert {path.name for path in (ROOT / 'examples').glob('joinery_*.js')} == {row[0] for row in EXAMPLES}
    sources = [{"filename": name, "source": (ROOT / "examples" / name).read_text()} for name, _, _ in EXAMPLES]
    result = init_page.evaluate("""async (sources) => {
        const cad = await import('/static/cad.js');
        cad.initCAD(window.oc);
        const {Joinery} = await import('/static/joinery.js');
        const kernel = await import('/static/joinery-kernel.js');
        const {default: JSZip} = await import('https://cdn.jsdelivr.net/npm/jszip@3.10.1/+esm');
        const rows = [], failures = [];
        const box = part => kernel.bounds(oc,part._shape);
        for (const {filename,source} of sources) {
            const started = performance.now();
            try {
                const evaluate = new Function('Workplane','Assembly','Joinery', source + '\\nreturn {body,joint,result};');
                const {body,joint,result} = evaluate(cad.Workplane,cad.Assembly,Joinery);
                const components = [...joint.parts,...joint.keys];
                const meshes = result.toMesh();
                const printed = joint.toAssembly({mode:'print',gap:15});
                const bounds = printed._parts.map(box);
                const separated = bounds.every((a,i) => bounds.slice(i+1).every(b =>
                    a[3] < b[0] || b[3] < a[0] || a[4] < b[1] || b[4] < a[1]));
                const blob = await printed.to3MF();
                const zip = await JSZip.loadAsync(await blob.arrayBuffer());
                const objects = await zip.file('3D/Objects/objects.model').async('string');
                const settings = await zip.file('Metadata/model_settings.config').async('string');
                rows.push({filename,elapsedSeconds:(performance.now()-started)/1000,method:joint.method,parts:joint.parts.length,keys:joint.keys.length,
                    valid:kernel.valid(oc,body._shape) && components.every(part=>kernel.valid(oc,part._shape)),
                    bodyVolume:kernel.volume(oc,body._shape),bodyBounds:box(body),
                    meshes:meshes.length,meshData:meshes.every(mesh=>mesh.vertices.length>0 && mesh.indices.length>0),
                    printSeparated:separated,onBed:bounds.every(b=>Math.abs(b[2])<.001),
                    exportedMeshes:(objects.match(/<mesh>/g)||[]).length,
                    named:components.every(part=>settings.includes(part._meta.partName)),
                    modes:result.isAssembly && printed.isAssembly && joint.toAssembly({mode:'assembled'}).isAssembly});
            } catch (error) { failures.push({filename,error:String(error),stack:error.stack}); }
        }
        return {rows,failures};
    }""", sources)
    report = ROOT / "output" / "testing" / f"showcase-{uuid4().hex}.json"
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(json.dumps(result, indent=2))
    assert not result["failures"], json.dumps(result["failures"], indent=2)
    assert len(result["rows"]) == 10
    for row, (filename, method, key_count) in zip(result["rows"], EXAMPLES, strict=True):
        assert (row["filename"], row["method"], row["keys"]) == (filename, method, key_count), row
        assert row["parts"] == 2 and row["valid"] and row["modes"], row
        assert abs(row["bodyBounds"][2]) < 0.001, row
        assert row["meshes"] == row["exportedMeshes"] == 2 + key_count, row
        assert row["meshData"] and row["named"] and row["onBed"] and row["printSeparated"], row
    by_name = {row['filename']: row for row in result['rows']}
    assert abs(by_name['joinery_04_arch_bridge.js']['bodyVolume'] - math.pi * (50**2 - 28**2) * 24 / 2) < 0.01
    assert abs(by_name['joinery_08_bridge_girder.js']['bodyVolume'] - 160 * (50 * 8 * 2 + 20 * 16)) < 0.01
    # Different names on the same coupon do not constitute ten interesting objects.
    assert len({round(row["bodyVolume"], 2) for row in result["rows"]}) == 10
    assert len({tuple(round(value, 2) for value in row["bodyBounds"]) for row in result["rows"]}) == 10


# Read-only UI path: each seeded project is selected through the real model
# picker, rendered and offered as a real 3MF download. No model injection/API calls.
def verify_picker_projects(server, shared_browser, tmp_path, projects):
    page = shared_browser.new_page(accept_downloads=True, viewport={"width": 1400, "height": 1000}, device_scale_factor=2)
    gallery = ROOT / 'output' / 'testing' / f'gallery-{uuid4().hex}'
    gallery.mkdir(parents=True)
    messages = []
    trace = (gallery / 'events.log').open('w')

    def record(message):
        messages.append(message)
        trace.write(message + '\n')
        trace.flush()

    page.on('pageerror', lambda error: record(str(error)))
    page.on('console', lambda message: record(f'{message.type}: {message.text}'))
    try:
        page.goto(server + '/', wait_until='domcontentloaded')
        expect(page.locator('#filename-display')).not_to_have_text('loading...', timeout=90000)
        page.locator('#file-selector-btn').click()
        for filename, _, _ in EXAMPLES:
            expect(page.locator('#file-list .file-item').filter(has_text=filename)).to_have_count(1)
        page.locator('#file-selector-btn').click()
        for filename, _, _ in projects:
            record(f'PROJECT: {filename}')
            page.locator('#file-selector-btn').click()
            item = page.locator('#file-list .file-item').filter(has_text=filename)
            expect(item).to_have_count(1)
            item.click()
            expect(page.locator('#filename-display')).to_have_text(filename, timeout=30000)
            expect(page.locator('#download-3mf-btn')).to_be_enabled(timeout=90000)
            expect(page.locator('#status-text')).to_have_text('Ready')
            expect(page.locator('input.property-value[data-prop-name="VIEW"]')).to_have_value('1')
            viewer = page.locator('#viewer-container')
            viewer.hover()
            for _ in range(18):
                page.mouse.wheel(0, -100)
            viewer.screenshot(path=str(gallery / (filename + '.png')))
            with page.expect_download(timeout=90000) as pending:
                page.locator('#download-3mf-btn').click()
            download = pending.value
            assert download.suggested_filename.endswith('.3mf')
            download.save_as(tmp_path / (filename + '.3mf'))
    finally:
        diagnostics = {'messages': messages, 'url': page.url}
        (gallery / 'diagnostics.json').write_text(json.dumps(diagnostics, indent=2))
        try:
            diagnostics['body'] = page.locator('body').inner_text(timeout=2000)
        except BrowserError as error:
            diagnostics['body_error'] = str(error)
        (gallery / 'diagnostics.json').write_text(json.dumps(diagnostics, indent=2))
        page.close()
        trace.close()


# Full gallery acceptance: run every project through the UI before releasing
# the gallery and in check-full. The bounded gate covers the common picker
# primitive with contrasting hollow/flat and one-key/two-key projects.
def test_connector_projects_in_model_picker(server, shared_browser, tmp_path):
    verify_picker_projects(server, shared_browser, tmp_path, EXAMPLES)


def test_connector_catalog_and_picker_workflow(server, shared_browser, tmp_path):
    verify_picker_projects(server, shared_browser, tmp_path, [EXAMPLES[5], EXAMPLES[9]])


# The production standalone bundler must include the same ten real project
# sources; this exercises actual filesystem packaging, not a stubbed manifest.
def test_connector_projects_bundled_for_standalone(tmp_path):
    spec = importlib.util.spec_from_file_location('showcase_bundler', ROOT / 'site/src/standalone/bundler.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.bundle(ROOT, tmp_path)
    html = (tmp_path / 'editor-standalone.html').read_text()
    for filename, method, _ in EXAMPLES:
        assert filename in html
        assert method in (ROOT / 'examples' / filename).read_text()
    for filename in ('joinery.js', 'joinery-kernel.js', 'joinery-families-sliding.js', 'joinery-families-snaps.js', 'joinery-families-locks.js'):
        assert (tmp_path / 'static' / filename).is_file()


# Exercise the actual release selector: only the declared example-only surface
# can narrow coverage; every real infrastructure/core path retains regressions.
def test_showcase_change_impact_selection():
    runner = runpy.run_path(str(ROOT / 'run'))
    selection = runner['showcase_only_changes']
    browser_selection = runner['showcase_browser_changes']
    examples = [f'examples/{filename}' for filename, _, _ in EXAMPLES]
    assert selection(examples + ['docs/joinery-gallery.md', 'src/joinery_examples_test.py'])
    assert not selection([])
    assert not selection(['README.md'])
    for path in ['run', 'src/conftest.py', 'src/server.py', 'static/joinery.js', 'static/editor.js', 'greenline.toml']:
        assert (ROOT / path).is_file()
        assert not selection(examples + [path]), path
    assert browser_selection(examples + ['run', 'src/conftest.py', 'static/editor.js'])
    assert not browser_selection(['run'])
    for path in ['src/server.py', 'src/agentd3_chat.py', 'static/cad.js', 'static/joinery.js', 'greenline.toml']:
        assert not browser_selection(examples + ['run', path]), path


# Real editor lifecycle integration (separate from the UI-only picker scenario):
# reading identical model bytes must not enqueue rendering or disable exports.
def test_identical_model_reload_does_not_recompile(cad_page):
    expect(cad_page.locator('#filename-display')).not_to_have_text('loading...', timeout=90000)
    expect(cad_page.locator('#download-3mf-btn')).to_be_enabled(timeout=90000)
    result = cad_page.evaluate("""async () => {
        const editor = window.cadEditor;
        const request = editor._renderRequestId;
        const code = editor.editor.getValue();
        await Promise.all([editor._reloadCurrentFile(), editor._reloadCurrentFile()]);
        await Promise.all([editor._checkFileChanged(), editor._checkFileChanged()]);
        return {sameRequest:request === editor._renderRequestId,
            sameCode:code === editor.editor.getValue(),
            exportEnabled:!document.getElementById('download-3mf-btn').disabled,
            checkSettled:!editor._fileCheckPending};
    }""")
    assert all(result.values()), result

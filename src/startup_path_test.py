"""Editor startup must stay on the app origin, including the auto-gui proxy."""

import hashlib
import importlib.util
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STATIC = ROOT / "static"


def test_editor_entry_uses_proxy_base():
    html = (STATIC / "editor.html").read_text()
    assert "import(`${appBase}/static/editor.js${cacheBuster}`)" in html
    assert "import(`/static/editor.js${cacheBuster}`)" not in html
    assert "new Worker('/static/cad-worker.js'" not in (STATIC / "editor.js").read_text()


def test_opencascade_pin_is_the_official_beta():
    source = (STATIC / "opencascade.js").read_text()
    assert 'OPENCASCADE_VERSION = "2.0.0-beta.b5ff984"' in source
    for name in ("editor.js", "cad-worker.js", "app.js", "perf-test.html"):
        text = (STATIC / name).read_text()
        assert "opencascade.js@2.0.0-beta" not in text, name
        assert "opencascade.js" in text or "loadOpenCascade" in text or "OPENCASCADE_CDN" in text


def test_app_base_keeps_proxy_prefix_and_direct_root():
    script = """
import { appBase, appUrl } from './static/app-base.js';
const cases = [
  [appBase('/'), ''],
  [appBase('/anker_holder'), ''],
  [appBase('/proxy/daz-cad/'), '/proxy/daz-cad'],
  [appBase('/proxy/daz-cad'), '/proxy/daz-cad'],
  [appBase('/proxy/daz-cad/static/editor.js'), '/proxy/daz-cad'],
  [appUrl('/static/editor.js', '/proxy/daz-cad/'), '/proxy/daz-cad/static/editor.js'],
  [appUrl('/static/cad-worker.js', '/static/cad-worker.js'), '/static/cad-worker.js'],
  [appUrl('https://cdn.jsdelivr.net/npm/opencascade.js/dist/x.js', '/proxy/daz-cad/'), 'https://cdn.jsdelivr.net/npm/opencascade.js/dist/x.js'],
];
for (const [actual, expected] of cases) {
  if (actual !== expected) {
    console.error(JSON.stringify({ actual, expected }));
    process.exit(1);
  }
}
"""
    result = subprocess.run(
        ["node", "--input-type=module", "-e", script],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr or result.stdout


# ##################################################################
# proxy stylesheet prefixing
# execute the real inline initializer against browser link elements; an HTML
# proxy may already have rewritten the href before JavaScript starts
def test_file_browser_stylesheet_prefixing_is_idempotent(server, shared_browser):
    html = (STATIC / "editor.html").read_text()
    initializer = re.search(r"const browserCss = .*?\n        }", html, re.DOTALL)
    assert initializer is not None
    page = shared_browser.new_page()
    try:
        page.goto(server + "/health", wait_until="domcontentloaded")
        for initial in ("/static/file-browser.css?v=1", "/proxy/daz-cad/static/file-browser.css?v=1"):
            actual = page.evaluate(
                """({initializer, initial}) => {
                    document.querySelector('[data-app-style]')?.remove();
                    const link = document.createElement('link');
                    link.dataset.appStyle = 'file-browser.css';
                    link.setAttribute('href', initial);
                    document.head.append(link);
                    new Function('appBase', initializer)('/proxy/daz-cad');
                    return link.getAttribute('href');
                }""",
                {"initializer": initializer.group(), "initial": initial},
            )
            assert actual == "/proxy/daz-cad/static/file-browser.css?v=1"
    finally:
        page.close()


# ##################################################################
# file browser stylesheet version
# the checked-in URL must change with CSS bytes rather than remaining a stale literal
def test_file_browser_stylesheet_version_matches_content():
    html = (STATIC / "editor.html").read_text()
    digest = hashlib.sha256((STATIC / "file-browser.css").read_bytes()).hexdigest()[:12]
    versions = re.findall(r'href="/static/file-browser\.css\?v=([0-9a-f]+)"', html)
    assert versions == [digest]


# ##################################################################
# uncommitted change selection
# exercise real git state so local checks cover edits before the first commit
def test_gate_detects_uncommitted_and_untracked_candidate_paths(tmp_path):
    for arguments in (
        ["init", "-b", "master"],
        ["config", "user.name", "CAD integration"],
        ["config", "user.email", "cad@example.test"],
    ):
        subprocess.run(["git", *arguments], cwd=tmp_path, check=True, capture_output=True)
    (tmp_path / "tracked.js").write_text("initial")
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "Initial source"], cwd=tmp_path, check=True, capture_output=True)
    (tmp_path / "tracked.js").write_text("edited")
    (tmp_path / "untracked.js").write_text("new")
    script = "import json, runpy, sys; ns=runpy.run_path(sys.argv[1]); print(json.dumps(ns['_candidate_paths']()))"
    result = subprocess.run(
        [sys.executable, "-c", script, str(ROOT / "run")], cwd=tmp_path,
        capture_output=True, text=True, check=True,
    )
    assert json.loads(result.stdout) == ["tracked.js", "untracked.js"]


# ##################################################################
# standalone asset packaging
# exercise the real bundler rather than a manifest-only assertion
def test_standalone_bundle_includes_file_browser_assets(tmp_path):
    spec = importlib.util.spec_from_file_location("cad_standalone_bundler", ROOT / "site/src/standalone/bundler.py")
    assert spec is not None and spec.loader is not None
    bundler = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(bundler)
    assert "file-browser.css" in bundler.CSS_FILES
    assert "app-base.js" in bundler._collect_js_files(STATIC)
    bundler.bundle(ROOT, tmp_path)
    build_hash = bundler._compute_build_hash(STATIC)
    html = (tmp_path / "editor-standalone.html").read_text()
    assert f'href="./static/file-browser.css?v={build_hash}"' in html
    assert 'href="/static/file-browser.css' not in html
    assert (tmp_path / "static/file-browser.css").read_bytes() == (STATIC / "file-browser.css").read_bytes()
    assert (tmp_path / "static/app-base.js").is_file()
    editor = (tmp_path / "static/editor.js").read_text()
    assert f"from './app-base.js?v={build_hash}'" in editor

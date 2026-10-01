"""Editor startup must stay on the app origin, including the auto-gui proxy."""

import subprocess
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

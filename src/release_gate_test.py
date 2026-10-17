import runpy
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
GATE = runpy.run_path(str(ROOT / "run"))


# ##################################################################
# browser impact boundary
# browser consumers cannot alter upstream geometry; keep every browser/preview
# scenario and worker/export regression instead of broad geometry integration
@pytest.mark.parametrize("path", [
    "static/editor.js", "static/editor.html", "static/viewer.js", "static/file-browser.css",
    "src/model_preview.py", "src/file_browser_test.py", "src/preview_race_test.py",
    "site/src/standalone/bundler.py",
])
def test_browser_impact_preserves_preview_and_worker_coverage(path):
    selected = GATE["_selected_gate_tests"]([path])
    assert "src/file_browser_test.py" in selected
    assert "src/preview_race_test.py" in selected
    assert "src/model_preview_test.py" in selected
    assert "src/server_test.py::test_worker_direct_opencascade_preview_and_exports" in selected
    assert not set(GATE["GEOMETRY_TESTS"]) & set(selected)


# ##################################################################
# transitive geometry dependencies
# shared entry points, kernel dependencies and unknown ownership stay conservative
@pytest.mark.parametrize("path", [
    "static/cad.js", "static/cad-worker.js", "static/opencascade.js", "static/app-base.js", "static/joinery.js",
    "static/joinery-kernel.js", "static/joinery-families-snaps.js", "src/server.py",
    "src/conftest.py", "pyproject.toml", "run", "src/new_geometry.py",
])
def test_shared_and_geometry_changes_retain_geometry_coverage(path):
    selected = GATE["_selected_gate_tests"]([path, "static/editor.js"])
    assert set(GATE["GEOMETRY_TESTS"]) <= set(selected)
    assert "src/file_browser_test.py" in selected


# ##################################################################
# lane partition
# the original stateful modules stay intact, selected tests occur exactly once,
# and the browser bottleneck no longer serializes unrelated CAD/preview fixtures
@pytest.mark.parametrize("paths", [[], ["run"], ["src/agentd3_chat.py"], ["static/editor.js", "src/server.py"]])
def test_gate_lanes_preserve_every_selected_target_once(paths):
    selected = GATE["_selected_gate_tests"](paths)
    lanes = GATE["_gate_lanes"](selected)
    flattened = [target for targets in lanes.values() for target in targets]
    assert sorted(flattened) == sorted(selected)
    assert len(flattened) == len(set(flattened))
    for name, targets in lanes.items():
        if name == "chat":
            assert all(target.startswith("src/agentd3_chat_test.py") for target in targets)
        elif name == "browser":
            assert targets == ["src/file_browser_test.py"]
        else:
            assert name == "cad"
            assert "src/file_browser_test.py" not in targets
    if "src/file_browser_test.py" in selected:
        assert "src/preview_race_test.py" in lanes["cad"]
        assert "browser" in lanes


# ##################################################################
# runner-change coverage
# changes to scheduling must still exercise all eight targets from the measured
# slow release, rather than appearing fast by omitting its expensive validations
def test_runner_change_keeps_the_measured_release_coverage():
    selected = GATE["_selected_gate_tests"](["run", "src/release_gate_test.py"])
    previous = {
        "src/startup_path_test.py", "src/model_preview_test.py", "src/file_browser_test.py",
        "src/preview_race_test.py", "src/server_test.py::test_chat_job_unknown",
        "src/server_test.py::test_worker_direct_opencascade_preview_and_exports",
        "src/joinery_kernel_test.py",
        "src/joinery_test.py::test_all_joinery_methods_create_valid_complementary_solids",
    }
    assert set(selected) == previous | {"src/release_gate_test.py", "src/cdn_cache_test.py"}

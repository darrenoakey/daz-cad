"""Standalone editor bundler - packages editor for serverless use."""

import json
import re
import shutil
from pathlib import Path


# JavaScript files to copy to the standalone site
JS_FILES = [
    "cad.js",
    "editor.js",
    "viewer.js",
    "patterns.js",
    "gridfinity.js",
    "cad-worker.js",
    "opentype.module.js",
    "threemf.js",
]

FONT_FILES = [
    "fonts/Overpass-Bold.ttf",
]

TEMPLATE_FILES = [
    "template.3mf",
]


def _load_examples(examples_dir: Path) -> dict[str, str]:
    """Load all example .js files from the examples directory."""
    examples = {}
    for path in sorted(examples_dir.glob("*.js")):
        examples[path.name] = path.read_text()
    return examples


def _build_import_map() -> str:
    """Build the import map for standalone mode using relative paths."""
    return json.dumps({
        "imports": {
            "three": "https://cdn.jsdelivr.net/npm/three@0.160.0/build/three.module.js",
            "three/addons/": "https://cdn.jsdelivr.net/npm/three@0.160.0/examples/jsm/",
            "jszip": "https://cdn.jsdelivr.net/npm/jszip@3.10.1/dist/jszip.min.js",
            "/static/cad.js": "./static/cad.js",
            "/static/viewer.js": "./static/viewer.js",
            "/static/gridfinity.js": "./static/gridfinity.js",
            "/static/patterns.js": "./static/patterns.js",
            "/static/threemf.js": "./static/threemf.js",
            "/static/opentype.module.js": "./static/opentype.module.js",
        }
    }, indent=8)


def _build_editor_html(source_html: str, examples: dict[str, str]) -> str:
    """Transform editor.html for standalone use."""
    html = source_html

    # Remove the dynamic import map script and replace with static one
    html = re.sub(
        r'<script>\s*const cacheBuster.*?</script>',
        f"""<script>
        window.DAZ_CAD_STANDALONE = true;
        window.DAZ_CAD_EXAMPLES = {json.dumps(examples, indent=8)};
    </script>
    <script type="importmap">
    {_build_import_map()}
    </script>""",
        html,
        count=1,
        flags=re.DOTALL,
    )

    # Remove the hot reload script
    html = re.sub(
        r'<!-- Hot reload client -->.*?</script>',
        '',
        html,
        flags=re.DOTALL,
    )

    # Remove the cache-busted module loading and replace with direct import
    html = re.sub(
        r'<!-- Cache-busted module loading -->.*?</script>',
        """<script type="module">
        import('./static/editor.js');
    </script>""",
        html,
        count=1,
        flags=re.DOTALL,
    )

    # Remove the cad-tests.js script
    html = re.sub(
        r'<script>\s*// Cache-busted non-module script.*?</script>',
        '',
        html,
        flags=re.DOTALL,
    )

    # Hide the chat pane
    html = html.replace(
        '<div class="chat-pane">',
        '<div class="chat-pane" style="display: none;">',
    )

    # Add a subtle "Back to site" link
    html = html.replace(
        '<div class="status-indicator">',
        '<a href="/" style="color: #8b949e; font-size: 11px; text-decoration: none; margin-right: 12px; opacity: 0.7;" '
        'onmouseover="this.style.opacity=1" onmouseout="this.style.opacity=0.7">'
        'dazcad.insidemind.com.au</a>'
        '<div class="status-indicator">',
    )

    # Update title
    html = html.replace(
        '<title>CAD Editor - Live Preview</title>',
        '<title>daz-cad Editor</title>',
    )

    return html


def bundle(project_root: Path, output_dir: Path) -> None:
    """Bundle the standalone editor into the output directory.

    Args:
        project_root: Path to daz-cad root directory.
        output_dir: Path to output directory (e.g., site/local/web/).
    """
    static_src = project_root / "static"
    examples_dir = project_root / "examples"
    static_dst = output_dir / "static"
    static_dst.mkdir(parents=True, exist_ok=True)

    # Copy JS files
    for filename in JS_FILES:
        src = static_src / filename
        if src.exists():
            shutil.copy2(src, static_dst / filename)

    # Copy font files
    for font_path in FONT_FILES:
        src = static_src / font_path
        if src.exists():
            dst = static_dst / font_path
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)

    # Copy template files
    for template_path in TEMPLATE_FILES:
        src = static_src / template_path
        if src.exists():
            shutil.copy2(src, static_dst / template_path)

    # Load examples
    examples = _load_examples(examples_dir)

    # Build standalone HTML
    editor_html = (static_src / "editor.html").read_text()
    standalone_html = _build_editor_html(editor_html, examples)

    (output_dir / "editor-standalone.html").write_text(standalone_html)

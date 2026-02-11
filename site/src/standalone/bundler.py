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
    # Use lambda replacement to prevent re.sub from interpreting backslash
    # escapes in the JSON (e.g. \\n becoming literal newlines)
    examples_json = json.dumps(examples, indent=8)
    import_map = _build_import_map()
    html = re.sub(
        r'<script>\s*const cacheBuster.*?</script>',
        lambda _: f"""<script>
        window.DAZ_CAD_STANDALONE = true;
        window.DAZ_CAD_EXAMPLES = {examples_json};
    </script>
    <script type="importmap">
    {import_map}
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

    # Replace chat pane content with "AI not available" image
    html = re.sub(
        r'<div class="chat-pane">.*?</div>\s*</div>\s*</div>',
        '<div class="chat-pane" style="display: flex; flex-direction: column; align-items: center; '
        'justify-content: center; background: #0B1120; padding: 20px;">'
        '<img src="images/feature-ai-unavailable.jpg" alt="AI Assistant not available in web version" '
        'style="max-width: 100%; border-radius: 12px; margin-bottom: 12px;">'
        '<p style="color: #94A3B8; font-size: 0.8rem; text-align: center; line-height: 1.4;">'
        'Run <code style="color: #06B6D4;">./run serve</code> locally for AI-assisted modeling</p>'
        '</div></div></div>',
        html,
        count=1,
        flags=re.DOTALL,
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

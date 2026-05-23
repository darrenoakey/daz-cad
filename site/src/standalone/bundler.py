"""Standalone editor bundler - packages editor for serverless use."""

import hashlib
import json
import re
import shutil
from pathlib import Path


# Intra-/static module basenames whose import specifiers get content-hash
# cache-busting. cad-worker.js is handled separately (it's loaded as a Worker
# URL, not an ES import, and must stay an absolute path).
_BUSTABLE_MODULES = (
    "cad", "viewer", "gridfinity", "patterns", "naming",
    "threemf", "opentype.module",
)


def _compute_build_hash(static_src: Path) -> str:
    """Content hash over all bundled JS source — changes iff any JS changes.

    A single build hash (rather than per-file) is used so that ANY change to
    ANY module re-versions every URL in the graph. That makes a stale module
    impossible, including transitive imports inside the CAD Worker (which does
    not use the page's import map). Cache-optimality is traded for correctness;
    these files almost always change together anyway.
    """
    h = hashlib.sha256()
    for filename in sorted(JS_FILES):
        src = static_src / filename
        if src.exists():
            h.update(src.read_bytes())
    return h.hexdigest()[:12]


def _bust_js(content: str, build_hash: str) -> str:
    """Rewrite a JS file's intra-/static import URLs to carry ?v=<hash>.

    Handles three forms so the version propagates through the whole module
    graph, both in the page (import map) context and the Worker context:
      - absolute `/static/foo.js`  -> `./foo.js?v=<hash>` (relative; all
        modules live in /static/, so this resolves identically and needs no
        import map — which the Worker lacks)
      - relative `./foo.js`        -> `./foo.js?v=<hash>`
      - the Worker URL `/static/cad-worker.js` -> same path + ?v=<hash>
        (kept absolute: it's resolved against the document base, not /static/)
    """
    alt = "|".join(m.replace(".", r"\.") for m in _BUSTABLE_MODULES)
    # Worker URL first (absolute path preserved), avoid double-busting.
    content = re.sub(
        r"(/static/cad-worker\.js)(?!\?)",
        rf"\1?v={build_hash}",
        content,
    )
    # Absolute static module imports -> relative + version.
    content = re.sub(
        rf"/static/({alt})\.js(?!\?)",
        rf"./\1.js?v={build_hash}",
        content,
    )
    # Already-relative static module imports -> + version.
    content = re.sub(
        rf"(?<![\w/])\./({alt})\.js(?!\?)",
        rf"./\1.js?v={build_hash}",
        content,
    )
    return content


# JavaScript files to copy to the standalone site
JS_FILES = [
    "cad.js",
    "editor.js",
    "viewer.js",
    "patterns.js",
    "naming.js",
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


def _build_import_map(build_hash: str) -> str:
    """Build the import map for standalone mode using version-stamped paths.

    Belt-and-suspenders: _bust_js() already rewrites source imports to
    relative ?v= URLs, so these /static/* entries are normally unused. They
    remain (with the same version) so any absolute import we didn't rewrite
    still resolves to a busted URL rather than a cacheable bare path.
    """
    v = f"?v={build_hash}"
    return json.dumps({
        "imports": {
            "three": "https://cdn.jsdelivr.net/npm/three@0.160.0/build/three.module.js",
            "three/addons/": "https://cdn.jsdelivr.net/npm/three@0.160.0/examples/jsm/",
            "jszip": "https://cdn.jsdelivr.net/npm/jszip@3.10.1/dist/jszip.min.js",
            "/static/cad.js": f"./static/cad.js{v}",
            "/static/viewer.js": f"./static/viewer.js{v}",
            "/static/gridfinity.js": f"./static/gridfinity.js{v}",
            "/static/patterns.js": f"./static/patterns.js{v}",
            "/static/naming.js": f"./static/naming.js{v}",
            "/static/threemf.js": f"./static/threemf.js{v}",
            "/static/opentype.module.js": f"./static/opentype.module.js{v}",
        }
    }, indent=8)


def _build_editor_html(source_html: str, examples: dict[str, str], build_hash: str) -> str:
    """Transform editor.html for standalone use."""
    html = source_html

    # Remove the dynamic import map script and replace with static one
    # Use lambda replacement to prevent re.sub from interpreting backslash
    # escapes in the JSON (e.g. \\n becoming literal newlines)
    examples_json = json.dumps(examples, indent=8)
    import_map = _build_import_map(build_hash)
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

    # Remove the cache-busted module loading and replace with a version-stamped
    # direct import so a stale editor.js can never be served from browser cache.
    html = re.sub(
        r'<!-- Cache-busted module loading -->.*?</script>',
        lambda _: f"""<script type="module">
        import('./static/editor.js?v={build_hash}');
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

    # Chat pane is left intact; editor.js decides at runtime whether to
    # use Chrome's on-device LanguageModel API or show an "unavailable" fallback.

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

    # Content hash over all JS — stamped into every module URL for cache-busting.
    build_hash = _compute_build_hash(static_src)

    # Copy JS files, rewriting intra-/static import URLs to carry ?v=<hash>.
    for filename in JS_FILES:
        src = static_src / filename
        if src.exists():
            (static_dst / filename).write_text(_bust_js(src.read_text(), build_hash))

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
    standalone_html = _build_editor_html(editor_html, examples, build_hash)

    (output_dir / "editor-standalone.html").write_text(standalone_html)

    # The wrapper editor.html (produced by the generator) embeds the standalone
    # page in an iframe. Version-stamp that iframe URL too, so the entire chain
    # below the single top-level editor.html is content-hashed and a stale
    # standalone page can't be served from browser cache.
    wrapper_path = output_dir / "editor.html"
    if wrapper_path.exists():
        wrapper = wrapper_path.read_text()
        # Static src attribute.
        wrapper = wrapper.replace(
            'src="editor-standalone.html"',
            f'src="editor-standalone.html?v={build_hash}"',
        )
        # Dynamic src set from URL params: keep the version, fold the page's
        # own query (?file=...) in as an additional & param.
        wrapper = wrapper.replace(
            "'editor-standalone.html' + window.location.search",
            f"'editor-standalone.html?v={build_hash}' + "
            "window.location.search.replace(/^\\?/, '&')",
        )
        wrapper_path.write_text(wrapper)

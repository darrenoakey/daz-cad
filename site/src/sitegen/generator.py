"""Main site generator - produces all HTML pages into local/web/."""

import json
from pathlib import Path

from . import _common
from . import hero
from . import features
from . import examples_gallery
from . import footer
from . import documentation
from . import editor_embed


def _load_config(site_root: Path) -> dict:
    """Load site config from local/config.json."""
    config_path = site_root / "local" / "config.json"
    return json.loads(config_path.read_text())


def generate_index(config: dict) -> str:
    """Generate the home page."""
    site = config.get("site", {})
    github_url = config.get("github", "")

    body_css = hero.css() + features.css() + examples_gallery.css() + footer.css()
    body_html = (
        hero.html(
            tagline=site.get("tagline", "Browser-Based Parametric CAD"),
            subtitle="Design 3D models with code. Export to your 3D printer.",
        )
        + features.html()
        + examples_gallery.html_section(limit=6)
        + footer.html(github_url)
    )

    return _common.page_wrapper(
        title=f"{site.get('name', 'daz-cad')} - {site.get('tagline', 'Parametric CAD')}",
        description="Browser-based parametric CAD editor powered by OpenCascade.js. Design 3D models with code.",
        active="home",
        github_url=github_url,
        body_css=body_css,
        body_html=body_html,
    )


def generate_docs(config: dict, project_root: Path) -> str:
    """Generate the documentation page."""
    site = config.get("site", {})
    github_url = config.get("github", "")
    docs_dir = project_root / "docs"
    spec_path = project_root / "static" / "cad-library-spec.md"

    docs_html = documentation.generate_docs_html(docs_dir, spec_path)
    body_css = documentation.css()
    body_js = documentation.js()

    return _common.page_wrapper(
        title=f"Documentation - {site.get('name', 'daz-cad')}",
        description="Complete API documentation for daz-cad parametric CAD library.",
        active="docs",
        github_url=github_url,
        body_css=body_css,
        body_html=docs_html,
        body_js=body_js,
    )


def generate_examples(config: dict) -> str:
    """Generate the examples gallery page."""
    site = config.get("site", {})
    github_url = config.get("github", "")

    body_css = examples_gallery.css()
    body_html = examples_gallery.html_page() + footer.html(github_url)

    return _common.page_wrapper(
        title=f"Examples - {site.get('name', 'daz-cad')}",
        description="Example CAD models built with daz-cad. Gridfinity bins, pattern cutting, and more.",
        active="examples",
        github_url=github_url,
        body_css=body_css + footer.css(),
        body_html=body_html,
    )


def generate_editor(config: dict) -> str:
    """Generate the editor embed page."""
    site = config.get("site", {})
    github_url = config.get("github", "")

    body_css = editor_embed.css()
    body_html = editor_embed.html_page()
    body_js = editor_embed.js()

    return _common.page_wrapper(
        title=f"Editor - {site.get('name', 'daz-cad')}",
        description="Try daz-cad in your browser. Full parametric CAD editor with OpenCascade.js.",
        active="editor",
        github_url=github_url,
        body_css=body_css,
        body_html=body_html,
        body_js=body_js,
    )


def generate_error() -> str:
    """Generate a simple error page."""
    return """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Page Not Found - daz-cad</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, sans-serif;
            background: #0B1120;
            color: #F1F5F9;
            display: flex;
            align-items: center;
            justify-content: center;
            min-height: 100vh;
            margin: 0;
            text-align: center;
        }
        h1 { font-size: 4rem; margin-bottom: 0.5rem; color: #3B82F6; }
        p { color: #94A3B8; margin-bottom: 1.5rem; }
        a {
            color: #3B82F6;
            text-decoration: none;
            padding: 0.75rem 1.5rem;
            border: 1px solid #334155;
            border-radius: 8px;
        }
        a:hover { border-color: #3B82F6; }
    </style>
</head>
<body>
    <div>
        <h1>404</h1>
        <p>Page not found</p>
        <a href="/">Back to Home</a>
    </div>
</body>
</html>
"""


def generate_site(site_root: Path, project_root: Path) -> Path:
    """Generate the complete static site.

    Args:
        site_root: Path to site/ directory.
        project_root: Path to daz-cad root directory.

    Returns:
        Path to the generated output directory (local/web/).
    """
    config = _load_config(site_root)
    web_path = site_root / "local" / "web"
    web_path.mkdir(parents=True, exist_ok=True)

    # Generate pages
    pages = {
        "index.html": generate_index(config),
        "docs.html": generate_docs(config, project_root),
        "examples.html": generate_examples(config),
        "editor.html": generate_editor(config),
        "error.html": generate_error(),
    }

    for filename, content in pages.items():
        (web_path / filename).write_text(content)

    # Create directories for assets
    (web_path / "images").mkdir(exist_ok=True)
    (web_path / "screenshots").mkdir(exist_ok=True)
    (web_path / "static").mkdir(exist_ok=True)

    return web_path

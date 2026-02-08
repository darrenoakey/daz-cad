"""Example models gallery section and page."""

from pathlib import Path


def css() -> str:
    return """
.examples-section {
    padding: var(--space-3xl) 0;
}
.examples-section h2 {
    text-align: center;
    margin-bottom: var(--space-2xl);
}
.examples-grid {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: var(--space-lg);
}
.example-card {
    background: var(--bg-card);
    border: 1px solid var(--border-color);
    border-radius: 12px;
    overflow: hidden;
    transition: border-color 0.2s, transform 0.2s;
}
.example-card:hover {
    border-color: var(--accent-blue);
    transform: translateY(-2px);
}
.example-card img {
    width: 100%;
    height: 220px;
    object-fit: cover;
    background: var(--bg-code);
}
.example-card-body {
    padding: var(--space-md);
}
.example-card h3 {
    font-size: 1rem;
    margin-bottom: var(--space-xs);
}
.example-card p {
    color: var(--text-secondary);
    font-size: 0.8rem;
    margin-bottom: var(--space-md);
    line-height: 1.5;
}
.example-card-actions {
    display: flex;
    gap: var(--space-sm);
}
.example-card-actions .btn {
    font-size: 0.75rem;
    padding: 0.375rem 0.75rem;
}

@media (max-width: 992px) { .examples-grid { grid-template-columns: repeat(2, 1fr); } }
@media (max-width: 576px) { .examples-grid { grid-template-columns: 1fr; } }
"""


EXAMPLES = [
    {"file": "default.js", "title": "Simple Box", "desc": "Basic box with filleted edges. A great starting point."},
    {"file": "demo_patterns.js", "title": "Pattern Showcase", "desc": "Honeycomb, circles, lines, and diamond patterns cut into faces."},
    {"file": "gridfinity-demo.js", "title": "Gridfinity Bin", "desc": "Stackable Gridfinity storage bin with custom compartments."},
    {"file": "open-box.js", "title": "Open Box", "desc": "Box with boolean subtraction creating an open container."},
    {"file": "baseplate-demo.js", "title": "Gridfinity Baseplate", "desc": "Grid baseplate for Gridfinity storage system."},
    {"file": "border-demo.js", "title": "Border & Clipping", "desc": "Pattern cutting with border margins and face clipping."},
    {"file": "demo_lines_pattern.js", "title": "Line Patterns", "desc": "Various line pattern configurations and angles."},
    {"file": "tab-demo.js", "title": "Tab & Slot", "desc": "Interlocking tab and slot interface between parts."},
    {"file": "clip-demo.js", "title": "Clip Modes", "desc": "Comparison of partial vs whole clip modes for patterns."},
    {"file": "baseplate-on-surface.js", "title": "Surface Baseplate", "desc": "Gridfinity baseplate placed on an arbitrary surface."},
]


def _screenshot_name(filename: str) -> str:
    return f"screenshots/{filename.replace('.js', '.png')}"


def html_section(limit: int = 6) -> str:
    """Generate the home page example showcase section."""
    cards = []
    for ex in EXAMPLES[:limit]:
        screenshot = _screenshot_name(ex["file"])
        cards.append(f"""<div class="example-card">
            <img src="{screenshot}" alt="{ex['title']}" loading="lazy">
            <div class="example-card-body">
                <h3>{ex["title"]}</h3>
                <p>{ex["desc"]}</p>
                <div class="example-card-actions">
                    <a href="/editor?file={ex['file']}" class="btn btn-primary">Open in Editor</a>
                </div>
            </div>
        </div>""")

    return f"""<section class="examples-section">
    <div class="container">
        <h2>Example Models</h2>
        <div class="examples-grid">
            {"".join(cards)}
        </div>
        <div style="text-align: center; margin-top: var(--space-xl);">
            <a href="/examples" class="btn btn-secondary">View All Examples</a>
        </div>
    </div>
</section>
"""


def html_page() -> str:
    """Generate the full examples gallery page content."""
    cards = []
    for ex in EXAMPLES:
        screenshot = _screenshot_name(ex["file"])
        cards.append(f"""<div class="example-card">
            <img src="{screenshot}" alt="{ex['title']}" loading="lazy">
            <div class="example-card-body">
                <h3>{ex["title"]}</h3>
                <p>{ex["desc"]}</p>
                <div class="example-card-actions">
                    <a href="/editor?file={ex['file']}" class="btn btn-primary">Open in Editor</a>
                </div>
            </div>
        </div>""")

    return f"""<section class="examples-section" style="min-height: 80vh;">
    <div class="container">
        <h2>All Examples</h2>
        <div class="examples-grid">
            {"".join(cards)}
        </div>
    </div>
</section>
"""


def load_example_sources(examples_dir: Path) -> dict[str, str]:
    """Load example JavaScript files from the examples directory."""
    sources = {}
    for ex in EXAMPLES:
        filepath = examples_dir / ex["file"]
        if filepath.exists():
            sources[ex["file"]] = filepath.read_text()
    return sources

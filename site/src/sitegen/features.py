"""Feature grid section for the home page."""


def css() -> str:
    return """
.features {
    padding: var(--space-3xl) 0;
}
.features h2 {
    text-align: center;
    margin-bottom: var(--space-2xl);
}
.features-grid {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: var(--space-lg);
}
.feature-card {
    background: var(--bg-card);
    border: 1px solid var(--border-color);
    border-radius: 12px;
    padding: var(--space-lg);
    transition: border-color 0.2s, transform 0.2s;
}
.feature-card:hover {
    border-color: var(--accent-blue);
    transform: translateY(-2px);
}
.feature-card img {
    width: 100%;
    height: 180px;
    object-fit: cover;
    border-radius: 8px;
    margin-bottom: var(--space-md);
    background: var(--bg-code);
}
.feature-card h3 {
    margin-bottom: var(--space-sm);
    color: var(--accent-cyan);
}
.feature-card p {
    color: var(--text-secondary);
    font-size: 0.875rem;
    line-height: 1.6;
}

@media (max-width: 992px) { .features-grid { grid-template-columns: repeat(2, 1fr); } }
@media (max-width: 576px) { .features-grid { grid-template-columns: 1fr; } }
"""


FEATURES = [
    {
        "title": "Parametric Modeling",
        "desc": "Design 3D models with code. Live preview updates as you type. Extract variables as interactive sliders.",
        "image": None,
    },
    {
        "title": "OpenCascade Engine",
        "desc": "Industry-grade B-rep geometry kernel running entirely in your browser via WebAssembly.",
        "image": None,
    },
    {
        "title": "Pattern Library",
        "desc": "Honeycomb, circles, lines, diamonds, and more. Cut patterns into any face with automatic clipping.",
        "image": "images/feature-patterns.jpg",
    },
    {
        "title": "Gridfinity Support",
        "desc": "Generate Gridfinity bins, plugs, and baseplates. Auto-fit bins to your cuts with a single function.",
        "image": "images/feature-gridfinity.jpg",
    },
    {
        "title": "Multi-Color 3MF Export",
        "desc": "Export multi-material 3MF files compatible with Bambu Lab printers. Full color support.",
        "image": "images/feature-export.jpg",
    },
    {
        "title": "AI Assistant",
        "desc": "Natural language model editing in the server version. Describe what you want and the AI builds it.",
        "image": None,
    },
]


def html() -> str:
    cards = []
    for f in FEATURES:
        img = f'<img src="{f["image"]}" alt="{f["title"]}">' if f["image"] else ""
        cards.append(f"""<div class="feature-card">
            {img}
            <h3>{f["title"]}</h3>
            <p>{f["desc"]}</p>
        </div>""")

    return f"""<section class="features">
    <div class="container">
        <h2>Features</h2>
        <div class="features-grid">
            {"".join(cards)}
        </div>
    </div>
</section>
"""

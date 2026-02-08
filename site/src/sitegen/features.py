"""Feature grid section for the home page and individual feature detail pages."""


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
    text-decoration: none;
    color: inherit;
    display: block;
}
.feature-card:hover {
    border-color: var(--accent-blue);
    transform: translateY(-2px);
    color: inherit;
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


def detail_css() -> str:
    """CSS for individual feature detail pages."""
    return """
.feature-detail {
    max-width: 800px;
    margin: 0 auto;
    padding: var(--space-3xl) var(--space-xl);
}
.feature-detail h1 {
    margin-bottom: var(--space-md);
    background: linear-gradient(135deg, var(--accent-blue), var(--accent-cyan));
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
}
.feature-detail .feature-tagline {
    font-size: 1.25rem;
    color: var(--text-secondary);
    margin-bottom: var(--space-2xl);
    line-height: 1.6;
}
.feature-detail img.feature-hero {
    width: 100%;
    border-radius: 12px;
    margin-bottom: var(--space-2xl);
    border: 1px solid var(--border-color);
}
.feature-detail h2 {
    margin-top: var(--space-2xl);
    margin-bottom: var(--space-md);
    color: var(--accent-cyan);
}
.feature-detail p {
    color: var(--text-secondary);
    line-height: 1.7;
    margin-bottom: var(--space-md);
}
.feature-detail ul {
    color: var(--text-secondary);
    padding-left: var(--space-xl);
    margin-bottom: var(--space-lg);
}
.feature-detail li {
    margin-bottom: var(--space-sm);
    line-height: 1.6;
}
.feature-detail pre {
    margin-bottom: var(--space-lg);
}
.feature-detail .cta-section {
    margin-top: var(--space-3xl);
    padding: var(--space-xl);
    background: var(--bg-card);
    border: 1px solid var(--border-color);
    border-radius: 12px;
    text-align: center;
}
.feature-detail .cta-section p {
    color: var(--text-primary);
    margin-bottom: var(--space-md);
}
"""


FEATURES = [
    {
        "slug": "parametric-modeling",
        "title": "Parametric Modeling",
        "desc": "Design 3D models with code. Live preview updates as you type. Extract variables as interactive sliders.",
        "image": None,
        "screenshot": "screenshots/default.png",
        "detail": {
            "tagline": "Write code, see 3D models update in real time. Extract any variable into an interactive slider.",
            "sections": [
                ("Code-Driven Design", """
<p>daz-cad uses a JavaScript API inspired by CadQuery. You write code that describes your 3D model, and the live preview updates instantly as you type. No clicking through menus or dragging handles — just clean, readable code that produces precise geometry.</p>

<pre><code class="language-javascript">// A simple parametric box with rounded edges
const width = 40;    // slider: 10..100
const height = 20;   // slider: 5..50
const radius = 3;    // slider: 0..10

let result = box(width, width, height)
    .edges("|Z").fillet(radius);
</code></pre>
"""),
                ("Interactive Sliders", """
<p>Any variable with a <code>// slider: min..max</code> comment is automatically extracted into an interactive slider in the properties panel. Drag the slider and watch your model update in real time — perfect for dialing in dimensions.</p>
<ul>
<li>Numeric sliders with min/max ranges</li>
<li>Real-time 3D preview updates</li>
<li>Multiple parameters at once</li>
</ul>
"""),
                ("Monaco Editor", """
<p>The built-in code editor is powered by Monaco — the same editor engine behind VS Code. You get syntax highlighting, autocomplete, error checking, and all the editing features you'd expect from a professional IDE.</p>
"""),
            ],
        },
    },
    {
        "slug": "opencascade",
        "title": "OpenCascade Engine",
        "desc": "Industry-grade B-rep geometry kernel running entirely in your browser via WebAssembly.",
        "image": None,
        "screenshot": "screenshots/open-box.png",
        "detail": {
            "tagline": "The same geometry kernel used in professional CAD software, compiled to WebAssembly and running in your browser.",
            "sections": [
                ("Industry-Grade Geometry", """
<p>OpenCascade is an open-source B-rep (boundary representation) geometry kernel used in professional CAD tools like FreeCAD. daz-cad compiles it to WebAssembly via OpenCascade.js, giving you access to the full power of B-rep modeling directly in the browser — no installation required.</p>
"""),
                ("B-Rep Modeling", """
<p>Unlike mesh-based tools that approximate surfaces with triangles, B-rep modeling works with exact mathematical surfaces. This means:</p>
<ul>
<li>Precise fillets and chamfers on any edge</li>
<li>Exact boolean operations (union, cut, intersect)</li>
<li>Clean geometry suitable for 3D printing</li>
<li>Edge and face selection for targeted operations</li>
</ul>
"""),
                ("Zero Installation", """
<p>Everything runs in the browser. OpenCascade.js is loaded from CDN, the geometry kernel initializes in seconds, and your models are computed entirely client-side. No server required for the core CAD operations.</p>
"""),
            ],
        },
    },
    {
        "slug": "patterns",
        "title": "Pattern Library",
        "desc": "Honeycomb, circles, lines, diamonds, and more. Cut patterns into any face with automatic clipping.",
        "image": "images/feature-patterns.jpg",
        "screenshot": "screenshots/demo_patterns.png",
        "detail": {
            "tagline": "Cut repeating patterns into any face of your model. Honeycomb, circles, lines, diamonds — with automatic boundary clipping.",
            "sections": [
                ("cutPattern API", """
<p>The <code>cutPattern()</code> function cuts repeating geometric shapes into any face of your model. Select a face, choose a pattern shape, and set your dimensions — the pattern automatically fills the face with proper spacing and alignment.</p>

<pre><code class="language-javascript">let result = box(80, 80, 5)
    .faces(">Z")
    .cutPattern({
        shape: "hexagon",
        width: 8,
        spacing: 2,
        border: 3
    });
</code></pre>
"""),
                ("Pattern Shapes", """
<p>Built-in pattern shapes for every need:</p>
<ul>
<li><strong>Hexagon</strong> — honeycomb patterns, optimal for structural lightweighting</li>
<li><strong>Circle</strong> — round perforations with configurable diameter</li>
<li><strong>Diamond</strong> — rotated square patterns for decorative panels</li>
<li><strong>Line</strong> — parallel slot patterns, configurable angle</li>
<li><strong>Square</strong> — grid patterns for ventilation or aesthetics</li>
</ul>
"""),
                ("Smart Clipping", """
<p>Patterns automatically clip to the face boundary. Two clip modes handle edge cases:</p>
<ul>
<li><code>clip: 'partial'</code> — clips shapes at the face edge (partial shapes appear at boundaries)</li>
<li><code>clip: 'whole'</code> — only keeps shapes fully inside the face (clean edges)</li>
</ul>
<p>A configurable <code>border</code> parameter insets the pattern from the face edges, maintaining structural integrity.</p>
"""),
            ],
        },
    },
    {
        "slug": "gridfinity",
        "title": "Gridfinity Support",
        "desc": "Generate Gridfinity bins, plugs, and baseplates. Auto-fit bins to your cuts with a single function.",
        "image": "images/feature-gridfinity.jpg",
        "screenshot": "screenshots/gridfinity-demo.png",
        "detail": {
            "tagline": "Generate parametric Gridfinity storage components. Bins, plugs, baseplates, and custom compartments — all to spec.",
            "sections": [
                ("Gridfinity Module", """
<p>The Gridfinity module generates storage components that follow the Gridfinity open standard. Create bins, plugs, and baseplates that stack and interlock perfectly with any other Gridfinity-compatible components.</p>

<pre><code class="language-javascript">// 2x3 Gridfinity bin, 4 units tall
let result = Gridfinity.bin({
    gridX: 2,
    gridY: 3,
    height: 4
});
</code></pre>
"""),
                ("Custom Compartments", """
<p>Use <code>cutRectGrid()</code> and <code>cutCircleGrid()</code> to add custom compartment layouts to your bins. Dividers are positioned on the Gridfinity grid for perfect alignment.</p>

<pre><code class="language-javascript">let result = Gridfinity.bin({ gridX: 3, gridY: 2, height: 3 })
    .cutRectGrid({ cols: 3, rows: 2, wall: 1.2 });
</code></pre>
"""),
                ("Full Component Set", """
<ul>
<li><strong>bin()</strong> — storage bins with configurable grid size and height</li>
<li><strong>plug()</strong> — plugs that fill empty bin slots</li>
<li><strong>baseplate()</strong> — baseplates that bins stack onto</li>
<li><strong>fitBin()</strong> — auto-fits a bin to your custom cuts</li>
<li><strong>cutRectGrid()</strong> / <strong>cutCircleGrid()</strong> — compartment layouts</li>
</ul>
"""),
            ],
        },
    },
    {
        "slug": "3mf-export",
        "title": "Multi-Color 3MF Export",
        "desc": "Export multi-material 3MF files compatible with Bambu Lab printers. Full color support.",
        "image": "images/feature-export.jpg",
        "screenshot": None,
        "detail": {
            "tagline": "Export your models as multi-color 3MF files. Assign colors to parts and print with Bambu Lab multi-material support.",
            "sections": [
                ("3MF Format", """
<p>3MF is the modern standard for 3D printing files. Unlike STL, 3MF supports multiple materials, colors, and metadata in a single file. daz-cad generates 3MF files that are ready to slice in Bambu Studio.</p>
"""),
                ("Multi-Color Printing", """
<p>Assign colors to different parts of your model using the <code>.color()</code> method. When exported to 3MF, each color becomes a separate material that your slicer can assign to different filaments.</p>

<pre><code class="language-javascript">let base = box(40, 40, 5).color("#2196F3");
let lid = box(40, 40, 2)
    .translate(0, 0, 5)
    .color("#FF5722");

let result = base.union(lid);
</code></pre>
"""),
                ("Export Options", """
<ul>
<li><strong>STL</strong> — universal 3D printing format, single color</li>
<li><strong>3MF</strong> — multi-color, multi-material, Bambu Lab compatible</li>
<li>Infill density and pattern metadata</li>
<li>Part naming for slicer organization</li>
</ul>
"""),
            ],
        },
    },
    {
        "slug": "ai-assistant",
        "title": "AI Assistant",
        "desc": "Natural language model editing in the server version. Describe what you want and the AI builds it.",
        "image": "images/feature-ai-unavailable.jpg",
        "screenshot": None,
        "detail": {
            "tagline": "Describe what you want in plain English. The AI assistant writes the code and updates your 3D model.",
            "sections": [
                ("Natural Language CAD", """
<p>The server version of daz-cad includes a built-in AI assistant powered by Claude. Describe your model in plain English — "make a box with honeycomb pattern on top" — and the AI writes the corresponding daz-cad code.</p>
"""),
                ("How It Works", """
<p>The AI assistant receives the full daz-cad API specification and your current code as context. It understands the complete library including patterns, Gridfinity, boolean operations, and edge selection. Responses include working code that runs immediately in the live preview.</p>
<ul>
<li>Understands the complete daz-cad API</li>
<li>Modifies your existing code or creates from scratch</li>
<li>Explains what it changed and why</li>
<li>Iterative refinement — keep chatting to adjust the model</li>
</ul>
"""),
                ("Server Version Only", """
<p>The AI assistant requires the daz-cad server to be running locally (it uses Claude's API). The standalone editor on this website has all the CAD features but without the AI chat. Clone the repo and run <code>./run serve</code> to get the full experience.</p>
"""),
            ],
        },
    },
]


def html() -> str:
    cards = []
    for f in FEATURES:
        img = f'<img src="{f["image"]}" alt="{f["title"]}">' if f["image"] else ""
        cards.append(f"""<a href="/features/{f["slug"]}.html" class="feature-card">
            {img}
            <h3>{f["title"]}</h3>
            <p>{f["desc"]}</p>
        </a>""")

    return f"""<section class="features">
    <div class="container">
        <h2>Features</h2>
        <div class="features-grid">
            {"".join(cards)}
        </div>
    </div>
</section>
"""


def generate_detail_page(feature: dict) -> str:
    """Generate the HTML body content for a feature detail page."""
    sections_html = ""
    for heading, content in feature["detail"]["sections"]:
        sections_html += f'<h2>{heading}</h2>\n{content}\n'

    img_html = ""
    if feature.get("screenshot"):
        img_html = f'<img class="feature-hero" src="/{feature["screenshot"]}" alt="{feature["title"]}">'
    elif feature.get("image"):
        img_html = f'<img class="feature-hero" src="/{feature["image"]}" alt="{feature["title"]}">'

    return f"""<article class="feature-detail">
    <h1>{feature["title"]}</h1>
    <p class="feature-tagline">{feature["detail"]["tagline"]}</p>
    {img_html}
    {sections_html}
    <div class="cta-section">
        <p>Try {feature["title"]} in the browser editor</p>
        <a href="/editor.html" class="btn btn-primary">Open Editor</a>
    </div>
</article>
"""

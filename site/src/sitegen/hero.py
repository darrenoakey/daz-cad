"""Full-screen hero section with CTA buttons."""


def css() -> str:
    return """
.hero {
    position: relative;
    min-height: 500px;
    display: flex;
    align-items: center;
    justify-content: center;
    text-align: center;
    overflow: hidden;
    background: linear-gradient(135deg, #0B1120 0%, #1a2744 50%, #0B1120 100%);
}
.hero-bg {
    position: absolute;
    inset: 0;
    background-size: cover;
    background-position: center;
    opacity: 0.3;
}
.hero-content {
    position: relative;
    z-index: 1;
    max-width: 700px;
    padding: var(--space-3xl) var(--space-xl);
}
.hero h1 {
    font-size: 3rem;
    margin-bottom: var(--space-md);
    background: linear-gradient(135deg, var(--accent-blue), var(--accent-cyan));
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
}
.hero p {
    font-size: 1.25rem;
    color: var(--text-secondary);
    margin-bottom: var(--space-2xl);
    line-height: 1.6;
}
.hero-buttons {
    display: flex;
    gap: var(--space-md);
    justify-content: center;
    flex-wrap: wrap;
}
@media (max-width: 768px) {
    .hero h1 { font-size: 2rem; }
    .hero p { font-size: 1rem; }
}
"""


def html(tagline: str, subtitle: str, hero_image: str = "images/hero.jpg") -> str:
    return f"""<section class="hero">
    <div class="hero-bg" style="background-image: url('{hero_image}');"></div>
    <div class="hero-content">
        <h1>{tagline}</h1>
        <p>{subtitle}</p>
        <div class="hero-buttons">
            <a href="/editor" class="btn btn-primary">Try It Now</a>
            <a href="/docs" class="btn btn-secondary">Documentation</a>
        </div>
    </div>
</section>
"""

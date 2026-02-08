"""Footer section."""


def css() -> str:
    return """
.site-footer {
    background: var(--bg-secondary);
    border-top: 1px solid var(--border-color);
    padding: var(--space-2xl) 0;
    margin-top: var(--space-3xl);
}
.footer-content {
    display: flex;
    justify-content: space-between;
    align-items: center;
    flex-wrap: wrap;
    gap: var(--space-md);
}
.footer-brand {
    font-family: var(--font-display);
    font-weight: 700;
    color: var(--text-secondary);
}
.footer-links {
    display: flex;
    gap: var(--space-lg);
    list-style: none;
}
.footer-links a {
    color: var(--text-muted);
    font-size: 0.875rem;
}
.footer-links a:hover { color: var(--text-primary); }
"""


def html(github_url: str = "") -> str:
    github_link = f'<li><a href="{github_url}" target="_blank" rel="noopener">GitHub</a></li>' if github_url else ""

    return f"""<footer class="site-footer">
    <div class="container">
        <div class="footer-content">
            <div class="footer-brand">daz-cad</div>
            <ul class="footer-links">
                <li><a href="/docs">Documentation</a></li>
                <li><a href="/examples">Examples</a></li>
                <li><a href="/editor">Editor</a></li>
                {github_link}
            </ul>
        </div>
    </div>
</footer>
"""

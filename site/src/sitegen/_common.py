"""Common page wrapper, navigation, and head meta."""

from . import _global


def css() -> str:
    return """
/* Navigation */
.nav {
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    height: var(--nav-height);
    background: var(--bg-secondary);
    border-bottom: 1px solid var(--border-color);
    z-index: 1000;
    backdrop-filter: blur(12px);
}
.nav .container {
    display: flex;
    align-items: center;
    justify-content: space-between;
    height: 100%;
}
.nav-brand {
    display: flex;
    align-items: center;
    gap: var(--space-sm);
    font-family: var(--font-display);
    font-size: 1.125rem;
    font-weight: 700;
    color: var(--text-primary);
}
.nav-brand img { width: 28px; height: 28px; }
.nav-links {
    display: flex;
    align-items: center;
    gap: var(--space-lg);
    list-style: none;
}
.nav-links a {
    color: var(--text-secondary);
    font-size: 0.875rem;
    font-weight: 500;
    transition: color 0.2s;
}
.nav-links a:hover, .nav-links a.active { color: var(--text-primary); }
.theme-toggle {
    background: none;
    border: 1px solid var(--border-color);
    color: var(--text-secondary);
    cursor: pointer;
    padding: 0.375rem 0.5rem;
    border-radius: 6px;
    font-size: 1rem;
    transition: all 0.2s;
}
.theme-toggle:hover { border-color: var(--accent-blue); color: var(--text-primary); }

/* Mobile nav */
.nav-toggle { display: none; background: none; border: none; color: var(--text-primary); font-size: 1.5rem; cursor: pointer; }
@media (max-width: 768px) {
    .nav-toggle { display: block; }
    .nav-links {
        display: none;
        position: absolute;
        top: var(--nav-height);
        left: 0;
        right: 0;
        background: var(--bg-secondary);
        border-bottom: 1px solid var(--border-color);
        flex-direction: column;
        padding: var(--space-md);
    }
    .nav-links.open { display: flex; }
}
"""


def js() -> str:
    return """
// Theme toggle
(function() {
    const saved = localStorage.getItem('theme');
    if (saved) document.documentElement.setAttribute('data-theme', saved);

    document.addEventListener('DOMContentLoaded', function() {
        const toggle = document.querySelector('.theme-toggle');
        if (toggle) {
            toggle.addEventListener('click', function() {
                const current = document.documentElement.getAttribute('data-theme');
                const next = current === 'light' ? 'dark' : 'light';
                document.documentElement.setAttribute('data-theme', next);
                localStorage.setItem('theme', next);
                toggle.textContent = next === 'light' ? '\\u263e' : '\\u2600';
            });
        }

        // Mobile nav toggle
        const navToggle = document.querySelector('.nav-toggle');
        const navLinks = document.querySelector('.nav-links');
        if (navToggle && navLinks) {
            navToggle.addEventListener('click', function() {
                navLinks.classList.toggle('open');
            });
        }
    });
})();
"""


def head(title: str, description: str, og_image: str = "images/og.jpg") -> str:
    return f"""<!DOCTYPE html>
<html lang="en" data-theme="dark">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <meta name="description" content="{description}">
    <meta property="og:title" content="{title}">
    <meta property="og:description" content="{description}">
    <meta property="og:image" content="{og_image}">
    <meta property="og:type" content="website">
    <link rel="icon" type="image/png" sizes="32x32" href="favicon-32.png">
    <link rel="apple-touch-icon" sizes="180x180" href="favicon-180.png">
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;600;700&display=swap" rel="stylesheet">
    <style>
{_global.css()}
{css()}
    </style>
</head>
"""


def nav(active: str = "", github_url: str = "") -> str:
    def link(href: str, text: str, name: str) -> str:
        cls = ' class="active"' if name == active else ""
        return f'<a href="{href}"{cls}>{text}</a>'

    github_link = f'<a href="{github_url}" target="_blank" rel="noopener">GitHub</a>' if github_url else ""

    return f"""<nav class="nav">
    <div class="container">
        <a href="/" class="nav-brand">
            <img src="favicon-32.png" alt="daz-cad">
            <span>daz-cad</span>
        </a>
        <button class="nav-toggle" aria-label="Menu">&#9776;</button>
        <ul class="nav-links">
            <li>{link("/", "Home", "home")}</li>
            <li>{link("/docs", "Docs", "docs")}</li>
            <li>{link("/examples", "Examples", "examples")}</li>
            <li>{link("/editor", "Editor", "editor")}</li>
            <li>{github_link}</li>
            <li><button class="theme-toggle" aria-label="Toggle theme">&#9790;</button></li>
        </ul>
    </div>
</nav>
<div style="height: var(--nav-height);"></div>
"""


def page_wrapper(title: str, description: str, active: str, github_url: str, body_css: str, body_html: str, body_js: str = "") -> str:
    all_js = js()
    if body_js:
        all_js += "\n" + body_js

    return (
        head(title, description)
        + f"<style>{body_css}</style>\n"
        + "<body>\n"
        + nav(active, github_url)
        + body_html
        + f"\n<script>{all_js}</script>\n"
        + "</body>\n</html>"
    )

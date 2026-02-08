"""Global CSS reset, typography, and responsive breakpoints."""


def css() -> str:
    return """
/* Reset */
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
html { scroll-behavior: smooth; }

/* Theme variables */
:root {
    /* Dark mode (default) */
    --bg-primary: #0B1120;
    --bg-secondary: #111827;
    --bg-card: #1E293B;
    --bg-code: #0D1117;
    --text-primary: #F1F5F9;
    --text-secondary: #94A3B8;
    --text-muted: #64748B;
    --accent-blue: #3B82F6;
    --accent-cyan: #06B6D4;
    --accent-green: #10B981;
    --border-color: #1E293B;
    --border-highlight: #334155;

    /* Font stacks */
    --font-display: 'JetBrains Mono', monospace;
    --font-body: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    --font-mono: 'JetBrains Mono', 'Consolas', monospace;

    /* Spacing */
    --space-xs: 0.25rem;
    --space-sm: 0.5rem;
    --space-md: 1rem;
    --space-lg: 1.5rem;
    --space-xl: 2rem;
    --space-2xl: 3rem;
    --space-3xl: 4rem;

    /* Layout */
    --max-width: 1200px;
    --nav-height: 64px;
}

/* Light mode */
[data-theme="light"] {
    --bg-primary: #F8FAFC;
    --bg-secondary: #F1F5F9;
    --bg-card: #FFFFFF;
    --bg-code: #F1F5F9;
    --text-primary: #0F172A;
    --text-secondary: #475569;
    --text-muted: #94A3B8;
    --border-color: #E2E8F0;
    --border-highlight: #CBD5E1;
}

body {
    font-family: var(--font-body);
    background: var(--bg-primary);
    color: var(--text-primary);
    line-height: 1.6;
    -webkit-font-smoothing: antialiased;
}

a { color: var(--accent-blue); text-decoration: none; transition: color 0.2s; }
a:hover { color: var(--accent-cyan); }

h1, h2, h3, h4 { font-family: var(--font-display); font-weight: 700; line-height: 1.2; }
h1 { font-size: 2.5rem; }
h2 { font-size: 1.75rem; }
h3 { font-size: 1.25rem; }

code, pre { font-family: var(--font-mono); }
pre {
    background: var(--bg-code);
    border: 1px solid var(--border-color);
    border-radius: 8px;
    padding: var(--space-md);
    overflow-x: auto;
    font-size: 0.875rem;
    line-height: 1.5;
}
code {
    background: var(--bg-code);
    padding: 0.125rem 0.375rem;
    border-radius: 4px;
    font-size: 0.875em;
}
pre code { background: none; padding: 0; }

img { max-width: 100%; height: auto; }

.container { max-width: var(--max-width); margin: 0 auto; padding: 0 var(--space-xl); }

.btn {
    display: inline-flex;
    align-items: center;
    gap: var(--space-sm);
    padding: 0.75rem 1.5rem;
    border-radius: 8px;
    font-family: var(--font-display);
    font-size: 0.875rem;
    font-weight: 600;
    text-decoration: none;
    transition: all 0.2s;
    cursor: pointer;
    border: none;
}
.btn-primary {
    background: var(--accent-blue);
    color: white;
}
.btn-primary:hover { background: #2563EB; color: white; }
.btn-secondary {
    background: transparent;
    color: var(--text-primary);
    border: 1px solid var(--border-highlight);
}
.btn-secondary:hover { border-color: var(--accent-blue); color: var(--accent-blue); }

/* Responsive */
@media (max-width: 768px) {
    h1 { font-size: 1.75rem; }
    h2 { font-size: 1.375rem; }
    .container { padding: 0 var(--space-md); }
}
"""

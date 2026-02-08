"""Documentation page with sidebar navigation and syntax highlighting."""

import html
import re
from pathlib import Path


def css() -> str:
    return """
.docs-layout {
    display: flex;
    min-height: calc(100vh - var(--nav-height));
}
.docs-sidebar {
    width: 260px;
    min-width: 260px;
    padding: var(--space-lg);
    background: var(--bg-secondary);
    border-right: 1px solid var(--border-color);
    position: sticky;
    top: var(--nav-height);
    height: calc(100vh - var(--nav-height));
    overflow-y: auto;
}
.docs-sidebar h3 {
    font-size: 0.75rem;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: var(--text-muted);
    margin-bottom: var(--space-sm);
    margin-top: var(--space-md);
}
.docs-sidebar h3:first-child { margin-top: 0; }
.docs-sidebar ul {
    list-style: none;
    margin-bottom: var(--space-md);
}
.docs-sidebar li a {
    display: block;
    padding: 0.25rem 0.5rem;
    font-size: 0.8125rem;
    color: var(--text-secondary);
    border-radius: 4px;
    transition: all 0.15s;
}
.docs-sidebar li a:hover {
    color: var(--text-primary);
    background: var(--bg-card);
}
.docs-sidebar li a.active {
    color: var(--accent-blue);
    background: rgba(59, 130, 246, 0.1);
}
.docs-content {
    flex: 1;
    padding: var(--space-2xl) var(--space-2xl);
    max-width: 900px;
}
.docs-content h1 {
    margin-bottom: var(--space-xl);
    padding-bottom: var(--space-md);
    border-bottom: 1px solid var(--border-color);
}
.docs-content h2 {
    margin-top: var(--space-2xl);
    margin-bottom: var(--space-md);
    padding-bottom: var(--space-sm);
    border-bottom: 1px solid var(--border-color);
}
.docs-content h3 {
    margin-top: var(--space-xl);
    margin-bottom: var(--space-sm);
    color: var(--accent-cyan);
}
.docs-content h4 {
    margin-top: var(--space-lg);
    margin-bottom: var(--space-sm);
}
.docs-content p {
    margin-bottom: var(--space-md);
    color: var(--text-secondary);
    line-height: 1.7;
}
.docs-content ul, .docs-content ol {
    margin-bottom: var(--space-md);
    padding-left: var(--space-xl);
    color: var(--text-secondary);
}
.docs-content li {
    margin-bottom: var(--space-xs);
    line-height: 1.6;
}
.docs-content table {
    width: 100%;
    border-collapse: collapse;
    margin-bottom: var(--space-lg);
    font-size: 0.875rem;
}
.docs-content th, .docs-content td {
    padding: 0.5rem 0.75rem;
    text-align: left;
    border: 1px solid var(--border-color);
}
.docs-content th {
    background: var(--bg-card);
    font-weight: 600;
}
.docs-content td { color: var(--text-secondary); }
.docs-content hr {
    border: none;
    border-top: 1px solid var(--border-color);
    margin: var(--space-xl) 0;
}
.docs-content strong { color: var(--text-primary); }
.open-in-editor {
    display: inline-flex;
    align-items: center;
    gap: 0.25rem;
    font-size: 0.75rem;
    color: var(--accent-blue);
    cursor: pointer;
    margin-left: 0.5rem;
    opacity: 0.7;
    transition: opacity 0.2s;
}
.open-in-editor:hover { opacity: 1; }

@media (max-width: 768px) {
    .docs-sidebar { display: none; }
    .docs-content { padding: var(--space-md); }
}
"""


def js() -> str:
    return """
// Sidebar active state tracking
(function() {
    document.addEventListener('DOMContentLoaded', function() {
        var headings = document.querySelectorAll('.docs-content h2, .docs-content h3');
        var links = document.querySelectorAll('.docs-sidebar a');

        function updateActive() {
            var scrollY = window.scrollY + 100;
            var current = '';
            headings.forEach(function(h) {
                if (h.offsetTop <= scrollY) current = h.id;
            });
            links.forEach(function(a) {
                a.classList.toggle('active', a.getAttribute('href') === '#' + current);
            });
        }

        window.addEventListener('scroll', updateActive);
        updateActive();
    });
})();
"""


def _slugify(text: str) -> str:
    """Convert heading text to URL-safe slug."""
    slug = text.lower().strip()
    slug = re.sub(r'[^a-z0-9\s-]', '', slug)
    slug = re.sub(r'[\s-]+', '-', slug)
    return slug


def _escape(text: str) -> str:
    return html.escape(text)


def _render_markdown(md_text: str) -> tuple[str, list[dict]]:
    """Convert markdown to HTML and extract headings for sidebar.

    Returns (html_content, headings) where headings is a list of
    {level, text, id} dicts.
    """
    lines = md_text.split('\n')
    out = []
    headings = []
    in_code = False
    code_lang = ''
    code_lines = []
    in_table = False
    table_rows = []
    in_list = False
    list_items = []

    def flush_list():
        nonlocal in_list, list_items
        if in_list and list_items:
            out.append('<ul>\n' + '\n'.join(list_items) + '\n</ul>')
            list_items = []
            in_list = False

    def flush_table():
        nonlocal in_table, table_rows
        if in_table and table_rows:
            header = table_rows[0]
            body = table_rows[2:]  # skip separator row
            cols = [c.strip() for c in header.split('|')[1:-1]]
            table_html = '<table><thead><tr>'
            for c in cols:
                table_html += f'<th>{_inline_format(c)}</th>'
            table_html += '</tr></thead><tbody>'
            for row in body:
                cells = [c.strip() for c in row.split('|')[1:-1]]
                table_html += '<tr>'
                for c in cells:
                    table_html += f'<td>{_inline_format(c)}</td>'
                table_html += '</tr>'
            table_html += '</tbody></table>'
            out.append(table_html)
            table_rows = []
            in_table = False

    for line in lines:
        # Code blocks
        if line.startswith('```'):
            if in_code:
                code_content = _escape('\n'.join(code_lines))
                lang_class = f' class="language-{code_lang}"' if code_lang else ''
                out.append(f'<pre><code{lang_class}>{code_content}</code></pre>')
                in_code = False
                code_lines = []
                code_lang = ''
            else:
                flush_list()
                flush_table()
                in_code = True
                code_lang = line[3:].strip()
            continue

        if in_code:
            code_lines.append(line)
            continue

        # Table detection
        if '|' in line and line.strip().startswith('|'):
            flush_list()
            if not in_table:
                in_table = True
            table_rows.append(line)
            continue
        else:
            flush_table()

        # Headings
        heading_match = re.match(r'^(#{1,4})\s+(.+)$', line)
        if heading_match:
            flush_list()
            level = len(heading_match.group(1))
            text = heading_match.group(2).strip()
            slug = _slugify(text)
            headings.append({'level': level, 'text': text, 'id': slug})
            out.append(f'<h{level} id="{slug}">{_inline_format(text)}</h{level}>')
            continue

        # Horizontal rule
        if re.match(r'^---+$', line.strip()):
            flush_list()
            out.append('<hr>')
            continue

        # List items
        if re.match(r'^[-*]\s', line.strip()):
            if not in_list:
                in_list = True
            content = re.sub(r'^[-*]\s', '', line.strip())
            list_items.append(f'<li>{_inline_format(content)}</li>')
            continue
        else:
            flush_list()

        # Empty line
        if not line.strip():
            continue

        # Paragraph
        out.append(f'<p>{_inline_format(line)}</p>')

    flush_list()
    flush_table()

    return '\n'.join(out), headings


def _inline_format(text: str) -> str:
    """Apply inline markdown formatting (bold, italic, code, links)."""
    # Code spans (do first to avoid processing inside code)
    text = re.sub(r'`([^`]+)`', r'<code>\1</code>', text)
    # Bold
    text = re.sub(r'\*\*([^*]+)\*\*', r'<strong>\1</strong>', text)
    # Italic
    text = re.sub(r'\*([^*]+)\*', r'<em>\1</em>', text)
    # Links
    text = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2">\1</a>', text)
    return text


def _build_sidebar(headings: list[dict]) -> str:
    """Build sidebar navigation from headings."""
    sidebar_html = ''
    current_section = None

    for h in headings:
        if h['level'] == 1:
            continue
        if h['level'] == 2:
            if current_section is not None:
                sidebar_html += '</ul>\n'
            sidebar_html += f'<h3>{_escape(h["text"])}</h3>\n<ul>\n'
            sidebar_html += f'<li><a href="#{h["id"]}">{_escape(h["text"])}</a></li>\n'
            current_section = h['text']
        elif h['level'] == 3:
            sidebar_html += f'<li><a href="#{h["id"]}">{_escape(h["text"])}</a></li>\n'

    if current_section is not None:
        sidebar_html += '</ul>\n'

    return sidebar_html


def generate_docs_html(docs_dir: Path, spec_path: Path) -> str:
    """Generate the documentation page content from markdown sources."""
    # Load markdown sources
    md_parts = []

    # Use library-reference.md as the primary source
    lib_ref = docs_dir / "library-reference.md"
    if lib_ref.exists():
        md_parts.append(lib_ref.read_text())

    # Fall back to cad-library-spec.md if no library-reference
    if not md_parts and spec_path.exists():
        md_parts.append(spec_path.read_text())

    md_text = '\n\n'.join(md_parts)
    # Rewrite internal doc links to site pages
    md_text = md_text.replace('./user-guide.md', '/editor.html')
    content_html, headings = _render_markdown(md_text)
    sidebar_html = _build_sidebar(headings)

    return f"""<div class="docs-layout">
    <aside class="docs-sidebar">
        {sidebar_html}
    </aside>
    <main class="docs-content">
        {content_html}
    </main>
</div>
"""

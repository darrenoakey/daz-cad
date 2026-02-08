"""Standalone editor page embedding."""


def css() -> str:
    return """
.editor-page {
    display: flex;
    flex-direction: column;
    min-height: calc(100vh - var(--nav-height));
}
.editor-frame {
    flex: 1;
    border: none;
    width: 100%;
    min-height: calc(100vh - var(--nav-height));
}
.editor-banner {
    background: var(--bg-secondary);
    border-bottom: 1px solid var(--border-color);
    padding: var(--space-sm) var(--space-xl);
    display: flex;
    align-items: center;
    justify-content: space-between;
    font-size: 0.8125rem;
    color: var(--text-secondary);
}
.editor-banner a { font-weight: 500; }
"""


def html_page() -> str:
    """Generate editor embed page content (loads standalone editor in iframe)."""
    return """<div class="editor-page">
    <div class="editor-banner">
        <span>daz-cad Standalone Editor</span>
        <span>
            Models saved to browser localStorage
        </span>
    </div>
    <iframe class="editor-frame" src="editor-standalone.html" title="daz-cad Editor"></iframe>
</div>
"""


def js() -> str:
    return """
// Pass URL parameters to editor iframe
(function() {
    document.addEventListener('DOMContentLoaded', function() {
        var iframe = document.querySelector('.editor-frame');
        if (iframe && window.location.search) {
            iframe.src = 'editor-standalone.html' + window.location.search;
        }
    });
})();
"""

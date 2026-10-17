"""Real-browser integration coverage for preview scheduling and pixel readback."""

from uuid import uuid4

import pytest


# ##################################################################
# preview page
# isolate this module from other browser tests and use the real CAD worker/server
@pytest.fixture(scope="module")
def preview_page(server, shared_browser):
    page = shared_browser.new_page()
    page.goto(server)
    page.wait_for_function(
        """() => window.cadEditor?.isReady && window.cadEditor._workerReady &&
            !window.cadEditor._isRendering && window.cadEditor.viewer.meshGroup.children.length > 0 &&
            document.getElementById('status-text')?.textContent === 'Ready'""",
        timeout=90000,
    )
    page.wait_for_function(
        """() => window.cadEditor._previewJobs.size === 0 &&
            window.cadEditor._fileMetadata.get(window.cadEditor._currentFile)?.thumbnail""",
        timeout=15000,
    )
    yield page
    page.close()


# ##################################################################
# unchanged source idle coalescing
# drive the production scheduler twice in one JS task, with real native idle
# callbacks, live rendered geometry and a real server PNG upload (not a BDD test)
def test_latest_unchanged_render_keeps_pending_thumbnail(preview_page):
    page = preview_page
    uploads = []

    def record_upload(request):
        if request.method == "PUT" and "/thumbnail?revision=" in request.url:
            uploads.append(request.url)

    page.on("request", record_upload)
    try:
        with page.expect_response(
            lambda response: response.request.method == "PUT" and "/thumbnail?revision=" in response.url,
            timeout=15000,
        ) as uploaded:
            state = page.evaluate(
                """async () => {
                    const editor = window.cadEditor;
                    const response = await fetch(`/api/models/${encodeURIComponent(editor._currentFile)}`);
                    if (!response.ok) throw new Error(`Source read failed: ${response.status}`);
                    const metadata = await response.json();
                    const source = {filename: editor._currentFile, content: editor.editor.getValue()};
                    if (source.content !== metadata.content) throw new Error('Rendered source is not saved');
                    const current = editor._renderRequestId;
                    // Both schedules run before the browser can dispatch its real idle callback.
                    editor._scheduleThumbnail(source, metadata, current - 1);
                    editor._scheduleThumbnail(source, metadata, current);
                    return {filename: source.filename, revision: metadata.revision};
                }"""
            )
        response = uploaded.value
        assert response.status == 200, response.text()
        assert response.json()["revision"] == state["revision"]
        assert response.json()["thumbnail"]
        page.wait_for_function("() => window.cadEditor._previewJobs.size === 0", timeout=15000)
        assert len(uploads) == 1, f"unchanged source should coalesce into one upload: {uploads}"
        assert f"/{state['filename']}/thumbnail" in uploads[0]
    finally:
        page.remove_listener("request", record_upload)


# ##################################################################
# unchanged rendered source
# a real source-save response with a cached thumbnail must not schedule work
# or re-upload the immutable PNG, even when the render completed again
def test_cached_unchanged_source_does_not_regenerate_thumbnail(preview_page):
    page = preview_page
    uploads = []

    def record_upload(request):
        if request.method == "PUT" and "/thumbnail?revision=" in request.url:
            uploads.append(request.url)

    page.on("request", record_upload)
    try:
        state = page.evaluate(
            """async () => {
                const editor = window.cadEditor;
                const url = `/api/models/${encodeURIComponent(editor._currentFile)}`;
                const before = await (await fetch(url)).json();
                if (!before.thumbnail) throw new Error('Expected a persisted preview');
                await editor._saveRenderedFile(
                    {filename: editor._currentFile, content: editor.editor.getValue()}, editor._renderRequestId
                );
                const after = await (await fetch(url)).json();
                return {before, after, pending: editor._previewJobs.size};
            }"""
        )
        assert state["before"] == state["after"]
        assert state["pending"] == 0
        assert uploads == []
    finally:
        page.remove_listener("request", record_upload)


# ##################################################################
# thumbnail color and alpha
# use real Three.js geometry, shader, render target, PNG encoding and decoding;
# a basic material removes lighting from the expected sRGB pixel values
@pytest.mark.parametrize("opacity, expected_alpha", [(1.0, 255), (0.5, 128)])
def test_thumbnail_preserves_srgb_and_straight_alpha(preview_page, opacity, expected_alpha):
    pixels = preview_page.evaluate(
        """async (opacity) => {
            const THREE = await import('three');
            const viewer = window.cadEditor.viewer;
            const originalGroup = viewer.meshGroup;
            viewer.meshGroup = new THREE.Group();
            const geometry = new THREE.BoxGeometry(20, 20, 20);
            const material = new THREE.MeshBasicMaterial({
                color: 0x808080, transparent: opacity < 1, opacity
            });
            viewer.meshGroup.add(new THREE.Mesh(geometry, material));
            try {
                const image = new Image();
                image.src = viewer.captureThumbnail();
                viewer.meshGroup = originalGroup;
                await image.decode();
                const canvas = document.createElement('canvas');
                canvas.width = canvas.height = 192;
                const context = canvas.getContext('2d');
                context.drawImage(image, 0, 0);
                return {
                    center: Array.from(context.getImageData(96, 96, 1, 1).data),
                    corner: Array.from(context.getImageData(0, 0, 1, 1).data)
                };
            } finally {
                viewer.meshGroup = originalGroup;
                geometry.dispose();
                material.dispose();
            }
        }""",
        opacity,
    )
    assert all(abs(channel - 128) <= 2 for channel in pixels["center"][:3]), pixels
    assert abs(pixels["center"][3] - expected_alpha) <= 1, pixels
    assert pixels["corner"] == [0, 0, 0, 0], pixels


# ##################################################################
# external-save snapshot interrupted by an edit
# reload a real saved model, immediately cancel that render with a newer edit,
# then verify its successful worker render POSTs the newer source to disk
# (the server fixture supplies an isolated temporary models directory)
def test_user_edit_after_external_save_snapshot_is_persisted(preview_page):
    page = preview_page
    filename = f"test-preview-snapshot-{uuid4().hex}.js"
    external = 'const result = new Workplane("XY").box(12, 14, 16);\nresult;'
    edited = 'const result = new Workplane("XY").box(18, 20, 22);\nresult;'
    page.evaluate(
        """async ({filename, content}) => {
            const response = await fetch(`/api/models/${filename}`, {
                method: 'POST', headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({content})
            });
            if (!response.ok) throw new Error(`Test source creation failed: ${response.status}`);
            await window.cadEditor._selectFile(filename);
        }""",
        {"filename": filename, "content": external},
    )
    page.wait_for_function(
        """filename => {
            const editor = window.cadEditor;
            return editor._currentFile === filename && !editor._isRendering &&
                editor._previewJobs.size === 0 && editor._fileMetadata.get(filename)?.thumbnail;
        }""",
        arg=filename,
        timeout=30000,
    )
    with page.expect_response(
        lambda response: response.request.method == "POST" and response.url.endswith(f"/api/models/{filename}"),
        timeout=30000,
    ) as saved:
        snapshot = page.evaluate(
            """async (edited) => {
                const editor = window.cadEditor;
                await editor._reloadCurrentFile();
                const snapshot = editor._skipSave;
                // One JS task prevents the old worker render from completing before this edit.
                editor.editor.setValue(edited);
                clearTimeout(editor.debounceTimer);
                editor.debounceTimer = null;
                editor._render();
                return snapshot;
            }""",
            edited,
        )
    assert snapshot == {"filename": filename, "content": external}
    assert saved.value.status == 200, saved.value.text()
    assert saved.value.request.post_data_json == {"content": edited}
    state = page.evaluate(
        """async filename => {
            const response = await fetch(`/api/models/${filename}`);
            if (!response.ok) throw new Error(`Saved source read failed: ${response.status}`);
            return {source: await response.json(), skipSave: window.cadEditor._skipSave};
        }""",
        filename,
    )
    assert state["source"]["content"] == edited
    assert state["skipSave"] is None

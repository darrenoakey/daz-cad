import hashlib
import os
import struct
import subprocess
import sys
import zlib
from pathlib import Path

import pytest

from src.model_preview import MAX_PNG_BYTES, ModelPreviews, model_path, validate_png


# ##################################################################
# png chunk
# build real checksummed image chunks for transparent test images
def png_chunk(kind, payload):
    return struct.pack('>I', len(payload)) + kind + payload + struct.pack('>I', zlib.crc32(kind + payload))


# ##################################################################
# transparent png
# two pixels include an opaque pixel and a transparent pixel, not a signature-only fixture
def transparent_png(width=2, height=1, pixels=None):
    pixels = pixels if pixels is not None else b'\0\x22\x44\x66\xff\0\0\0\0'
    header = struct.pack('>IIBBBBB', width, height, 8, 6, 0, 0, 0)
    return (b'\x89PNG\r\n\x1a\n' + png_chunk(b'IHDR', header)
            + png_chunk(b'IDAT', zlib.compress(pixels)) + png_chunk(b'IEND', b''))


# ##################################################################
# invalid png rejection
# exercise framing, checksums, dimensions, filters, exact inflation and bounded input
@pytest.mark.parametrize('data', [
    b'not png', transparent_png()[:-1], transparent_png() + b'trailing',
    transparent_png(width=1025), transparent_png(height=0), transparent_png(pixels=b'\0'),
    transparent_png(pixels=b'\5' + b'\0' * 8), transparent_png(pixels=b'\0' * 10000),
    b'\x89PNG\r\n\x1a\n' + b'\0' * MAX_PNG_BYTES,
    transparent_png()[:30] + b'\xff' + transparent_png()[31:],
], ids=['signature', 'truncated', 'trailing', 'width', 'height', 'scanline', 'filter', 'inflation', 'size', 'checksum'])
def test_reject_invalid_png(data):
    with pytest.raises(ValueError):
        validate_png(data)


# ##################################################################
# safe filenames
# avoid platform-specific separators, hidden files, extensions and symbolic-link escapes
@pytest.mark.parametrize('filename', ['../x.js', 'a\\x.js', '.hidden.js', 'model.txt', 'a\0.js', 'a\n.js'])
def test_reject_unsafe_model_names(tmp_path, filename):
    with pytest.raises(ValueError):
        model_path(tmp_path, filename)


# ##################################################################
# symbolic links
# preview operations cannot read source outside the model root through a link
def test_reject_source_symlink(tmp_path):
    outside = tmp_path / 'outside.js'
    outside.write_text('outside')
    root = tmp_path / 'models'
    root.mkdir()
    (root / 'link.js').symlink_to(outside)
    with pytest.raises(ValueError):
        model_path(root, 'link.js')


# ##################################################################
# exercise real application
# invoked in separate interpreters to isolate module configuration and verify restart durability
# no lifespan is run: the test creates its own source root and does not need git, watcher or chat
def exercise_application(root_string, phase):
    from fastapi.testclient import TestClient

    from src.server import MODELS_DIR, app

    root = Path(root_string)
    assert MODELS_DIR == root
    root.mkdir(parents=True, exist_ok=True)
    filename = "part space ☃.js"
    source = root / filename
    original = b"const result = box(2, 3, 4);"
    revision = hashlib.sha256(original).hexdigest()
    url = f"/api/models/{filename}"
    image_url = f"{url}/thumbnail?revision={revision}"
    image = transparent_png()
    client = TestClient(app)
    try:
        if phase == "first":
            source.write_bytes(original)
            for invalid_name in ['old\\part.js', '.hidden.js', 'line\nfeed.js']:
                (root / invalid_name).write_text('legacy invalid filename')
            (root / 'directory.js').mkdir()
            listing = client.get('/api/models')
            assert listing.status_code == 200, listing.text
            assert filename in listing.json()['files']
            assert all(name not in listing.json()['files'] for name in
                       ['old\\part.js', '.hidden.js', 'line\nfeed.js', 'directory.js'])
            stamp = source.stat().st_mtime_ns
            metadata = client.get(url).json()
            assert metadata["revision"] == revision
            assert metadata["thumbnail"] is None
            saved = client.post(url, json={"content": original.decode()}).json()
            assert saved["revision"] == revision and saved["thumbnail"] is None
            assert source.stat().st_mtime_ns == stamp
            assert client.put(image_url, content=b"not PNG", headers={"Content-Type": "image/png"}).status_code == 400
            assert client.put(image_url, content=image).status_code == 415
            oversized = b"x" * (MAX_PNG_BYTES + 1)
            assert client.put(image_url, content=oversized, headers={"Content-Type": "image/png"}).status_code == 413
            uploaded = client.put(image_url, content=image, headers={"Content-Type": "image/png"})
            assert uploaded.status_code == 200, uploaded.text
            assert uploaded.json()["thumbnail"]
            assert client.get(uploaded.json()["thumbnail"]).content == image
            cached = ModelPreviews(root).path(revision)
            cache_stamp = cached.stat().st_mtime_ns
            # An equally valid later image must not replace an immutable revision.
            another = transparent_png(pixels=b"\0" + b"\xff" * 8)
            assert client.put(image_url, content=another, headers={"Content-Type": "image/png"}).status_code == 200
            assert cached.read_bytes() == image
            assert cached.stat().st_mtime_ns == cache_stamp
            unchanged = client.post(url, json={"content": original.decode()}).json()
            assert unchanged["thumbnail"] == uploaded.json()["thumbnail"]
            assert source.stat().st_mtime_ns == stamp
            changed_source = original.decode() + " // saved change"
            modified = client.post(url, json={"content": changed_source}).json()
            assert modified["saved"] is True and modified["thumbnail"] is None
            assert modified["revision"] == hashlib.sha256(changed_source.encode()).hexdigest()
            assert source.read_text() == changed_source and source.stat().st_mtime_ns != stamp
            restored = client.post(url, json={"content": original.decode()}).json()
            assert restored["revision"] == revision and restored["thumbnail"]
        elif phase == "restart":
            metadata = client.get(url).json()
            assert metadata["revision"] == revision and metadata["thumbnail"]
            assert client.get(metadata["thumbnail"]).content == image
            listed = client.get("/api/models").json()
            assert filename in listed["files"]
            assert next(row for row in listed["models"] if row["filename"] == filename) == metadata_without_content(metadata)
            old_stamp = source.stat()
            source.write_bytes(original + b" // external edit")
            os.utime(source, ns=(old_stamp.st_atime_ns, old_stamp.st_mtime_ns))
            changed = client.get(url).json()
            assert changed["revision"] != revision and changed["thumbnail"] is None
            assert client.put(image_url, content=image, headers={"Content-Type": "image/png"}).status_code == 409
            stale = client.get(image_url)
            assert stale.content == image and "immutable" in stale.headers["Cache-Control"]
            source.write_bytes(original)
            assert client.get(url).json()["thumbnail"] == metadata["thumbnail"]
        else:
            raise ValueError(f"Unknown test phase: {phase}")
        assert client.get("/api/models/wrong.txt").status_code == 400
        assert client.post("/api/models/wrong.txt", json={"content": "x"}).status_code == 400
        assert client.get("/api/models/missing.js").status_code == 404
        assert client.get(f"{url}/thumbnail?revision=../../x").status_code == 400
        assert client.put("/api/models/missing.js/thumbnail?revision=" + revision,
                          content=image, headers={"Content-Type": "image/png"}).status_code == 404
        assert not (root / "model-previews").exists()
    finally:
        client.close()


# ##################################################################
# metadata without content
# compare the model list contract to the source-read contract without its source payload
def metadata_without_content(metadata):
    return {key: value for key, value in metadata.items() if key != "content"}


# ##################################################################
# application restart
# fresh app imports and clients use the same isolated disk store, never production data
def test_http_persistence_and_restart(tmp_path):
    root = tmp_path / 'models'
    project = Path(__file__).resolve().parent.parent
    for phase in ('first', 'restart'):
        result = subprocess.run(
            [sys.executable, '-c',
             ('import sys; from src.model_preview_test import exercise_application; '
              'exercise_application(sys.argv[1], sys.argv[2])'), str(root), phase],
            check=False, cwd=project, env={**os.environ, 'DAZCAD_MODELS_DIR': str(root)},
            capture_output=True, text=True, timeout=30,
        )
        assert result.returncode == 0, result.stdout + result.stderr


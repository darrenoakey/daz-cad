import hashlib
import os
import re
import struct
import tempfile
import zlib
from pathlib import Path
from urllib.parse import quote

MAX_PNG_BYTES = 1024 * 1024
MAX_DIMENSION = 1024
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


# ##################################################################
# model path
# reject aliases and symbolic links instead of silently changing a requested name
def model_path(root: Path, filename: str) -> Path:
    if (not filename.endswith('.js') or filename.startswith('.')
            or any(c in filename for c in '/\\\x00') or any(ord(c) < 32 for c in filename)):
        raise ValueError(f"Invalid model filename: {filename!r}")
    path = root / filename
    if path.is_symlink() or (path.exists() and not path.is_file()):
        raise ValueError(f"Not a regular model file: {filename!r}")
    return path


# ##################################################################
# source revision
# hash exact source bytes so external edits invalidate previews even with unchanged mtime
def source_revision(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


# ##################################################################
# validate png
# accept bounded noninterlaced eight-bit RGBA canvas PNGs, checking framing and inflation
# without invoking a general-purpose image parser or allowing decompression bombs
def validate_png(data: bytes) -> None:
    if len(data) > MAX_PNG_BYTES or not data.startswith(PNG_SIGNATURE):
        raise ValueError(f"Invalid PNG signature or size: {len(data)} bytes")
    offset, width, height = 8, 0, 0
    compressed = bytearray()
    ended = False
    idat_ended = False
    seen_idat = False
    while offset < len(data):
        if offset + 12 > len(data):
            raise ValueError(f"Truncated PNG chunk at {offset}")
        length = int.from_bytes(data[offset:offset + 4], 'big')
        kind = data[offset + 4:offset + 8]
        end = offset + length + 12
        if end > len(data):
            raise ValueError(f"Truncated PNG {kind!r} chunk")
        payload = data[offset + 8:end - 4]
        crc = int.from_bytes(data[end - 4:end], 'big')
        if zlib.crc32(kind + payload) != crc:
            raise ValueError(f"PNG checksum mismatch for {kind!r}")
        if offset == 8:
            if kind != b'IHDR' or length != 13:
                raise ValueError(f"PNG must begin with IHDR, got {kind!r}")
            width, height, depth, color, compression, filtering, interlace = struct.unpack('>IIBBBBB', payload)
            if not (0 < width <= MAX_DIMENSION and 0 < height <= MAX_DIMENSION):
                raise ValueError(f"PNG dimensions out of bounds: {width}x{height}")
            if (depth, color, compression, filtering, interlace) != (8, 6, 0, 0, 0):
                raise ValueError(f"PNG must be noninterlaced eight-bit RGBA: {depth}, {color}")
        elif kind == b'IDAT':
            if idat_ended:
                raise ValueError(f"Noncontiguous PNG data at {offset}")
            seen_idat = True
            compressed.extend(payload)
        elif kind == b'IEND':
            if length or end != len(data) or not seen_idat:
                raise ValueError(f"Invalid PNG end at {offset}")
            ended = True
        elif kind in (b'PLTE', b'IHDR') or not kind[0] & 32:
            raise ValueError(f"Unsupported PNG chunk: {kind!r}")
        elif seen_idat:
            idat_ended = True
        offset = end
    if not ended:
        raise ValueError(f"PNG has no end chunk: {len(data)} bytes")
    expected = height * (1 + width * 4)
    decoder = zlib.decompressobj()
    try:
        pixels = decoder.decompress(compressed, expected + 1)
    except zlib.error as error:
        raise ValueError(f"Invalid PNG compressed data: {error}") from error
    if len(pixels) != expected or not decoder.eof or decoder.unused_data or decoder.unconsumed_tail:
        raise ValueError(f"Invalid PNG scanline size: expected {expected}, got {len(pixels)}")
    if any(pixels[row * (1 + width * 4)] > 4 for row in range(height)):
        raise ValueError(f"Invalid PNG scanline filter for {width}x{height}")


# ##################################################################
# preview store
# immutable source-addressed files live outside the models git repository
class ModelPreviews:
    # ##################################################################
    # initialize store
    # constructing a reader must not create runtime files
    def __init__(self, models_root: Path):
        self.models_root = models_root
        self.root = models_root.parent / 'model-previews'

    # ##################################################################
    # preview path
    # validate revision before using it as a disk name
    def path(self, revision: str) -> Path:
        if not re.fullmatch(r'[0-9a-f]{64}', revision):
            raise ValueError(f"Invalid source revision: {revision!r}")
        return self.root / f'{revision}.png'

    # ##################################################################
    # metadata
    # always rehash source rather than trusting timestamps or in-memory state
    def metadata(self, filename: str, content: bytes | None = None) -> dict:
        path = model_path(self.models_root, filename)
        revision = source_revision(path.read_bytes() if content is None else content)
        url = f'/api/models/{quote(filename, safe="")}/thumbnail?revision={revision}'
        return {'filename': filename, 'mtime': path.stat().st_mtime, 'revision': revision,
                'thumbnail': url if self.path(revision).is_file() else None}

    # ##################################################################
    # store png
    # publish atomically and never replace an existing immutable revision
    def put(self, revision: str, data: bytes) -> None:
        target = self.path(revision)
        validate_png(data)
        self.root.mkdir(parents=True, exist_ok=True)
        descriptor, name = tempfile.mkstemp(dir=self.root, prefix='.preview-')
        try:
            with os.fdopen(descriptor, 'wb') as stream:
                stream.write(data)
            try:
                os.link(name, target)
            except FileExistsError:
                pass
        finally:
            Path(name).unlink(missing_ok=True)

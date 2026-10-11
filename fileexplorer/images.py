"""Bounded raster-image reads; decoding and display remain in Steam's browser."""
import base64
import io
import os
import stat
import struct

from .vfs import split

LIMIT = 20 * 1024 * 1024
MAX_PIXELS = 40_000_000


class LimitedBuffer(io.BytesIO):
    def write(self, value):
        if self.tell() + len(value) > LIMIT:
            raise ValueError('Image preview supports files up to 20 MiB.')
        return super().write(value)


def read(fs, location):
    key, path = split(location)
    if not key:
        # Reject links and special files even if the path changed since listing.
        fd = os.open(path, os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW)
        with os.fdopen(fd, 'rb') as source:
            info = os.fstat(source.fileno())
            if not stat.S_ISREG(info.st_mode): raise ValueError('Open a regular image file.')
            if info.st_size > LIMIT: raise ValueError('Image preview supports files up to 20 MiB.')
            raw = source.read(LIMIT + 1)
    else:
        info = fs.info(location)
        if info['directory'] or info['link']: raise ValueError('Open a regular image file.')
        if info['size'] > LIMIT: raise ValueError('Image preview supports files up to 20 MiB.')
        output = LimitedBuffer()
        fs.read_to(location, output, lambda *_: None)
        raw = output.getvalue()
    return describe(raw)


def dimensions(raw):
    if raw.startswith(b'\x89PNG\r\n\x1a\n') and len(raw) >= 33 and raw[12:16] == b'IHDR':
        return 'image/png', *struct.unpack('>II', raw[16:24])
    if raw[:6] in (b'GIF87a', b'GIF89a') and len(raw) >= 13:
        return 'image/gif', *struct.unpack('<HH', raw[6:10])
    if raw.startswith(b'BM') and len(raw) >= 26:
        header = int.from_bytes(raw[14:18], 'little')
        if header == 12: width, height = struct.unpack('<HH', raw[18:22])
        elif header >= 40 and len(raw) >= 14 + header:
            width, height = struct.unpack('<ii', raw[18:26]); height = abs(height)
        else: raise ValueError('Unsupported BMP header.')
        return 'image/bmp', width, height
    if raw.startswith(b'\xff\xd8'):
        offset = 2
        while offset < len(raw):
            if raw[offset] != 255: break
            while offset < len(raw) and raw[offset] == 255: offset += 1
            if offset >= len(raw): break
            marker = raw[offset]; offset += 1
            if marker in (0xda, 0xd9): break
            if marker in (0x01, *range(0xd0, 0xd9)): continue
            length = int.from_bytes(raw[offset:offset + 2], 'big')
            if length < 2 or offset + length > len(raw): break
            if marker in (0xc0, 0xc1, 0xc2, 0xc3, 0xc5, 0xc6, 0xc7, 0xc9, 0xca, 0xcb, 0xcd, 0xce, 0xcf) and length >= 8:
                height, width = struct.unpack('>HH', raw[offset + 3:offset + 7])
                return 'image/jpeg', width, height
            offset += length
    if raw.startswith(b'RIFF') and raw[8:12] == b'WEBP':
        offset = 12
        while offset + 8 <= len(raw):
            kind = raw[offset:offset + 4]
            size = int.from_bytes(raw[offset + 4:offset + 8], 'little')
            payload = raw[offset + 8:offset + 8 + size]
            if len(payload) != size: break
            if kind == b'VP8X' and size >= 10:
                return 'image/webp', 1 + int.from_bytes(payload[4:7], 'little'), 1 + int.from_bytes(payload[7:10], 'little')
            if kind == b'VP8L' and size >= 5 and payload[0] == 0x2f:
                bits = int.from_bytes(payload[1:5], 'little')
                return 'image/webp', 1 + (bits & 0x3fff), 1 + ((bits >> 14) & 0x3fff)
            if kind == b'VP8 ' and size >= 10 and payload[3:6] == b'\x9d\x01\x2a':
                width, height = struct.unpack('<HH', payload[6:10])
                return 'image/webp', width & 0x3fff, height & 0x3fff
            offset += 8 + size + (size % 2)
    raise ValueError('This file is not a supported BMP, PNG, JPEG, GIF or WebP image, or its header is damaged.')


def describe(raw):
    if len(raw) > LIMIT: raise ValueError('Image preview supports files up to 20 MiB.')
    mime, width, height = dimensions(raw)
    if not 0 < width <= 16384 or not 0 < height <= 16384 or width * height > MAX_PIXELS:
        raise ValueError('Image preview supports up to 40 megapixels and 16,384 pixels per side.')
    return dict(mime=mime, width=width, height=height, size=len(raw),
                data='data:' + mime + ';base64,' + base64.b64encode(raw).decode('ascii'))

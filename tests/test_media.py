import base64
from concurrent.futures import ThreadPoolExecutor
import http.client
import io
import os
from pathlib import Path
import sys
import tempfile
import shutil
import unittest
from unittest.mock import patch
from urllib.parse import urlsplit
import wave

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'vendor')]
from fileexplorer.media import Media, TagReader, Source, byte_range, cover


class MediaTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / 'sample.wav'
        with wave.open(str(self.path), 'wb') as output:
            output.setnchannels(1); output.setsampwidth(2); output.setframerate(8000)
            output.writeframes(b'\x01\x02' * 16000)
        self.raw = self.path.read_bytes()
        self.media = Media()

    def tearDown(self):
        self.media.shutdown(); self.temp.cleanup()

    def request(self, stream, headers=None, method='GET', path=None):
        url = urlsplit(stream['url'])
        conn = http.client.HTTPConnection(url.hostname, url.port, timeout=3)
        try:
            conn.request(method, path or url.path, headers=headers or {})
            response = conn.getresponse()
            return response.status, dict(response.getheaders()), response.read()
        finally: conn.close()

    def test_stream_head_ranges_and_revocation(self):
        result = self.media.open(str(self.path), {})
        self.assertIsNone(result['cover'])
        self.assertEqual(self.media.server.server_address[0], '127.0.0.1')
        status, headers, raw = self.request(result)
        self.assertEqual((status, raw), (200, self.raw))
        self.assertEqual(headers['Content-Type'], 'audio/wav')
        self.assertEqual(self.request(result, method='HEAD')[2], b'')
        for requested, start, end in [('bytes=8-20', 8, 20), ('bytes=32000-', 32000, len(self.raw)-1), ('bytes=-17', len(self.raw)-17, len(self.raw)-1)]:
            status, headers, raw = self.request(result, {'Range': requested})
            self.assertEqual((status, raw), (206, self.raw[start:end+1]))
            self.assertEqual(headers['Content-Range'], f'bytes {start}-{end}/{len(self.raw)}')
        self.media.close(result['token'])
        self.assertEqual(self.request(result)[0], 404)

    def test_refuses_paths_host_rebinding_and_bad_ranges(self):
        result = self.media.open(str(self.path), {})
        for path in ['/etc/passwd', '/' + result['token'] + '?path=/etc/passwd', '/bogus']:
            self.assertEqual(self.request(result, path=path)[0], 404)
        self.assertEqual(self.request(result, {'Host': 'attacker.invalid'})[0], 403)
        for value in ['bytes=999999-', 'bytes=-0', 'bytes=12-8', 'bytes=0-2,8-9', 'bytes=bad', 'items=0-2']:
            self.assertEqual(self.request(result, {'Range': value})[0], 416)

    def test_concurrent_seek_reads_are_independent(self):
        self.path.write_bytes(bytes(range(256)) * 10000)
        result = self.media.open(str(self.path), {})
        with ThreadPoolExecutor(max_workers=4) as pool:
            futures = [pool.submit(self.request, result, {'Range': f'bytes={i*1024}-{i*1024+255}'}) for i in range(12)]
            for future in futures: self.assertEqual(future.result()[2], bytes(range(256)))

    def test_empty_special_links_and_unknown_formats(self):
        for name in ['test.exe', 'test.txt']:
            with self.assertRaises(ValueError): self.media.open(str(self.path.with_name(name)), {})
        empty = self.path.with_name('empty.mp3'); empty.touch()
        with self.assertRaisesRegex(ValueError, 'empty'): self.media.open(str(empty), {})
        link = self.path.with_name('link.wav'); link.symlink_to(self.path)
        with self.assertRaises(OSError): self.media.open(str(link), {})
        fifo = self.path.with_name('pipe.wav'); os.mkfifo(fifo)
        with self.assertRaisesRegex(ValueError, 'regular'): self.media.open(str(fifo), {})
        with self.assertRaisesRegex(ValueError, 'Extract'): self.media.open('archive://test', {})

    def test_embedded_cover_and_budget(self):
        image = (ROOT / 'tests/fixtures/images/sample.png').read_bytes()
        payload = b'\0image/png\0\x03\0' + image
        frame = b'APIC' + len(payload).to_bytes(4, 'big') + b'\0\0' + payload
        length = bytes((len(frame) >> shift) & 127 for shift in (21, 14, 7, 0))
        tag = b'ID3\x03\0\0' + length + frame
        raw = bytearray(self.raw + b'id3 ' + len(tag).to_bytes(4, 'little') + tag + b'\0' * (len(tag) % 2))
        raw[4:8] = (len(raw) - 8).to_bytes(4, 'little')
        self.path.write_bytes(raw)
        result = self.media.open(str(self.path), {})
        self.assertEqual(base64.b64decode(result['cover'].split(',')[1]), image)
        source = Source(str(self.path), {})
        try:
            reader = TagReader(source, None); reader.budget = 4
            with self.assertRaisesRegex(ValueError, 'budget'): reader.read(5)
            with patch('fileexplorer.media.TAG_BUDGET', 1): self.assertIsNone(cover(source))
        finally: source.close()

    def test_replaced_path_does_not_change_open_file(self):
        result = self.media.open(str(self.path), {})
        self.path.unlink(); self.path.write_bytes(b'changed')
        self.assertEqual(self.request(result)[2], self.raw)

    def test_expiry_and_session_limit(self):
        results = [self.media.open(str(self.path), {}) for _ in range(4)]
        with self.assertRaisesRegex(ValueError, 'Close another'): self.media.open(str(self.path), {})
        with patch('fileexplorer.media.TTL', -1):
            self.assertEqual(self.request(results[0])[0], 404)
        self.assertEqual(self.media.sessions, {})

    @unittest.skipUnless(shutil.which('ffmpeg') and shutil.which('ffprobe'), 'System FFmpeg required')
    def test_compatibility_stream_and_seek(self):
        result = self.media.open(str(self.path), {})
        self.assertAlmostEqual(result['duration'], 2, places=1)
        base = '/' + result['token'] + '/compat'
        for query in ['?start=-1', '?start=nan', '?start=inf', '?start=604800', '?path=/etc/passwd']:
            self.assertEqual(self.request(result, path=base + query)[0], 400)
        for start in (0, 1):
            status, headers, data = self.request(result, path=base + f'?start={start}&revision=1')
            self.assertEqual(status, 200)
            self.assertEqual(headers['Content-Type'], 'audio/webm')
            self.assertTrue(data.startswith(b'\x1aE\xdf\xa3'), data[:100])
            self.assertGreater(len(data), 100)
        self.media.close(result['token'])
        self.assertEqual(self.request(result, path=base)[0], 404)

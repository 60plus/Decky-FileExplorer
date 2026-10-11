import base64
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fileexplorer import archive, images
from fileexplorer.service import Service

FIXTURES = Path(__file__).parent / 'fixtures/images'


class ImageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.service = Service(self.root, self.root / 'settings')

    def tearDown(self):
        self.service.shutdown(); self.temp.cleanup()

    def test_raster_formats_preserve_original_bytes_and_dimensions(self):
        for name, mime in [('sample.png','image/png'),('sample.jpg','image/jpeg'),('sample.bmp','image/bmp'),('sample.gif','image/gif'),('sample.webp','image/webp')]:
            with self.subTest(name=name):
                result = self.service.image(str(FIXTURES / name))
                self.assertEqual(result['mime'], mime)
                self.assertEqual((result['width'], result['height']), (32, 24))
                self.assertEqual(base64.b64decode(result['data'].split(',', 1)[1]), (FIXTURES / name).read_bytes())

    def test_content_detection_and_invalid_headers(self):
        disguised = self.root / 'wrong.jpg'
        disguised.write_bytes((FIXTURES / 'sample.png').read_bytes())
        self.assertEqual(self.service.image(str(disguised))['mime'], 'image/png')
        for raw in (b'', b'<svg xmlns="http://www.w3.org/2000/svg"/>', b'\xff\xd8\xff', b'BM'+b'\0'*30, b'RIFF'+b'\0'*4+b'WEBP'):
            with self.subTest(raw=raw), self.assertRaises(ValueError): images.describe(raw)

    def test_byte_and_dimension_limits_before_decode(self):
        large = self.root / 'large.png'
        with large.open('wb') as f: f.truncate(images.LIMIT + 1)
        with self.assertRaisesRegex(ValueError, '20 MiB'): self.service.image(str(large))
        raw = bytearray((FIXTURES / 'sample.png').read_bytes())
        for width, height in ((0, 1), (16385, 1), (10000, 10000)):
            raw[16:24] = width.to_bytes(4, 'big') + height.to_bytes(4, 'big')
            with self.assertRaisesRegex(ValueError, 'megapixels'): images.describe(bytes(raw))

    def test_growing_remote_image_is_bounded(self):
        class Remote:
            def info(self, _): return dict(directory=False, link=False, size=1)
            def read_to(self, _, output, progress):
                output.write(b'a'*40); output.write(b'b'*40)
        with patch.object(images, 'LIMIT', 64), self.assertRaisesRegex(ValueError, '20 MiB'):
            images.read(Remote(), 'smb://test/growing.png')

    def test_links_and_special_files_are_refused(self):
        link = self.root / 'link.png'; link.symlink_to(FIXTURES / 'sample.png')
        with self.assertRaises(OSError): self.service.image(str(link))
        fifo = self.root / 'pipe.png'; os.mkfifo(fifo)
        with self.assertRaisesRegex(ValueError, 'regular'): self.service.image(str(fifo))

    def test_archive_preview_extracts_only_selected_member_and_cleans_up(self):
        path = self.root / 'pictures.zip'
        raw = (FIXTURES / 'sample.png').read_bytes()
        with zipfile.ZipFile(path, 'w') as z:
            z.writestr('photos/picture.png', raw)
            z.writestr('unselected.bin', b'x' * (len(raw) + 1))
        with patch.object(images, 'LIMIT', len(raw)):
            result = self.service.image(archive.location(str(path), 'photos/picture.png'))
        self.assertEqual(base64.b64decode(result['data'].split(',', 1)[1]), raw)
        self.assertFalse(list(self.service.settings_dir.glob('.fileexplorer-image-*')))
        with self.assertRaisesRegex(ValueError, 'not found'): self.service.image(archive.location(str(path), 'missing.png'))
        with patch.object(images, 'LIMIT', len(raw)-1), self.assertRaisesRegex(ValueError, '20 MiB'):
            self.service.image(archive.location(str(path), 'photos/picture.png'))

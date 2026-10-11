import codecs
import json
import os
import tempfile
import unittest
from pathlib import Path

from fileexplorer import editor
from fileexplorer.vfs import VFS


class EditorTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.fs = VFS({})

    def tearDown(self): self.temp.cleanup()

    def test_unchanged_text_roundtrips_byte_for_byte(self):
        for codec, bom in [('utf-8', b''), ('utf-8', codecs.BOM_UTF8), ('utf-16-le', codecs.BOM_UTF16_LE), ('utf-16-be', codecs.BOM_UTF16_BE), ('cp1250', b'')]:
            p = self.root / 'config.cfg'
            raw = bom + '\tżółw = 3  \r\n\r\nnext=true\n# end'.encode(codec)
            p.write_bytes(raw)
            state = editor.read(self.fs, str(p), codec)
            editor.save(self.fs, str(p), state['text'], state['revision'], state['encoding'])
            self.assertEqual(p.read_bytes(), raw)

    def test_edit_keeps_mixed_eol_whitespace_and_final_newline(self):
        p = self.root / 'settings.cfg'
        p.write_bytes(b'\talpha=1  \r\n\r\nbeta=2\nlast=3\r')
        state = editor.read(self.fs, str(p))
        editor.save(self.fs, str(p), state['text'].replace('beta=2', 'beta=42'), state['revision'])
        self.assertEqual(p.read_bytes(), b'\talpha=1  \r\n\r\nbeta=42\nlast=3\r')

    def test_json_validates_without_reserializing(self):
        p = self.root / 'a.json'
        original = b'{\r\n\t"x" : 1,  \r\n  "name": "hello"\r\n}\r\n'
        p.write_bytes(original)
        state = editor.read(self.fs, str(p))
        with self.assertRaisesRegex(ValueError, 'Invalid JSON at line'):
            editor.save(self.fs, str(p), '{\n broken', state['revision'])
        self.assertEqual(p.read_bytes(), original)
        editor.save(self.fs, str(p), state['text'].replace('"x" : 1', '"x" : 2'), state['revision'])
        self.assertEqual(p.read_bytes(), original.replace(b'"x" : 1', b'"x" : 2'))
        self.assertEqual(json.loads(p.read_bytes())['x'], 2)

    def test_conflict_does_not_overwrite_external_changes(self):
        p = self.root / 'file.txt'; p.write_text('original')
        state = editor.read(self.fs, str(p)); p.write_text('changed elsewhere')
        with self.assertRaisesRegex(ValueError, 'changed outside'):
            editor.save(self.fs, str(p), 'my edit', state['revision'])
        self.assertEqual(p.read_text(), 'changed elsewhere')

    def test_legacy_encoding_and_unrepresentable_characters(self):
        p = self.root / 'legacy.cfg'; raw = 'żółw=3\r\n'.encode('cp1250'); p.write_bytes(raw)
        with self.assertRaises(ValueError): editor.read(self.fs, str(p))
        state = editor.read(self.fs, str(p), 'cp1250')
        with self.assertRaisesRegex(ValueError, 'original encoding'):
            editor.save(self.fs, str(p), state['text'] + '😀', state['revision'], 'cp1250')
        self.assertEqual(p.read_bytes(), raw)
        editor.save(self.fs, str(p), state['text'].replace('3', '4'), state['revision'], 'cp1250')
        self.assertEqual(p.read_bytes(), 'żółw=4\r\n'.encode('cp1250'))

    def test_binary_and_oversize_refused(self):
        p = self.root / 'binary'; p.write_bytes(b'hi\0data')
        with self.assertRaises(ValueError): editor.read(self.fs, str(p))
        p.write_bytes(b'a' * (editor.LIMIT + 1))
        with self.assertRaises(ValueError): editor.read(self.fs, str(p))

    def test_invalid_edited_content_is_rejected_before_writing(self):
        p = self.root / 'config.cfg'; p.write_bytes(b'original\r\n')
        state = editor.read(self.fs, str(p))
        for invalid in ['text\0binary', 'a\n' * 10000]:
            with self.assertRaises(ValueError): editor.save(self.fs, str(p), invalid, state['revision'])
            self.assertEqual(p.read_bytes(), b'original\r\n')

    @unittest.skipUnless(os.name == 'posix', 'Linux file modes')
    def test_save_keeps_file_permissions(self):
        p = self.root / 'private.txt'; p.write_text('old'); p.chmod(0o640)
        state = editor.read(self.fs, str(p))
        editor.save(self.fs, str(p), 'new', state['revision'])
        self.assertEqual(p.stat().st_mode & 0o777, 0o640)


if __name__ == '__main__': unittest.main()

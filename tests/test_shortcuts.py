import os
from pathlib import Path
import tempfile
import unittest
from fileexplorer import shortcuts


class ShortcutTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.root = Path(self.temp.name)
    def tearDown(self): self.temp.cleanup()

    def test_prepare_does_not_execute_script_and_quotes_spaces(self):
        path = self.root/'game launch.sh'; sentinel = self.root/'ran'
        path.write_text('#!/bin/sh\ntouch "' + str(sentinel) + '"\n')
        result = shortcuts.prepare(str(path))
        self.assertIn('/sh"', result['executable'])
        self.assertEqual(result['arguments'], '"' + str(path) + '"')
        self.assertFalse(sentinel.exists())
        self.assertFalse(result['needs_execute'])

    def test_windows_target_is_added_as_selected(self):
        for suffix in ('exe', 'com', 'bat', 'cmd'):
            path = self.root/('demo.' + suffix); path.write_bytes(b'MZdemo')
            result = shortcuts.prepare(str(path))
            self.assertEqual(result['executable'], '"' + str(path) + '"')
            self.assertTrue(result['windows']); self.assertFalse(result['needs_execute'])

    def test_native_permission_requires_explicit_selection(self):
        path = self.root/'Demo.AppImage'; path.write_bytes(b'\x7fELFtest'); path.chmod(0o644)
        self.assertTrue(shortcuts.prepare(str(path))['needs_execute'])
        self.assertFalse(path.stat().st_mode & 0o100)
        self.assertFalse(shortcuts.prepare(str(path), True)['needs_execute'])
        self.assertTrue(path.stat().st_mode & 0o100)

    def test_unknown_remote_and_ambiguous_paths_are_rejected(self):
        for name in ('plain.txt', 'bad"name.sh', 'bad$name.sh'):
            path = self.root/name; path.write_text('test')
            with self.assertRaises(ValueError): shortcuts.prepare(str(path))
        with self.assertRaisesRegex(ValueError, 'local'): shortcuts.prepare('smb://test/game.exe')
        with self.assertRaises(ValueError): shortcuts.prepare(str(self.root))

    def test_folder_uses_executable_parent_then_working_or_install_folder(self):
        sub = self.root/'game'; sub.mkdir(); exe = sub/'play.exe'; exe.write_bytes(b'MZ')
        self.assertEqual(shortcuts.game_folder('"'+str(exe)+'"', str(self.root))['path'], str(sub))
        self.assertEqual(shortcuts.game_folder('/usr/bin/bash', str(sub))['path'], str(sub))
        self.assertEqual(shortcuts.game_folder(install_dir=str(sub))['path'], str(sub))
        with self.assertRaises(ValueError): shortcuts.game_folder(install_dir=str(self.root/'missing'))


if __name__ == '__main__': unittest.main()

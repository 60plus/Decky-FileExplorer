import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fileexplorer import credentials
from fileexplorer.service import PROFILES, Service

SHARED = dict(opacity=100, text_size=14, show_hidden=True, folders_first=True, remember_paths=True,
              check_updates_on_start=True, sort_by='name', splash_enabled=False)
HANDHELD = dict(SHARED, ui_scale=70, legend_mode='panel', toolbar_hidden=True)
PC = dict(SHARED, ui_scale=100, legend_mode='steam', toolbar_hidden=False)


class SetupTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.home = self.root / 'home'
        self.home.mkdir()
        self.settings = self.root / 'settings'
        self.service = Service(self.home, self.settings)

    def tearDown(self):
        self.service.shutdown()
        self.temp.cleanup()

    def reopen(self):
        self.service.shutdown()
        self.service = Service(self.home, self.settings)
        return self.service

    def test_new_installation_starts_without_completed_setup(self):
        settings = self.service.state()['settings']
        self.assertFalse(settings['setup_completed'])
        self.assertFalse(settings['toolbar_hidden'])
        self.assertEqual(settings['profile'], '')

    def test_profiles_match_the_agreed_presets(self):
        self.assertEqual(self.service.setup_profiles(), {'handheld': HANDHELD, 'pc': PC})
        self.assertEqual(PROFILES, self.service.setup_profiles())
        # Returned presets are copies: callers cannot change the backend defaults.
        self.service.setup_profiles()['pc']['ui_scale'] = 70
        self.assertEqual(self.service.setup_profiles()['pc']['ui_scale'], 100)

    def test_existing_settings_file_without_setup_keys_keeps_personalisation(self):
        self.service.update_settings({'accent': 'rose', 'ui_scale': 80, 'legend_mode': 'none'})
        saved = json.loads(self.service.config_file.read_text())
        for key in ('setup_completed', 'toolbar_hidden', 'profile'): saved['settings'].pop(key, None)
        self.service.config_file.write_text(json.dumps(saved))
        settings = self.reopen().state()['settings']
        self.assertFalse(settings['setup_completed'])
        self.assertEqual((settings['accent'], settings['ui_scale'], settings['legend_mode']), ('rose', 80, 'none'))

    def test_toolbar_and_setup_flags_persist_and_validate(self):
        self.service.update_settings({'toolbar_hidden': True, 'setup_completed': True, 'profile': 'handheld'})
        settings = self.reopen().state()['settings']
        self.assertTrue(settings['toolbar_hidden'])
        self.assertTrue(settings['setup_completed'])
        self.assertEqual(settings['profile'], 'handheld')
        for key, value in (('toolbar_hidden', 'yes'), ('setup_completed', 1), ('profile', 'tablet'), ('profile', None)):
            with self.assertRaises(ValueError): self.service.update_settings({key: value})
        self.assertTrue(self.service.state()['settings']['toolbar_hidden'])
        self.assertEqual(self.service.state()['settings']['profile'], 'handheld')
        self.service.update_settings({'profile': ''})
        self.assertEqual(self.service.state()['settings']['profile'], '')

    def test_setup_applies_profile_and_marks_completion(self):
        state = self.service.setup('handheld')
        settings = state['settings']
        for key, value in HANDHELD.items(): self.assertEqual(settings[key], value, key)
        self.assertTrue(settings['setup_completed'])
        self.assertEqual(settings['profile'], 'handheld')
        self.assertEqual(settings['accent'], 'cyan')
        reopened = self.reopen().state()['settings']
        self.assertTrue(reopened['setup_completed'])
        self.assertEqual(reopened['ui_scale'], 70)

    def test_setup_applies_edited_values_over_the_profile(self):
        settings = self.service.setup('pc', {'ui_scale': 90, 'show_hidden': False, 'accent': 'green'})['settings']
        self.assertEqual((settings['ui_scale'], settings['show_hidden'], settings['accent']), (90, False, 'green'))
        self.assertEqual(settings['legend_mode'], 'steam')
        self.assertFalse(settings['toolbar_hidden'])
        self.assertEqual(settings['profile'], 'pc')
        self.assertTrue(settings['setup_completed'])

    def test_setup_rejects_unknown_profile_and_invalid_edits_without_saving(self):
        self.service.update_settings({'accent': 'amber'})
        with self.assertRaises(ValueError): self.service.setup('tablet')
        with self.assertRaises(ValueError): self.service.setup('pc', {'ui_scale': 95})
        with self.assertRaises(ValueError): self.service.setup('pc', {'setup_completed': False})
        with self.assertRaises(ValueError): self.service.setup('pc', {'profile': 'handheld'})
        settings = self.reopen().state()['settings']
        self.assertFalse(settings['setup_completed'])
        self.assertEqual(settings['profile'], '')
        self.assertEqual(settings['accent'], 'amber')
        self.assertEqual(settings['ui_scale'], 100)

    def test_setup_keeps_panel_paths_and_connections(self):
        left = str(self.home / 'left')
        (self.home / 'left').mkdir()
        self.service.update_settings({'left': left})
        self.service.config['connections']['smb-1'] = {'host': 'nas', 'share': 'media', 'username': 'u', 'label': 'NAS'}
        self.service.save()
        state = self.service.setup('handheld')
        self.assertEqual(state['settings']['left'], left)
        self.assertEqual([c['id'] for c in state['connections']], ['smb-1'])

    def test_failed_save_rolls_back_setup_in_memory_and_on_disk(self):
        self.service.update_settings({'accent': 'violet'})
        with patch.object(Service, 'save', side_effect=OSError('disk full')):
            with self.assertRaises(OSError): self.service.setup('handheld', {'ui_scale': 80})
            with self.assertRaises(OSError): self.service.update_settings({'toolbar_hidden': True, 'accent': 'rose'})
        for settings in (self.service.state()['settings'], self.reopen().state()['settings']):
            self.assertFalse(settings['setup_completed'])
            self.assertEqual(settings['profile'], '')
            self.assertEqual((settings['ui_scale'], settings['legend_mode'], settings['toolbar_hidden'], settings['accent']), (100, 'both', False, 'violet'))
        # The service keeps working after the failure.
        self.assertTrue(self.service.setup('handheld')['settings']['setup_completed'])

    def test_failed_save_keeps_connections_and_previous_setup(self):
        self.service.setup('pc')
        self.service.config['connections']['smb-1'] = {'host': 'nas', 'share': 'media', 'username': 'u', 'label': 'NAS'}
        self.service.save()
        with patch.object(Service, 'save', side_effect=credentials.CredentialError('no credential store')):
            with self.assertRaises(credentials.CredentialError): self.service.setup('handheld')
        settings = self.service.state()['settings']
        self.assertEqual((settings['profile'], settings['ui_scale']), ('pc', 100))
        self.assertEqual([c['id'] for c in self.service.state()['connections']], ['smb-1'])

    def test_rerun_setup_can_switch_profiles(self):
        self.service.setup('handheld')
        settings = self.service.setup('pc')['settings']
        self.assertEqual((settings['profile'], settings['ui_scale'], settings['legend_mode'], settings['toolbar_hidden']),
                         ('pc', 100, 'steam', False))


if __name__ == '__main__':
    unittest.main()

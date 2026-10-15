import json
import sys
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fileexplorer.service import Service


class SplashTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.home = Path(self.temp.name) / 'home'
        self.home.mkdir()
        self.settings = Path(self.temp.name) / 'settings'
        self.service = Service(self.home, self.settings)

    def tearDown(self):
        self.service.shutdown()
        self.temp.cleanup()

    def reopen(self):
        self.service.shutdown()
        self.service = Service(self.home, self.settings)

    def test_first_launch_once_even_if_setup_is_cancelled_and_service_restarts(self):
        before = self.service.state()['settings']
        self.assertFalse(before['splash_enabled'])
        self.assertTrue(self.service.claim_splash()['show'])
        self.assertFalse(self.service.claim_splash()['show'])
        self.reopen()
        after = self.service.state()['settings']
        self.assertFalse(after['setup_completed'])
        self.assertFalse(self.service.claim_splash()['show'])
        self.assertEqual({**before, 'splash_seen': True}, after)

    def test_enabled_replays_and_disabled_stops_replaying(self):
        self.service.claim_splash()
        self.service.update_settings({'splash_enabled': True})
        self.reopen()
        self.assertTrue(self.service.claim_splash()['show'])
        self.assertTrue(self.service.claim_splash()['show'])
        self.service.update_settings({'splash_enabled': False})
        self.reopen()
        self.assertFalse(self.service.claim_splash()['show'])

    def test_concurrent_first_launch_claims_show_once(self):
        with ThreadPoolExecutor(max_workers=8) as workers:
            shown = list(workers.map(lambda _: self.service.claim_splash()['show'], range(20)))
        self.assertEqual(sum(shown), 1)

    def test_failed_save_does_not_consume_first_launch(self):
        with patch.object(Service, 'save', side_effect=OSError('disk full')):
            with self.assertRaises(OSError): self.service.claim_splash()
        self.assertFalse(self.service.state()['settings']['splash_seen'])
        self.assertTrue(self.service.claim_splash()['show'])

    def test_upgrade_keeps_preferences_and_connections(self):
        self.service.update_settings({'accent': 'rose', 'setup_completed': True})
        self.service.config['connections']['nas'] = {'host': 'nas', 'share': 'games', 'label': 'Games'}
        self.service.save()
        saved = json.loads(self.service.config_file.read_text())
        for key in ('splash_enabled', 'splash_seen'): saved['settings'].pop(key)
        self.service.config_file.write_text(json.dumps(saved))
        self.reopen()
        self.assertTrue(self.service.claim_splash()['show'])
        self.assertEqual(self.service.state()['settings']['accent'], 'rose')
        self.assertTrue(self.service.state()['settings']['setup_completed'])
        self.assertEqual(self.service.state()['connections'][0]['id'], 'nas')

    def test_setup_presets_default_off_without_rearming_first_launch(self):
        self.service.claim_splash()
        for profile in ('handheld', 'pc'):
            self.assertFalse(self.service.setup_profiles()[profile]['splash_enabled'])
            self.service.setup(profile, {'splash_enabled': True})
            self.assertTrue(self.service.claim_splash()['show'])
            self.service.setup(profile)
            self.assertFalse(self.service.claim_splash()['show'])

    def test_only_boolean_option_can_be_changed(self):
        for value in ('yes', 1, None):
            with self.assertRaises(ValueError): self.service.update_settings({'splash_enabled': value})
        with self.assertRaises(ValueError): self.service.update_settings({'splash_seen': False})
        with self.assertRaises(ValueError): self.service.setup('handheld', {'splash_seen': False})


if __name__ == '__main__':
    unittest.main()

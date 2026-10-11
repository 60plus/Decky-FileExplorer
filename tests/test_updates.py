import copy
import hashlib
import io
import json
from pathlib import Path
import stat
import tempfile
import threading
import unittest
from unittest.mock import patch
import zipfile

from fileexplorer import updates as u


def archive(version='0.6.1', extra=None, plugin=None):
    out = io.BytesIO()
    files = {'package.json': json.dumps({'name': 'decky-fileexplorer', 'version': version}),
             'plugin.json': json.dumps(plugin or {'name': 'FileExplorer', 'author': '60plus'}),
             'main.py': '', 'dist/index.js': '', 'fileexplorer/service.py': '',
             'fileexplorer/updates.py': '', 'vendor/smb/SMBConnection.py': ''}
    with zipfile.ZipFile(out, 'w') as z:
        for name, data in files.items(): z.writestr(zipfile.ZipInfo('FileExplorer/' + name), data)
        if extra:
            name, data, mode = extra
            info = zipfile.ZipInfo(name); info.external_attr = mode << 16
            z.writestr(info, data)
    return out.getvalue()


def candidate(data, version='0.6.1'):
    return dict(version=version, size=len(data), sha256=hashlib.sha256(data).hexdigest(),
                url=u.DOWNLOADS + 'v' + version + '/FileExplorer-' + version + '.zip')


class ReleaseTests(unittest.TestCase):
    def setUp(self):
        self.data = archive(); self.candidate = candidate(self.data)
        self.filename = 'FileExplorer-0.6.1.zip'
        self.release = dict(tag_name='v0.6.1', html_url=u.WEB+'/releases/tag/v0.6.1', draft=False, prerelease=False, body='Release notes', assets=[
            dict(name=self.filename, size=len(self.data), browser_download_url=self.candidate['url'], digest='sha256:'+self.candidate['sha256']),
            dict(name=self.filename+'.sha256', browser_download_url=self.candidate['url']+'.sha256')])

    def read(self, url, limit):
        if url == u.LATEST: return json.dumps(self.release).encode()
        if url.endswith('.sha256'): return (self.candidate['sha256']+'  '+self.filename+'\n').encode()
        return self.data

    def test_select_newer_and_download_identity(self):
        with patch.object(u, 'read_url', side_effect=self.read):
            result = u.check_release('0.6.0')
            self.assertEqual(result['candidate']['version'], '0.6.1')
            u.verify_archive(self.data, result['candidate'])

    def test_same_and_older_release_are_not_updates(self):
        with patch.object(u, 'read_url', side_effect=self.read):
            for installed in ('0.6.1', '0.7.0'): self.assertIsNone(u.check_release(installed)['candidate'])

    def test_no_release_is_not_up_to_date(self):
        with patch.object(u, 'read_url', return_value=None):
            result = u.check_release('0.6.0')
            self.assertIsNone(result['latest']); self.assertIn('No public stable', result['message'])

    def test_reject_prerelease_draft_invalid_versions(self):
        for changes in ({'prerelease': True}, {'draft': True}, {'tag_name': 'v0.7.0-rc1'}, {'tag_name': '../0.7.0'}):
            with patch.object(u, 'read_url', return_value=json.dumps(self.release | changes).encode()), self.assertRaises(ValueError): u.check_release('0.6.0')

    def test_reject_foreign_assets_missing_checksum_and_digest_mismatch(self):
        cases = []
        for url in ('https://evil.example/plugin.zip', u.DOWNLOADS+'v0.7.0/'+self.filename):
            r = copy.deepcopy(self.release); r['assets'][0]['browser_download_url'] = url; cases.append(r)
        r = copy.deepcopy(self.release); r['assets'].pop(); cases.append(r)
        r = copy.deepcopy(self.release); r['assets'][0]['digest'] = 'sha256:'+'0'*64; cases.append(r)
        for r in cases:
            self.release = r
            with patch.object(u, 'read_url', side_effect=self.read), self.assertRaises(ValueError): u.check_release('0.6.0')

    def test_reject_corrupt_or_mismatched_package(self):
        with self.assertRaises(ValueError): u.verify_archive(self.data+b'x', self.candidate)
        for data in (archive('0.7.0'), archive(plugin={'name':'Other','author':'60plus'}), archive(plugin={'name':'FileExplorer','author':'60plus','remote_binary':['evil']}), b'not zip'):
            with self.assertRaises(ValueError): u.verify_archive(data, candidate(data))

    def test_reject_traversal_duplicate_and_special_entries(self):
        for name, mode in [('FileExplorer/../escape', 0), ('/absolute', 0), ('FileExplorer//bad', 0), ('FileExplorer/link', stat.S_IFLNK), ('FileExplorer/fifo', stat.S_IFIFO), ('FileExplorer/main.py', 0)]:
            with self.subTest(name=name):
                data = archive(extra=(name, 'x', mode))
                with self.assertRaises(ValueError): u.verify_archive(data, candidate(data))

    def test_expansion_limit(self):
        with patch.object(u, 'MAX_EXPANDED', 5), self.assertRaises(ValueError): u.verify_archive(self.data, self.candidate)

    def test_redirect_refuses_http_and_foreign_host(self):
        for url in ('http://github.com/file', 'https://evil.example/file', 'https://github.com@evil.example/file'):
            with self.assertRaises(RuntimeError): u.SafeRedirect().redirect_request(None, None, 302, '', {}, url)


class StartupTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        class Service:
            settings_dir = Path(self.temp.name)
            lock = threading.RLock()
            config = {'settings': {'check_updates_on_start': True}}
        self.service = Service()
        self.updates = u.Updates(self.service)
        self.result = dict(installed='0.6.0', latest='0.6.1', candidate=candidate(archive()), message='Update available.')

    def tearDown(self): self.temp.cleanup()

    def test_notice_only_once_across_backend_reloads_then_next_boot(self):
        with patch.object(u, 'check_release', return_value=self.result) as check:
            self.assertIsNotNone(self.updates.startup())
            self.assertIsNone(u.Updates(self.service).startup())
            self.assertEqual(check.call_count, 1)
            state = self.updates.root/'startup.json'
            state.write_text(json.dumps({'boot':'previous-boot', 'checked':True}))
            self.assertIsNotNone(u.Updates(self.service).startup())
            self.assertEqual(check.call_count, 2)

    def test_disabled_skips_network_and_manual_check_still_works(self):
        self.service.config['settings']['check_updates_on_start'] = False
        with patch.object(u, 'check_release', return_value=self.result) as check:
            self.assertIsNone(self.updates.startup()); check.assert_not_called()
            self.assertIsNotNone(self.updates.check()['candidate'])

    def test_offline_retries_after_backoff_across_reload(self):
        with patch.object(u, 'check_release', side_effect=RuntimeError('offline')) as check:
            self.assertIsNone(self.updates.startup()); self.assertIsNone(u.Updates(self.service).startup())
            self.assertEqual(check.call_count, 1)
        with patch.object(u, 'time') as clock, patch.object(u, 'check_release', return_value=self.result):
            clock.time.return_value = 10**12; clock.monotonic.return_value = 100
            self.assertIsNotNone(u.Updates(self.service).startup())

    def test_up_to_date_is_only_checked_once(self):
        with patch.object(u, 'check_release', return_value=self.result | {'candidate': None}) as check:
            self.assertIsNone(self.updates.startup()); self.assertIsNone(u.Updates(self.service).startup())
            self.assertEqual(check.call_count, 1)

    def test_concurrent_instances_only_claim_one_notice(self):
        from concurrent.futures import ThreadPoolExecutor
        with patch.object(u, 'check_release', return_value=self.result) as check, ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda _: u.Updates(self.service).startup(), range(2)))
            self.assertEqual(sum(r is not None for r in results), 1)
            self.assertEqual(check.call_count, 1)

    def test_disabling_during_check_suppresses_notice(self):
        def finish(_):
            self.service.config['settings']['check_updates_on_start'] = False
            return self.result
        with patch.object(u, 'check_release', side_effect=finish): self.assertIsNone(self.updates.startup())

    def test_download_rechecks_bytes_and_keeps_settings(self):
        data = archive()
        with patch.object(u, 'check_release', return_value=self.result), patch.object(u, 'read_url', return_value=data):
            with self.assertRaises(ValueError): self.updates.prepare('0.6.1')
            self.updates.check()
            prepared = self.updates.prepare('0.6.1')
            path = self.updates.root/('FileExplorer-'+self.result['candidate']['sha256']+'.zip')
            self.assertEqual(path.read_bytes(), data); self.assertEqual(prepared['artifact'], path.as_uri())
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
            self.assertTrue(self.service.config['settings']['check_updates_on_start'])
        with patch.object(u, 'read_url', return_value=data+b'x'), self.assertRaises(ValueError): self.updates.prepare('0.6.1')


if __name__ == '__main__': unittest.main()

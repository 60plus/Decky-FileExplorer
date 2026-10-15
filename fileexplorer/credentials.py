"""User-scoped systemd credentials. Plaintext only travels over process pipes."""
import base64
import binascii
import copy
import re
import subprocess

from .environment import systemd_environment

# Stable format IDs from systemd's src/shared/creds-util.h. Reject null-key,
# unscoped and unknown formats; never silently fall back to a plaintext file.
FORMATS = {
    '55b9ed1d38594d43a8319d2ebb332ac6': 'system',
    'ef4ac13679a9480ea7db68897f9f165d': 'tpm',
    'adbc4ca3efb64201ba881b6f2e4095ea': 'tpm',
}
SAVE_ERROR = ('Secure SMB password storage is unavailable. No new password was saved. '
              'Check systemd credential support, or disable Remember connection for this session.')
READ_ERROR = ('The saved SMB password cannot be unlocked on this device. '
              'Restore access to the original system credentials, or forget and reconnect this share in Settings.')


class CredentialError(ValueError):
    pass


def credential_name(key):
    if not isinstance(key, str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,64}', key):
        raise CredentialError('Invalid SMB credential identifier.')
    return 'fileexplorer-smb-' + key


def protection(blob):
    try:
        if not isinstance(blob, str) or len(blob) > 65536: raise ValueError()
        raw = base64.b64decode(''.join(blob.split()), validate=True)
        return FORMATS[raw[:16].hex()]
    except (ValueError, KeyError, binascii.Error):
        raise CredentialError('Unsupported or damaged encrypted SMB password.') from None


def _run(action, key, value):
    try:
        result = subprocess.run(
            ['/usr/bin/systemd-creds', '--user', '--name=' + credential_name(key), action, '-', '-'],
            input=value, capture_output=True, timeout=20, env=systemd_environment())
        if result.returncode: raise CredentialError(SAVE_ERROR if action == 'encrypt' else READ_ERROR)
        return result.stdout
    except (OSError, subprocess.SubprocessError):
        raise CredentialError(SAVE_ERROR if action == 'encrypt' else READ_ERROR) from None


def unseal_password(key, blob):
    protection(blob)
    try:
        value = _run('decrypt', key, blob.encode('ascii')).decode('utf-8')
        if len(value) > 1024 or '\x00' in value: raise ValueError()
        return value
    except (UnicodeError, ValueError) as error:
        if isinstance(error, CredentialError): raise
        raise CredentialError(READ_ERROR) from None


def seal_password(key, password):
    if not isinstance(password, str) or len(password) > 1024 or '\x00' in password:
        raise CredentialError('Invalid SMB password.')
    try:
        blob = _run('encrypt', key, password.encode('utf-8')).decode('ascii').strip()
        protection(blob)
        # Migration must not remove the old value until this device can read it.
        if unseal_password(key, blob) != password: raise CredentialError(SAVE_ERROR)
        return blob
    except UnicodeError:
        raise CredentialError(SAVE_ERROR) from None


def protect_profiles(profiles):
    result = copy.deepcopy(profiles)
    for key, profile in result.items():
        if 'password' not in profile: continue
        password = profile.pop('password')
        if password:
            profile['password_credential'] = seal_password(key, password)
        else:
            profile.pop('password_credential', None)
    return result


def password_for(key, profile):
    if 'password_credential' in profile:
        return unseal_password(key, profile['password_credential'])
    return profile.get('password', '')  # Session-only or an explicitly warned legacy profile.


def storage_for(profile, saved):
    if 'password_credential' in profile:
        try: return protection(profile['password_credential'])
        except CredentialError: return 'unavailable'
    if profile.get('password'): return 'legacy' if saved else 'session'
    return 'none'

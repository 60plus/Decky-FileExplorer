"""No-TPM fallback probe using random data; never changes the host TPM.

Run on SteamOS as root in a transient isolated service:
  systemd-run --quiet --pipe --wait --collect -p PrivateDevices=yes \
    -p 'InaccessiblePaths=-/sys/class/tpm -/sys/class/tpmrm -/sys/firmware/acpi/tables/TPM2' \
    /usr/bin/python3 /absolute/path/to/this_script.py

Encryption uses the same automatic selection as the system credential broker.
The decrypted value is checked by the unprivileged deck account.
"""
import base64,json,os,secrets,subprocess
# Run this diagnostic inside a transient system service with PrivateDevices=yes.
assert os.geteuid()==0 and not os.path.exists('/dev/tpmrm0')
payload=secrets.token_bytes(32)
args=['/usr/bin/systemd-creds','--uid=1000','--name=fileexplorer-no-tpm-test']
c=subprocess.run([*args,'encrypt','-','-'],input=payload,capture_output=True,timeout=20)
if c.returncode: print(c.stderr.decode());raise SystemExit(c.returncode)
header=base64.b64decode(c.stdout)[:16].hex()
assert header=='55b9ed1d38594d43a8319d2ebb332ac6',header
p=subprocess.run(['runuser','-u','deck','--','/usr/bin/systemd-creds','--user','--name=fileexplorer-no-tpm-test','decrypt','-','-'],input=c.stdout,capture_output=True,check=True,timeout=20)
assert p.stdout==payload
print(json.dumps(dict(status='passed',tpm_device_visible=False,protection='user-scoped host key',roundtrip_as_deck=True)))

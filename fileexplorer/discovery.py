"""Bounded, on-demand SMB discovery on directly connected private IPv4 LANs."""
import ipaddress
import json
import re
import shutil
import socket
import subprocess
import threading
from concurrent.futures import ThreadPoolExecutor

_lock = threading.Lock()


def candidates(routes):
    addresses = set()
    networks = []
    limited = False
    for route in routes:
        if route.get('dev', '').startswith(('lo', 'docker', 'veth', 'br-', 'tun', 'tap', 'wg', 'tailscale')): continue
        try:
            network = ipaddress.IPv4Network(route['dst'])
            if not network.is_private or network.is_loopback or network.is_link_local: continue
            if network.num_addresses > 256:
                network = ipaddress.IPv4Network(route['prefsrc'] + '/24', strict=False)
                limited = True
            networks.append(str(network))
            for address in network.hosts():
                if len(addresses) >= 512:
                    limited = True
                    break
                addresses.add(str(address))
        except (KeyError, ValueError): continue
    return sorted(addresses, key=ipaddress.IPv4Address), sorted(set(networks)), limited


def avahi_servers(output):
    result = {}
    for line in output.splitlines():
        parts = line.split(';')
        if len(parts) < 9 or parts[0] != '=' or parts[2] != 'IPv4' or parts[8] != '445': continue
        try:
            address = ipaddress.IPv4Address(parts[7])
            if not address.is_private or address.is_loopback: continue
        except ValueError: continue
        label = re.sub(r'\\(\d{3})', lambda m: chr(int(m[1])), parts[3])
        result[str(address)] = label
    return result


def discover():
    if not _lock.acquire(blocking=False): raise ValueError('Network discovery is already running')
    try:
        routes = subprocess.run(['ip', '-j', '-4', 'route', 'show', 'scope', 'link'],
                                capture_output=True, text=True, timeout=5, check=True)
        hosts, networks, limited = candidates(json.loads(routes.stdout))
        advertised = {}
        if shutil.which('avahi-browse'):
            try:
                result = subprocess.run(['avahi-browse', '-rtp', '_smb._tcp'], capture_output=True, text=True, timeout=4)
                advertised = avahi_servers(result.stdout)
            except subprocess.TimeoutExpired as e:
                output = e.stdout or b''
                advertised = avahi_servers(output.decode(errors='replace') if isinstance(output, bytes) else output)
        # Discovery probes only TCP 445; credentials are sent only to the chosen host.
        def probe(host):
            try:
                with socket.create_connection((host, 445), timeout=.45):
                    return dict(host=host, name=advertised.get(host, host))
            except OSError: return None
        targets = list(dict.fromkeys([*advertised, *hosts]))[:512]
        with ThreadPoolExecutor(max_workers=48) as pool: servers = [s for s in pool.map(probe, targets) if s]
        return dict(servers=servers, networks=networks, limited=limited)
    finally: _lock.release()

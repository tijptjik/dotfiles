"""Synthetic routing probe: run only inside a fresh network namespace."""
import json
from pathlib import Path
import socket
import subprocess
import sys


def run(*args, body=None):
    result = subprocess.run(args, input=body, text=True, capture_output=True)
    assert result.returncode == 0, (args, result.stderr)
    return result.stdout


assert {link['ifname'] for link in json.loads(run('ip', '-j', 'link', 'show'))} == {'lo'}, 'A fresh isolated network namespace is required'
run('ip', 'link', 'set', 'lo', 'up')
for name, address in [('tailscale0', '100.110.134.3/32'), ('wg0-mullvad', '10.0.0.1/32'), ('wan0', '198.18.0.1/24')]:
    run('ip', 'link', 'add', name, 'type', 'dummy')
    run('ip', 'link', 'set', name, 'up')
    run('ip', 'addr', 'add', address, 'dev', name)
run('ip', '-6', 'addr', 'add', 'fd7a:115c:a1e0::1/128', 'dev', 'tailscale0', 'nodad')
run('ip', '-6', 'addr', 'add', '2001:db8::1/128', 'dev', 'wg0-mullvad', 'nodad')
for family, network in [('-4', '100.85.220.100/32'), ('-6', 'fd7a:115c:a1e0::2/128')]:
    run('ip', family, 'route', 'add', network, 'dev', 'tailscale0', 'table', '52')
    run('ip', family, 'route', 'add', 'default', 'dev', 'wg0-mullvad', 'table', '1836018789')
    run('ip', family, 'route', 'add', 'default', 'dev', 'wan0')
    run('ip', family, 'rule', 'add', 'priority', '5099', 'not', 'fwmark', '0x6d6f6c65', 'lookup', '1836018789')
    run('ip', family, 'rule', 'add', 'priority', '5100', 'to', '100.64.0.0/10' if family == '-4' else 'fd7a:115c:a1e0::/48', 'lookup', '52')
run('nft', '-f', '-', body='''table inet fixture {
    chain filter {
        type filter hook output priority 0; policy drop;
        oifname "lo" accept
        ct mark 0xf41 accept
        oifname "wg0-mullvad" accept
    }
    chain observe {
        type filter hook postrouting priority 2; policy accept;
        meta l4proto udp oifname "tailscale0" counter comment "tailnet"
        meta l4proto udp oifname "wg0-mullvad" counter comment "vpn"
        meta l4proto udp oifname "wan0" counter comment "wan"
        meta l4proto udp oifname "lo" counter comment "local"
    }
}''')


def counts():
    result = json.loads(run('nft', '-j', 'list', 'chain', 'inet', 'fixture', 'observe'))
    return {item['rule']['comment']: next(e['counter']['packets'] for e in item['rule']['expr'] if 'counter' in e) for item in result['nftables'] if 'rule' in item}


def send(address, expected):
    before = counts()
    with socket.socket(socket.AF_INET6 if ':' in address else socket.AF_INET, socket.SOCK_DGRAM) as sock:
        try:
            sock.sendto(b'synthetic', (address, 45678))
        except PermissionError:
            assert expected is None
    after = counts()
    changed = {key: after[key] - before[key] for key in before}
    assert changed == {key: int(key == expected) for key in before}, (address, expected, changed)


send('100.85.220.100', 'vpn')  # Reproduce the original misrouting.
run('nft', '-f', sys.argv[1])
for priority in ('5099', '1000'):
    if priority == '1000':
        for family in ('-4', '-6'):
            run('ip', family, 'rule', 'del', 'priority', '5099')
            run('ip', family, 'rule', 'add', 'priority', priority, 'not', 'fwmark', '0x6d6f6c65', 'lookup', '1836018789')
    send('100.110.134.3', 'local')
    send('fd7a:115c:a1e0::1', 'local')
    send('100.85.220.100', 'tailnet')
    send('fd7a:115c:a1e0::2', 'tailnet')
    send('1.1.1.1', 'vpn')
    send('2001:db8::2', 'vpn')
    send('100.64.0.1', None)  # No tailnet route: fail closed.
    send('fd7a:115c:a1e0::99', None)
run('ip', 'link', 'del', 'tailscale0')
send('100.85.220.100', None)
send('1.1.1.1', 'vpn')
print('PASS: original timeout route reproduced; IPv4/IPv6 tailnet routing survives VPN precedence changes; internet stays on VPN; missing tailnet routes fail closed')

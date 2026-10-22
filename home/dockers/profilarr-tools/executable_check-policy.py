#!/usr/bin/env python3
"""Show a configured acquisition strategy; this is not a release classifier."""
import argparse
import json
import pathlib
import re

POLICY = pathlib.Path(__file__).resolve().parent.parent / 'profilarr-database/policy.json'


def main():
    policy = json.loads(POLICY.read_text())
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('profile', nargs='?', default=policy['default'])
    parser.add_argument('--list', action='store_true', help='List the supported acquisition profiles')
    args = parser.parse_args()
    profiles = policy['acquisitions']
    if args.list:
        print('\n'.join(profile['name'] for profile in profiles))
        return
    match = re.fullmatch(r'\s*@\s*(\S+)\s*\|\s*mx\s+(\S+)\s*\|\s*mn\s+(\S+)\s*', args.profile)
    if not match:
        parser.error('Expected @ {target} | mx {maximum} | mn {minimum}')
    target, maximum, minimum = match.groups()
    name = f'@ {target} | mx {maximum} | mn {minimum}'
    profile = next((profile for profile in profiles if profile['name'] == name), None)
    if profile is None:
        parser.error('This combination is not configured; use --list. Strategies overlap, so arbitrary ranges are not implied.')
    print(json.dumps(profile, indent=2))


if __name__ == '__main__':
    main()

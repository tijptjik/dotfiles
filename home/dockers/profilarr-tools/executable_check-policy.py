#!/usr/bin/env python3
"""Inspect requested tier rules and the native settings this snapshot enforces."""
import argparse
import json
import pathlib

POLICY = pathlib.Path(__file__).resolve().parent.parent / 'profilarr-database/policy.json'


def main():
    policy = json.loads(POLICY.read_text())
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('profile', nargs='?', default=policy['default'])
    parser.add_argument('--list', action='store_true', help='List acquisition profile names')
    args = parser.parse_args()
    if args.list:
        print('\n'.join(profile['name'] for profile in policy['acquisitions']))
        return
    profile = next((p for p in policy['acquisitions'] if p['name'] == args.profile), None)
    if profile is None:
        parser.error('Unknown profile; use --list')
    result = {k: v for k, v in profile.items() if k != 'legacyNames'}
    result['enforcement'] = policy['enforcement']
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()

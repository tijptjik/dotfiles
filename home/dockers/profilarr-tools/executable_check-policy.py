#!/usr/bin/env python3
"""Validate acquisition notation against an already-classified media tier.

This is a read-only policy checker, not a release or bitrate classifier.
"""
import argparse
import json
import pathlib
import re

policy = json.loads((pathlib.Path(__file__).parent.parent / 'profilarr-database/policy.json').read_text())
order = policy['order']

def parse_profile(text):
    match = re.fullmatch(r'\s*@\s*(\S+)\s*\|\s*mx\s+(\S+)\s*\|\s*mn\s+(\S+)\s*', text)
    if not match:
        raise ValueError('Expected @ {target} | mx {maximum} | mn {minimum}')
    target, maximum, minimum = match.groups()
    for value in [target, maximum, minimum]:
        if value not in order:
            raise ValueError(f'Unknown media tier: {value}')
    if not order.index(minimum) <= order.index(target) <= order.index(maximum):
        raise ValueError('Require minimum <= upgrade target <= maximum')
    return target, maximum, minimum

def evaluate(profile, candidate=None):
    target, maximum, minimum = parse_profile(profile)
    accepted = order[order.index(minimum):order.index(maximum) + 1]
    result = {'profile': f'@ {target} | mx {maximum} | mn {minimum}', 'acceptedTiers': accepted}
    if candidate is not None:
        if candidate not in order:
            raise ValueError(f'Unknown media tier: {candidate}')
        allowed = candidate in accepted
        result.update(candidate=candidate, accepted=allowed, upgradeTargetReached=allowed and order.index(candidate) >= order.index(target))
    return result

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('profile', nargs='?', default=policy['example']['name'])
    parser.add_argument('--candidate', choices=order)
    args = parser.parse_args()
    try:
        print(json.dumps(evaluate(args.profile, args.candidate), indent=2))
    except ValueError as error:
        parser.error(str(error))

"""Adopt metadata-only differences after comparing with native desired bytes."""
from native_adoption import adopt as native_adopt


def adopt(repo, manifest, state, apply_command):
    native_adopt(manifest, state, apply_command)

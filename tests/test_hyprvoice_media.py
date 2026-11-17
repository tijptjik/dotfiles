from pathlib import Path
import subprocess
import unittest


class HyprvoiceMediaTests(unittest.TestCase):
    def test_player_selection_and_resume(self):
        root = Path(__file__).resolve().parents[1]
        subprocess.run([
            'lua', str(root / 'tests/hyprvoice_media.lua'),
            str(root / 'native/home/files/.config/hypr/helpers.lua'),
        ], check=True)

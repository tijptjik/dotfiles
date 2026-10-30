import runpy
from pathlib import Path
import unittest


class DesktopPanelsToggleTests(unittest.TestCase):
    def test_toggles_only_bartjik_without_querying_notjik(self):
        script = Path(__file__).resolve().parents[1] / 'native/home/files/.local/bin/desktop-panels-toggle'
        toggle = runpy.run_path(str(script))['toggle']
        for visible, concealed in ((False, False), (True, True), (True, False)):
            with self.subTest(visible=visible, concealed=concealed):
                calls = []

                def control(name, *args):
                    calls.append((name, *args))
                    self.assertEqual(name, 'bartjikctl')
                    if args == ('bars',):
                        return {'bars': [{'visible': visible, 'concealed': concealed}]}
                    return {'ok': True}

                toggle.__globals__['control'] = control
                toggle()
                self.assertEqual(calls, [
                    ('bartjikctl', 'bars'),
                    ('bartjikctl', 'hide-reveal' if visible and not concealed else 'show-reveal'),
                ])

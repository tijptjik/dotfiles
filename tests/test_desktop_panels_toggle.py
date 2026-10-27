import runpy
from pathlib import Path
import unittest


class DesktopPanelsToggleTests(unittest.TestCase):
    def test_all_panel_states_converge(self):
        script = Path(__file__).resolve().parents[1] / 'home/dot_local/bin/executable_desktop-panels-toggle'
        toggle = runpy.run_path(str(script))['toggle']
        for bar_open in (False, True):
            for history_open in (False, True):
                with self.subTest(bar=bar_open, history=history_open):
                    calls = []

                    def control(name, *args):
                        calls.append((name, *args))
                        if args == ('bars',):
                            return {'bars': [{'visible': True, 'concealed': not bar_open}]}
                        if args == ('status',):
                            return {'drawerOpen': history_open}
                        return {'ok': True}

                    toggle.__globals__['control'] = control
                    toggle()
                    close = bar_open and history_open
                    self.assertEqual(calls[-2:], [
                        ('bartjikctl', 'hide-reveal' if close else 'show-reveal'),
                        ('notjikctl', 'history', 'hide' if close else 'show'),
                    ])

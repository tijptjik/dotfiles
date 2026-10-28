import importlib.util
from pathlib import Path
import unittest

PATH = Path(__file__).resolve().parents[1] / "etc/si-provision/nss_systemd.py"
spec = importlib.util.spec_from_file_location("nss_migration", PATH)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

class NssTests(unittest.TestCase):
    def test_preserves_existing_policy_and_comments(self):
        text = "passwd: files sss systemd\nshadow: files sss  # local policy\ngshadow: files\nhosts: files dns\n"
        result = module.render(text)
        self.assertEqual(result, "passwd: files sss systemd\nshadow: files sss systemd  # local policy\ngshadow: files systemd\nhosts: files dns\n")
        self.assertEqual(module.render(result), result)

    def test_current_defaults_are_unchanged(self):
        text = "shadow: files systemd\ngshadow: files systemd\n"
        self.assertEqual(module.render(text), text)

    def test_adds_missing_databases_without_changing_existing_lines(self):
        self.assertEqual(module.render("passwd: files\n"), "passwd: files\nshadow: files systemd\ngshadow: files systemd\n")

if __name__ == "__main__":
    unittest.main()

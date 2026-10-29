"""Historical Plex backups must not weaken active database validation."""
import ast
from pathlib import Path
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "tests/legacy/protection/backup.py"
PLEX = "/mnt/storage/meta/opt/plexmediaserver/Library/Application Support/Plex Media Server"

class DatabaseRoleTests(unittest.TestCase):
    def setUp(self):
        tree = ast.parse(SCRIPT.read_text())
        function = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "is_historical_plex_database")
        namespace = {"pathlib": __import__("pathlib"), "plex": PLEX}
        exec(compile(ast.Module(body=[function], type_ignores=[]), str(SCRIPT), "exec"), namespace)
        self.historical = namespace["is_historical_plex_database"]

    def test_only_plex_migration_backups_are_historical(self):
        directory = Path(PLEX) / "Plug-in Support/Databases"
        self.assertTrue(self.historical(directory / "com.plexapp.plugins.library.db.bak"))
        self.assertTrue(self.historical(directory / "com.plexapp.plugins.library.blobs.db.bak"))
        for name in ["com.plexapp.plugins.library.db", "com.plexapp.plugins.library.blobs.db", "other.bak"]:
            self.assertFalse(self.historical(directory / name))
        self.assertFalse(self.historical(Path("/mnt/storage/meta/appData/prowlarr/prowlarr.db.bak")))
        self.assertFalse(self.historical(directory / "nested/library.db.bak"))

if __name__ == "__main__":
    unittest.main()

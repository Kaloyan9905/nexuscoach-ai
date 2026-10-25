"""Unit tests for LCU lockfile parsing and watcher event triggers."""

import tempfile
import unittest
from pathlib import Path
from nexuscoach.lcu.lockfile import parse_lockfile
from nexuscoach.lcu.watcher import LCUWatcher

class TestLCUWatcher(unittest.TestCase):

    def test_parse_lockfile_format(self):
        with tempfile.NamedTemporaryFile("w+", delete=False) as f:
            f.write("LeagueClient:1234:56789:testPassword123:https\n")
            f_path = Path(f.name)

        try:
            creds = parse_lockfile(f_path)
            self.assertIsNotNone(creds)
            self.assertEqual(creds["process"], "LeagueClient")
            self.assertEqual(creds["pid"], "1234")
            self.assertEqual(creds["port"], "56789")
            self.assertEqual(creds["password"], "testPassword123")
            self.assertEqual(creds["protocol"], "https")
        finally:
            f_path.unlink(missing_ok=True)

    def test_watcher_simulation_triggers_callback(self):
        called = False

        def callback():
            nonlocal called
            called = True

        watcher = LCUWatcher(on_match_end=callback)
        watcher.simulate_match_end()
        self.assertTrue(called)

if __name__ == "__main__":
    unittest.main()

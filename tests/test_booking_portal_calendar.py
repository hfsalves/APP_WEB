"""Exercise the actual inline calendar without booking writes or a live database."""

from pathlib import Path
import shutil
import subprocess
import unittest


ROOT = Path(__file__).resolve().parents[1]
BUNDLED_NODE = Path.home() / ".cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node"
NODE = shutil.which("node") or (str(BUNDLED_NODE) if BUNDLED_NODE.is_file() else None)


class BookingPortalCalendarTests(unittest.TestCase):
    @unittest.skipUnless(NODE, "Node.js is required for the isolated calendar behavior checks")
    def test_real_calendar_editor_events_dates_policies_and_desktop_reset(self):
        result = subprocess.run(
            [NODE, str(ROOT / "tests/booking_portal_calendar.test.js")],
            cwd=ROOT, capture_output=True, text=True, timeout=10,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("9/9 calendar behavior checks passed", result.stdout)


if __name__ == "__main__":
    unittest.main()

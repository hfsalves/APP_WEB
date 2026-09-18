"""Run actual guest-picker JavaScript handlers against controlled focus transitions."""

from pathlib import Path
import shutil
import subprocess
import unittest


ROOT = Path(__file__).resolve().parents[1]
BUNDLED_NODE = Path.home() / ".cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node"
NODE = shutil.which("node") or (str(BUNDLED_NODE) if BUNDLED_NODE.is_file() else None)


class BookingPortalGuestPickerFocusTests(unittest.TestCase):
    @unittest.skipUnless(NODE, "Node.js is required for the isolated guest-picker behavior checks")
    def test_real_javascript_focus_click_keyboard_and_input_handlers(self):
        result = subprocess.run(
            [NODE, str(ROOT / "tests/booking_portal_search_focus.test.js")],
            cwd=ROOT, capture_output=True, text=True, timeout=10,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("7/7 guest-picker behavior checks passed", result.stdout)


if __name__ == "__main__":
    unittest.main()

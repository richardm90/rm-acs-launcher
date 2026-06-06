"""Tests for the launch-time .hod session-file validation in launcher.launch.

Run with:  python3 -m unittest discover -s tests

Background: ACS launches an emulator session by being handed the path to a
.hod file. When that path is wrong (e.g. a case mismatch on a case-sensitive
filesystem, as seen in the field where config held MYIBMI.COM.hod but the file
was myibmi.com.hod), ACS exits silently with rc=0. The launcher's
"still running / rc=0 => success" heuristic then reported "Launched
successfully" while nothing opened. We now validate .hod arguments up front.
"""
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from acs_launcher import launcher  # noqa: E402


class MissingSessionFilesTests(unittest.TestCase):
    def test_missing_hod_is_reported(self):
        self.assertEqual(
            launcher._missing_session_files(["/x/nope.hod"]), "/x/nope.hod"
        )

    def test_case_insensitive_extension(self):
        self.assertEqual(
            launcher._missing_session_files(["/x/nope.HOD"]), "/x/nope.HOD"
        )

    def test_no_hod_argument(self):
        self.assertIsNone(launcher._missing_session_files(["/bin/echo", "hi"]))

    def test_existing_hod_passes(self):
        with tempfile.NamedTemporaryFile(suffix=".hod") as f:
            self.assertIsNone(launcher._missing_session_files([f.name]))


class LaunchValidationTests(unittest.TestCase):
    def test_missing_hod_fails_without_spawning(self):
        ok, msg = launcher.launch("/bin/echo /tmp/definitely-absent.hod")
        self.assertFalse(ok)
        self.assertIn("file not found", msg)

    def test_existing_hod_launches(self):
        with tempfile.NamedTemporaryFile(suffix=".hod") as f:
            ok, msg = launcher.launch("/bin/echo " + f.name)
            self.assertTrue(ok)

    def test_command_without_hod_is_unaffected(self):
        ok, msg = launcher.launch("/bin/echo hello")
        self.assertTrue(ok)


if __name__ == "__main__":
    unittest.main()

"""Tests for the ACS logon PTY parsing in acs_launcher.launcher.

Run with:  python3 -m unittest discover -s tests

These exercise the prompt-detection and output-evaluation logic that caused
the intermittent "Logon failed (rc=-9)" error: the password was never fed to
ACS because the prompt wasn't recognised (missing trailing space, or the
username and password prompts arriving coalesced in one read chunk), so the
logon loop idled to its timeout and the child was SIGKILLed (rc=-9).
"""
import os
import sys
import textwrap
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Importing launcher pulls in logging_setup but not GTK, so this is safe.
from acs_launcher import launcher  # noqa: E402


class EndsWithPromptTests(unittest.TestCase):
    def test_classic_prompt_with_trailing_space(self):
        self.assertTrue(launcher._ends_with_prompt(b"User (richardm): "))

    def test_prompt_without_trailing_space(self):
        # The chunk boundary split the space off after the colon (the failure
        # seen in the field, where the log line ended "Password:").
        self.assertTrue(launcher._ends_with_prompt(b"Password:"))

    def test_prompt_with_trailing_tab(self):
        self.assertTrue(launcher._ends_with_prompt(b"Password:\t"))

    def test_coalesced_banner_and_prompts(self):
        buf = b"Signon to IBM i (IUG1); User (richardm): Password: "
        self.assertTrue(launcher._ends_with_prompt(buf))

    def test_only_last_line_considered(self):
        self.assertTrue(launcher._ends_with_prompt(b"some banner: text\nPassword: "))
        self.assertFalse(launcher._ends_with_prompt(b"Password: \nnow running"))

    def test_non_prompt(self):
        self.assertFalse(launcher._ends_with_prompt(b"connecting to host"))
        self.assertFalse(launcher._ends_with_prompt(b""))


class EvaluateLogonOutputTests(unittest.TestCase):
    def test_success_phrase(self):
        ok, msg = launcher._evaluate_logon_output("...completed successfully\n", 0)
        self.assertTrue(ok)

    def test_msg_failure_line(self):
        ok, msg = launcher._evaluate_logon_output("MSG1234 bad password\n", 1)
        self.assertFalse(ok)
        self.assertIn("MSG1234", msg)

    def test_rc_zero_no_completion_line(self):
        ok, _ = launcher._evaluate_logon_output("some chatter\n", 0)
        self.assertTrue(ok)

    def test_kill_rc_minus_9(self):
        # The field failure: timed-out loop killed the child (SIGKILL).
        ok, msg = launcher._evaluate_logon_output(
            "Signon to IBM i (IUG1); User (richardm): Password:", -9
        )
        self.assertFalse(ok)
        self.assertIn("rc=-9", msg)


def _write_fake_acs(path, script):
    """Write a fake `acslaunch` that emits prompts and reads replies, so the
    real _run_logon_pty loop can be driven end-to-end over a PTY."""
    path.write_text(script)
    os.chmod(path, 0o755)


class RunLogonPtyTests(unittest.TestCase):
    """Drive the real PTY loop against a scripted fake ACS child."""

    def _make_child(self, body):
        import tempfile
        import pathlib

        d = tempfile.mkdtemp()
        p = pathlib.Path(d) / "fake_acs.py"
        _write_fake_acs(p, "#!/usr/bin/env python3\n" + textwrap.dedent(body))
        return str(p)

    def test_coalesced_prompts_password_is_sent(self):
        # The hard case: username + password prompts in a single write, with no
        # further output afterwards. The old positional logic would never send
        # the password here.
        child = self._make_child(
            """
            import sys
            # Both prompts at once, no trailing newline, then block on input.
            sys.stdout.write("Signon to IBM i (IUG1); User (richardm): Password: ")
            sys.stdout.flush()
            pw = sys.stdin.readline().strip()
            if pw == "s3cret":
                sys.stdout.write("\\nLogon completed successfully\\n")
            else:
                sys.stdout.write("\\nMSG0001 Login failed\\n")
            sys.stdout.flush()
            """
        )
        ok, msg = launcher._run_logon_pty(
            f"{sys.executable} {child}", "s3cret", timeout=10
        )
        self.assertTrue(ok, msg)

    def test_separate_prompts_password_is_sent(self):
        child = self._make_child(
            """
            import sys
            sys.stdout.write("User (richardm): ")
            sys.stdout.flush()
            sys.stdin.readline()           # username (blank line)
            sys.stdout.write("Password: ")
            sys.stdout.flush()
            pw = sys.stdin.readline().strip()
            if pw == "s3cret":
                sys.stdout.write("\\nLogon completed successfully\\n")
            sys.stdout.flush()
            """
        )
        ok, msg = launcher._run_logon_pty(
            f"{sys.executable} {child}", "s3cret", timeout=10
        )
        self.assertTrue(ok, msg)

    def test_bad_password_reports_failure_without_timing_out(self):
        import time

        child = self._make_child(
            """
            import sys
            sys.stdout.write("Password: ")
            sys.stdout.flush()
            sys.stdin.readline()
            sys.stdout.write("\\nMSG0001 Login failed\\n")
            sys.stdout.flush()
            """
        )
        start = time.monotonic()
        ok, msg = launcher._run_logon_pty(
            f"{sys.executable} {child}", "wrong", timeout=10
        )
        elapsed = time.monotonic() - start
        self.assertFalse(ok)
        self.assertIn("Login failed", msg)
        self.assertLess(elapsed, 5, "should not idle to the full timeout")


if __name__ == "__main__":
    unittest.main()

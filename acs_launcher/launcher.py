import os
import pty
import select
import shlex
import subprocess
import tempfile
import termios
import time

from acs_launcher import logging_setup

log = logging_setup.get_logger()

# Env vars worth logging when a launch fails. Logging the full env risks
# capturing secrets inherited from the shell, so we whitelist the ones
# that actually affect ACS/Java behaviour.
_LOGGED_ENV_KEYS = ("JAVA_TOOL_OPTIONS", "LANG", "LC_ALL", "DISPLAY")


def _english_env():
    """Subprocess env that forces ACS prompts and message text into English.

    Why: prompt detection and MSG/CPF parsing match English literals; without
    this, a user with LANG=de_DE.UTF-8 would see localised strings and our
    parser would silently fail. Only used for the logon path, where we read
    the subprocess's output. The launch path uses _launch_env() instead so
    the JVM doesn't print its "Picked up JAVA_TOOL_OPTIONS" notice to stderr
    (which `acslaunch` then exits rc=1 on, producing a spurious error).
    """
    env = os.environ.copy()
    env["LANG"] = "C.UTF-8"
    env["LC_ALL"] = "C.UTF-8"
    existing = env.get("JAVA_TOOL_OPTIONS", "")
    forced = "-Duser.language=en -Duser.country=US"
    env["JAVA_TOOL_OPTIONS"] = (existing + " " + forced).strip() if existing else forced
    return env


def _launch_env():
    """Subprocess env for fire-and-forget launches. Inherits the caller's
    environment unchanged — we don't parse the child's output, so the locale
    doesn't matter, and avoiding JAVA_TOOL_OPTIONS keeps the JVM quiet."""
    return os.environ.copy()


def build_placeholders(config, system, user, password):
    """Build the placeholder dict for command substitution.

    Merges global settings, system info, and system custom fields into a
    single flat dict of {placeholder_name: value}.
    """
    placeholders = {
        "system": system["name"],
        "user": user,
        "password": password or "",
        "acs_exe": config.get("acs_exe_path", ""),
        "acs_jar": config.get("acs_jar_path", ""),
        "java": config.get("java_path", "java"),
    }
    for key, value in system.get("fields", {}).items():
        placeholders[key] = value
    return placeholders


def substitute(cmd_template, placeholders):
    """Replace {placeholder} tokens in a command string.

    Returns the substituted command string.
    Raises KeyError if a placeholder is referenced but not available.
    """
    return cmd_template.format(**placeholders)


def run_logon(cmd_string, password=None, timeout=30):
    """Run a logon command (blocking) and return (success, message).

    If `password` is None (legacy), the command is run with stdin=DEVNULL —
    the password must already be embedded in `cmd_string` as `/password=...`.

    If `password` is provided, the command is attached to a PTY and the
    password is fed to the ACS prompt interactively. The cmd_string MUST
    NOT include `/password=...` in this mode (ACS would skip the prompt
    and our driver would hang waiting for a prompt that never arrives).
    The password never appears on the subprocess argv.
    """
    if password:
        logging_setup.add_secret(password)
    log.info("run_logon: cmd=%s mode=%s", cmd_string, "pty" if password else "argv")
    try:
        if password is not None:
            ok, msg = _run_logon_pty(cmd_string, password, timeout)
            log.info("run_logon: result ok=%s msg=%s", ok, msg)
            return ok, msg

        try:
            args = shlex.split(cmd_string)
            proc = subprocess.Popen(
                args,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                env=_english_env(),
            )
            output_lines = []
            failed = False
            succeeded = False
            try:
                while True:
                    line = proc.stdout.readline()
                    if not line:
                        break
                    line = line.strip()
                    if line:
                        output_lines.append(line)
                    if "Login failed" in line or "Signon to" in line:
                        failed = True
                        break
                    if "completed successfully" in line:
                        succeeded = True
                        break
            except Exception:
                pass

            if failed:
                proc.kill()
                proc.wait()
                errors = [l for l in output_lines if l.startswith("MSG") or l.startswith("CPF")]
                detail = "; ".join(errors) if errors else "; ".join(output_lines[:3])
                log.info("run_logon: failed detail=%s", detail)
                return False, f"Logon failed: {detail}"

            if succeeded:
                proc.wait(timeout=5)
                log.info("run_logon: succeeded")
                return True, "Logon successful"

            proc.wait(timeout=timeout)
            if proc.returncode == 0:
                log.info("run_logon: succeeded (rc=0, no completion line)")
                return True, "Logon successful"
            detail = "; ".join(output_lines[:3]) if output_lines else "no output"
            log.info("run_logon: failed rc=%d detail=%s", proc.returncode, detail)
            return False, f"Logon failed (rc={proc.returncode}): {detail}"

        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()
            log.info("run_logon: timed out")
            return False, "Logon timed out"
        except Exception as e:
            log.exception("run_logon: unexpected error")
            return False, f"Logon error: {e}"
    finally:
        logging_setup.clear_secrets()


def _ends_with_prompt(buf):
    """True if `buf` ends with a prompt-like fragment (last line ends with a
    colon, optionally followed by whitespace).

    ACS prints its prompts ("User (richardm): ", "Password: ") via
    Console.readLine/readPassword with no trailing newline, so the banner and
    both prompts coalesce onto one line. We must not require a trailing space:
    an os.read() chunk boundary can split the space off after the colon (or the
    prompt may emit no space at all), and a missing match here means the
    password is never sent and the logon loop times out (rc=-9). Matching a
    trailing ':' plus optional spaces is robust to that timing race.
    """
    if not buf:
        return False
    nl = buf.rfind(b"\n")
    tail = bytes(buf[nl + 1:]) if nl >= 0 else bytes(buf)
    return tail.rstrip(b" \t").endswith(b":")


def _drain_master(master_fd, output, max_secs):
    """Read any remaining bytes from `master_fd` for up to `max_secs`."""
    deadline = time.monotonic() + max_secs
    while time.monotonic() < deadline:
        r, _, _ = select.select([master_fd], [], [], 0.1)
        if master_fd not in r:
            break
        try:
            chunk = os.read(master_fd, 4096)
        except OSError:
            break
        if not chunk:
            break
        output.extend(chunk)


def _evaluate_logon_output(text, returncode):
    """Decide success/failure from the captured output and exit code."""
    if "completed successfully" in text:
        return True, "Logon successful"
    failure_lines = [
        s for s in (l.strip() for l in text.splitlines())
        if s.startswith("MSG") or s.startswith("CPF")
    ]
    if failure_lines:
        return False, f"Logon failed: {'; '.join(failure_lines)}"
    if returncode == 0:
        return True, "Logon successful"
    nonempty = [l.strip() for l in text.splitlines() if l.strip()]
    detail = "; ".join(nonempty[:3]) if nonempty else "no output"
    return False, f"Logon failed (rc={returncode}): {detail}"


def _run_logon_pty(cmd_string, password, timeout):
    """Drive `acslaunch /plugin=logon` over a PTY, feeding the password
    to the prompt instead of placing it on the command line."""
    args = shlex.split(cmd_string)
    master_fd, slave_fd = pty.openpty()
    proc = None
    output = bytearray()
    user_sent = False
    pwd_sent = False
    try:
        # Pre-disable echo so the password doesn't echo back into our buffer
        # and to avoid a race with Java's Console.readPassword disabling echo
        # only after our write has already arrived.
        attrs = termios.tcgetattr(slave_fd)
        attrs[3] &= ~termios.ECHO
        termios.tcsetattr(slave_fd, termios.TCSANOW, attrs)

        proc = subprocess.Popen(
            args,
            stdin=slave_fd,
            stdout=slave_fd,
            stderr=slave_fd,
            close_fds=True,
            env=_english_env(),
        )
        os.close(slave_fd)
        slave_fd = -1

        deadline = time.monotonic() + timeout
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                break
            r, _, _ = select.select([master_fd], [], [], min(remaining, 0.2))
            if master_fd in r:
                try:
                    chunk = os.read(master_fd, 4096)
                except OSError:
                    chunk = b""
                if not chunk:
                    break
                output.extend(chunk)
                # Drive the prompts by content, not by "a new prompt appeared".
                # ACS can emit "User (richardm): Password: " coalesced into one
                # os.read() chunk; a positional check ("output grew since the
                # username prompt") would then never fire the password branch,
                # because ACS is already blocked waiting for the password and
                # emits nothing more — the loop would idle to its timeout (rc=-9).
                # The password prompt is unambiguous (it contains "Password"),
                # so send the password as soon as we see it.
                if not pwd_sent and _ends_with_prompt(output) and b"Password" in output:
                    if not user_sent:
                        # Username prompt was coalesced with the password prompt
                        # (or already satisfied by /userid=); just answer the password.
                        user_sent = True
                    os.write(master_fd, password.encode("utf-8") + b"\n")
                    pwd_sent = True
                elif not user_sent and _ends_with_prompt(output):
                    os.write(master_fd, b"\n")
                    user_sent = True
                # Early-break on a clear failure: ACS retries the prompt
                # after a bad password, so without this we'd idle until the
                # full timeout instead of returning the actual error.
                if pwd_sent and b"Login failed" in output:
                    break
            if proc.poll() is not None:
                _drain_master(master_fd, output, max_secs=0.5)
                break
    finally:
        if proc is not None and proc.poll() is None:
            proc.kill()
        try:
            os.close(master_fd)
        except OSError:
            pass
        if slave_fd >= 0:
            try:
                os.close(slave_fd)
            except OSError:
                pass
        if proc is not None:
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                pass

    text = output.decode("utf-8", errors="replace")
    rc = proc.returncode if proc is not None else -1
    return _evaluate_logon_output(text, rc)


def _missing_session_files(args):
    """Return the first .hod argument that points at a non-existent file.

    ACS launches an emulator session by being handed the path to a .hod file.
    If that path is wrong (e.g. a case mismatch on a case-sensitive
    filesystem), ACS exits silently with rc=0 — indistinguishable from success
    via exit code alone. We validate .hod arguments here so the caller can
    report a real failure. Returns None if all .hod args (if any) exist.
    """
    for arg in args:
        if arg.lower().endswith(".hod") and not os.path.isfile(arg):
            return arg
    return None


def launch(cmd_string, password=None):
    """Launch a command (fire-and-forget, detached from this process).

    Waits briefly to catch immediate failures (e.g. bad path, missing file).
    Returns (success, message).

    `password`, if given, is registered with the log redactor so any custom
    launch_cmd template that embeds {password} doesn't write it to the log.
    """
    if password:
        logging_setup.add_secret(password)
    # Use temp files (not PIPEs) so the child can keep writing past the 2s
    # window without us holding fds it would otherwise block on.
    out_f = tempfile.TemporaryFile()
    err_f = tempfile.TemporaryFile()
    try:
        args = shlex.split(cmd_string)
        env = _launch_env()
        env_summary = {k: env.get(k, "") for k in _LOGGED_ENV_KEYS}
        log.info("launch: cmd=%s", cmd_string)
        log.debug("launch: argv=%r env=%r", args, env_summary)
        # ACS exits quietly (rc=0, no stderr) when handed a .hod session file
        # that doesn't exist, which our "still running / rc=0" heuristics would
        # otherwise report as a successful launch. Catch the missing file up
        # front so the user gets a real error instead of a false success.
        missing = _missing_session_files(args)
        if missing:
            log.warning("launch: session file not found: %s", missing)
            return False, f"Launch failed: file not found — {missing}"
        try:
            proc = subprocess.Popen(
                args,
                start_new_session=True,
                stdout=out_f,
                stderr=err_f,
                env=env,
            )
        except FileNotFoundError:
            log.warning("launch: command not found: %s", args[0] if args else "")
            return False, f"Launch error: command not found — {args[0] if args else ''}"

        try:
            proc.wait(timeout=2)
            out_f.seek(0)
            err_f.seek(0)
            stdout = out_f.read().decode("utf-8", errors="replace").strip()
            stderr = err_f.read().decode("utf-8", errors="replace").strip()
            log.info(
                "launch: exited within 2s rc=%d stdout_len=%d stderr_len=%d",
                proc.returncode, len(stdout), len(stderr),
            )
            if stdout:
                log.debug("launch: stdout=%s", stdout)
            if stderr:
                log.debug("launch: stderr=%s", stderr)
            if proc.returncode != 0 and stderr:
                return False, f"Launch failed (rc={proc.returncode}): {stderr[:200]}"
            return True, "Launched successfully"
        except subprocess.TimeoutExpired:
            log.info("launch: still running after 2s (treating as success)")
            return True, "Launched successfully"
    except Exception as e:
        log.exception("launch: unexpected error")
        return False, f"Launch error: {e}"
    finally:
        # Don't close the temp files if the child is still running — it
        # still holds them via its inherited fds and will write to them
        # until it exits. They'll be reclaimed when the child closes them.
        logging_setup.clear_secrets()

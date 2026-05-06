import os
import pty
import select
import shlex
import subprocess
import termios
import time


def _english_env():
    """Subprocess env that forces ACS prompts and message text into English.

    Why: prompt detection and MSG/CPF parsing match English literals; without
    this, a user with LANG=de_DE.UTF-8 would see localised strings and our
    parser would silently fail.
    """
    env = os.environ.copy()
    env["LANG"] = "C.UTF-8"
    env["LC_ALL"] = "C.UTF-8"
    existing = env.get("JAVA_TOOL_OPTIONS", "")
    forced = "-Duser.language=en -Duser.country=US"
    env["JAVA_TOOL_OPTIONS"] = (existing + " " + forced).strip() if existing else forced
    return env


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
    if password is not None:
        return _run_logon_pty(cmd_string, password, timeout)
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
            # Extract the most useful error line (MSG... lines)
            errors = [l for l in output_lines if l.startswith("MSG") or l.startswith("CPF")]
            detail = "; ".join(errors) if errors else "; ".join(output_lines[:3])
            return False, f"Logon failed: {detail}"

        if succeeded:
            proc.wait(timeout=5)
            return True, "Logon successful"

        # Process ended without clear success/failure — check exit code
        proc.wait(timeout=timeout)
        if proc.returncode == 0:
            return True, "Logon successful"
        detail = "; ".join(output_lines[:3]) if output_lines else "no output"
        return False, f"Logon failed (rc={proc.returncode}): {detail}"

    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait()
        return False, "Logon timed out"
    except Exception as e:
        return False, f"Logon error: {e}"


def _ends_with_prompt(buf):
    """True if `buf` ends with a prompt-like fragment (last line ends with ': ')."""
    if not buf:
        return False
    nl = buf.rfind(b"\n")
    tail = bytes(buf[nl + 1:]) if nl >= 0 else bytes(buf)
    return tail.endswith(b": ")


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
    prompt_after_user = 0
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
                if not user_sent and _ends_with_prompt(output):
                    os.write(master_fd, b"\n")
                    user_sent = True
                    prompt_after_user = len(output)
                elif (user_sent and not pwd_sent
                      and len(output) > prompt_after_user
                      and _ends_with_prompt(output)):
                    os.write(master_fd, password.encode("utf-8") + b"\n")
                    pwd_sent = True
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


def launch(cmd_string):
    """Launch a command (fire-and-forget, detached from this process).

    Waits briefly to catch immediate failures (e.g. bad path, missing file).
    Returns (success, message).
    """
    try:
        args = shlex.split(cmd_string)
        proc = subprocess.Popen(
            args,
            start_new_session=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            env=_english_env(),
        )
        # Wait briefly to catch immediate crashes
        try:
            proc.wait(timeout=2)
            # Process exited within 2s — likely an error
            stderr = proc.stderr.read().decode("utf-8", errors="replace").strip()
            proc.stderr.close()
            if proc.returncode != 0 and stderr:
                return False, f"Launch failed (rc={proc.returncode}): {stderr[:200]}"
            return True, "Launched successfully"
        except subprocess.TimeoutExpired:
            # Still running after 2s — that's the expected case
            proc.stderr.close()
            return True, "Launched successfully"
    except FileNotFoundError:
        return False, f"Launch error: command not found — {shlex.split(cmd_string)[0]}"
    except Exception as e:
        return False, f"Launch error: {e}"

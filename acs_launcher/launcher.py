import shlex
import subprocess


def build_placeholders(config, system, user, password):
    """Build the placeholder dict for command substitution.

    Merges global settings, system info, and system custom fields into a
    single flat dict of {placeholder_name: value}.
    """
    placeholders = {
        "system": system["name"],
        "user": user,
        "password": password or "",
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


def run_logon(cmd_string, timeout=30):
    """Run a logon command (blocking) and return (success, message).

    Reads output line-by-line to detect success/failure quickly.
    ACS logon doesn't use exit codes reliably — on failure it prints an
    error then drops to an interactive prompt, so we detect failure from
    the output and kill the process early.
    """
    try:
        args = shlex.split(cmd_string)
        proc = subprocess.Popen(
            args,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
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

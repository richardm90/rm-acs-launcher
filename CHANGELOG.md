# Changelog

## 0.3.1

### Fixed

- Intermittent "Logon failed (rc=-9): Picked up JAVA_TOOL_OPTIONS…" message in the status bar when authenticating a 5250 (or other logon-gated) session, even though logon had actually succeeded. The PTY prompt detector required the prompt to end with `": "` (colon + space) and expected the username and password prompts to arrive as two separate reads; depending on `os.read` chunk-boundary timing the trailing space could be split off, or the two prompts could coalesce into one chunk, so the password was never sent and the logon loop idled to its 30 s timeout and SIGKILLed the child (rc=-9). The detector now tolerates a missing trailing space and drives the password from the prompt's content (`Password`) rather than its position. Added a `tests/` suite (stdlib `unittest`, no new dependencies) covering both failure modes.

## 0.3.0

### Added

- Diagnostic launch logging. Each launch attempt is recorded to `~/.local/state/rm-acs-launcher/launcher.log` (rotating, 1 MB × 3) including the command, return code, and full stdout/stderr — useful for diagnosing launches that fail or report a spurious error in the status bar. Passwords are redacted from the log via both per-launch secret masking and a regex pass over common password flags.
- "Enable launch logging" toggle and "View log" button in Preferences. View log opens the file with the desktop's default text viewer via `xdg-open`.
- README instructions for pointing the launcher at a central configuration file via a symlink.

### Fixed

- Spurious "Launch failed (rc=1): Picked up JAVA_TOOL_OPTIONS…" message in the status bar when a launch succeeded. The JVM's informational `JAVA_TOOL_OPTIONS` notice is no longer triggered on the launch path — `JAVA_TOOL_OPTIONS` is now only set for the logon path, where output parsing genuinely needs locale-stable English text.

## 0.2.0

### Security

- Passwords are no longer placed on the ACS subprocess command line. The launcher now feeds the password to the ACS logon prompt over a pseudo-terminal, keeping it out of `/proc/<pid>/cmdline` where any local user could read it during the logon. Existing configurations using the previous default `logon_cmd` are migrated automatically; custom templates that still embed `{password}` keep working under the original behaviour.
- Tightened permissions on `~/.config/rm-acs-launcher/` to `0700` and `config.json` to `0600`. Existing installs are migrated on the next save.
- Forced `LANG=C.UTF-8` and `JAVA_TOOL_OPTIONS=-Duser.language=en` on the ACS subprocess so prompt and message parsing is locale-stable.

### Other

- Trim main window image
- Replace bundled function icons with Lucide-derived artwork; rename default fallback icon to `app-default.png` (existing configs are migrated automatically)

## 0.1.2

- Save last used system, user, and function when launching via quick access icons

## 0.1.1

- Fix dual panel icons by setting WM_CLASS and StartupWMClass
- Update application ID and keyring schema to com.github.richardm90.rm-acs-launcher

## 0.1.0

- Initial release of RM ACS Launcher
- GTK3 desktop application for launching IBM i ACS tools
- System, user, and function selection via dropdowns
- Password storage in GNOME Keyring via libsecret
- Configurable favourite quick-launch icon buttons
- Automatic logon with session-aware skip when already authenticated
- ACS launcher button for opening the default ACS GUI
- System Debugger function and auto-merge of new defaults into saved config
- ACS executable preference with `{acs_exe}` placeholder support
- Desktop integration with install/uninstall scripts (XDG conventions)
- Application icon with launcher badge
- Version numbering with status bar display

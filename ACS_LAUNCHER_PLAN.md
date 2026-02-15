# RM ACS Launcher - Implementation Plan

## Context

The user needs a desktop GUI application on Linux Mint that simplifies launching IBM i Access Client Solutions (ACS) tools. Currently, launching ACS requires manually typing long Java CLI commands with passwords. This app will provide a point-and-click launcher with system/user/function selection and automatic password retrieval from GNOME Keyring.

**Project location:** `/home/richard/git/rm-acs-launcher`

## Technology Stack

- **Python 3 + GTK3** (PyGObject) - native Linux Mint look, lightweight, pre-installed dependencies
- **libsecret** (gi.repository.Secret) - native GNOME Keyring integration for password storage
- **JSON config** at `~/.config/rm-acs-launcher/config.json` - no extra dependencies

## Project Structure

```
rm-acs-launcher/
  acs_launcher/
    __init__.py
    main.py              # Gtk.Application entry point
    window.py            # Main window with combos + Launch button
    config.py            # JSON config load/save (~/.config/rm-acs-launcher/)
    passwords.py         # GNOME Keyring via libsecret
    launcher.py          # Command builder + subprocess runner
    dialogs/
      __init__.py
      password_dialog.py         # Enter/update password prompt
      preferences_dialog.py      # ACS paths, Java options
      system_manager_dialog.py   # Add/edit/remove systems and users + custom fields
      function_manager_dialog.py # Add/edit/remove functions and their commands
  data/
    rm-acs-launcher.desktop  # Desktop menu entry
    config.example.json   # Example config
  install.sh              # Installation script
  uninstall.sh
```

## GUI Design

### Main Window (~450x350px)

```
+-------------------------------------------------+
|  RM ACS Launcher                         [_][X] |
+-------------------------------------------------+
|                                                 |
|  System:    [ Production (myibmi.com)    v ]    |
|  User:      [ richard                    v ]    |
|  Function:  [ 5250 - Terminal Emulator   v ]    |
|                                                 |
|              [    Launch    ]                   |
|                                                 |
|  [ Manage Passwords ]         [ Preferences ]   |
+-------------------------------------------------+
|  Ready                                          |
+-------------------------------------------------+
```

- System combo changes update User combo with that system's users
- Function combo shows all available ACS plugins
- Launch button disabled until all fields selected; disabled during launch
- Status bar shows progress: "Authenticating...", "Launching...", errors

### Dialogs

1. **Password Dialog** - shown when no keyring password found; password entry with show/hide toggle, "Save to keyring" checkbox
2. **Preferences Dialog** - ACS jar path, Java path, Java options (with file Browse buttons)
3. **System Manager Dialog** - list of systems with Add/Edit/Remove buttons; each system has hostname, label, user list, and custom fields (e.g. `hod_file`). Custom fields are key/value pairs that can be referenced as placeholders in function commands.
4. **Function Manager Dialog** - list of functions with Add/Edit/Remove buttons; each function has an id, label, launch command, optional logon command, and a list of required system fields

## Core Launch Flow

1. User selects system, user, function and clicks Launch
2. Look up password from GNOME Keyring (`Secret.password_lookup_sync`)
3. If not found, show Password Dialog; optionally save to keyring
4. Build the command for the selected function:
   - If the function has a **logon command**, run it first (blocking, with timeout)
   - Substitute placeholders: `{system}`, `{user}`, `{password}`, plus any
     system-level custom fields (e.g. `{hod_file}`)
   - If logon fails, show error in status bar and stop
5. Run the function's **launch command** (fire-and-forget via `Popen`, detached)
   - Same placeholder substitution
6. Save last selections to config

Steps 4-6 run in a background thread; GTK updates via `GLib.idle_add()`.

## Functions (Customisable Commands)

Functions are user-defined in the config. Each function specifies:
- **id** - unique identifier
- **label** - display name in the dropdown
- **launch_cmd** - the command to execute (with placeholder substitution)
- **logon_cmd** *(optional)* - a command to run before launch_cmd (e.g. ACS logon)
- **system_fields** *(optional)* - list of extra field names this function requires
  from the system config (e.g. `["hod_file"]`)

### Placeholder Substitution

Commands support these placeholders, replaced at launch time:
- `{system}` - the system hostname (e.g. `myibmi.com`)
- `{user}` - the selected user profile
- `{password}` - the password from GNOME Keyring
- `{acs_jar}` - the configured ACS jar path
- `{java}` - the configured Java path
- Any system-level custom field: `{hod_file}`, `{lib}`, etc.

### Default Functions

The app ships with sensible defaults that can be edited/removed by the user:

| ID | Label | Launch Command |
|----|-------|----------------|
| 5250 | 5250 Terminal Emulator | `/opt/ibm/iAccessClientSolutions/Start_Programs/Linux_x86-64/acslaunch_linux-64 {hod_file}` |
| rss | Run SQL Scripts | `{java} -jar {acs_jar} /plugin=rss /system={system}` |
| db2 | Database Management | `{java} -jar {acs_jar} /plugin=db2 /system={system}` |
| ifs | IFS Browser | `{java} -jar {acs_jar} /plugin=ifs /system={system}` |
| splf | Printer Output (Spool) | `{java} -jar {acs_jar} /plugin=splf /system={system}` |
| rmtcmd | Remote Command | `{java} -jar {acs_jar} /plugin=rmtcmd /system={system}` |
| ssh | SSH Terminal | `{java} -jar {acs_jar} /plugin=ssh /system={system}` |
| cfg | System Configuration | `{java} -jar {acs_jar} /plugin=cfg /system={system}` |
| keyman | Certificate Management | `{java} -jar {acs_jar} /plugin=keyman /system={system}` |
| l1c | Navigator for i | `{java} -jar {acs_jar} /plugin=l1c /system={system}` |

The 5250 default uses the native `acslaunch_linux-64` launcher with a `.hod` file,
while others use the standard `java -jar` approach. All are fully editable.

Functions that reference system-level fields (like `{hod_file}`) will validate
that the selected system has that field configured before enabling Launch.

### Logon Commands

Some functions may require authentication before launch. The logon command is
optional and configured per-function. Default logon command (used by functions
that need ACS authentication):
```
{java} -jar {acs_jar} /plugin=logon /system={system} /userid={user} /password={password} /auth
```

Not all functions need a logon command — e.g. 5250 with a `.hod` file may handle
its own authentication, while `ssh` uses SSH keys. The user can add/remove logon
commands per function as needed.

## Config File Format

`~/.config/rm-acs-launcher/config.json`:
```json
{
  "acs_jar_path": "/opt/ibm/iAccessClientSolutions/acsbundle.jar",
  "java_path": "/usr/bin/java",
  "java_opts": "-Xmx1024m",
  "systems": [
    {
      "name": "myibmi.com",
      "label": "Production",
      "users": ["richard", "hal"],
      "fields": {
        "hod_file": "/home/richard/IBM/iAccessClient/Emulator/myibmi.com.hod"
      }
    }
  ],
  "functions": [
    {
      "id": "5250",
      "label": "5250 Terminal Emulator",
      "launch_cmd": "/opt/ibm/iAccessClientSolutions/Start_Programs/Linux_x86-64/acslaunch_linux-64 {hod_file}",
      "logon_cmd": null,
      "system_fields": ["hod_file"]
    },
    {
      "id": "rss",
      "label": "Run SQL Scripts",
      "launch_cmd": "{java} -jar {acs_jar} /plugin=rss /system={system}",
      "logon_cmd": "{java} -jar {acs_jar} /plugin=logon /system={system} /userid={user} /password={password} /auth",
      "system_fields": []
    }
  ],
  "last_system": "myibmi.com",
  "last_user": "richard",
  "last_function": "5250"
}
```

## Password Management (passwords.py)

Uses native `gi.repository.Secret` API (not `secret-tool` CLI):
- **Schema:** `com.github.richard.acslauncher` with attributes: service, system, user
- **lookup(system, user)** - returns password or None
- **store(system, user, password)** - saves with label "RM ACS system/user"
- **clear(system, user)** - removes credential
- **has_password(system, user)** - existence check

## Implementation Order

1. `config.py` - config load/save with defaults (including default functions)
2. `passwords.py` - libsecret integration
3. `launcher.py` - placeholder substitution + subprocess runner
4. `main.py` - Gtk.Application entry point
5. `window.py` - main window with all widgets and launch flow
6. `dialogs/password_dialog.py` - password entry
7. `dialogs/system_manager_dialog.py` - add/edit/remove systems, users, and custom fields
8. `dialogs/function_manager_dialog.py` - add/edit/remove functions and commands
9. `dialogs/preferences_dialog.py` - ACS/Java path settings
10. `data/` + `install.sh` - desktop integration

## Known Limitations

- Password is briefly visible in process list during ACS logon (ACS limitation - no stdin/env var option)
- ACS credential cache duration is undocumented; logon runs immediately before each plugin launch to mitigate
- Requires GNOME Keyring to be unlocked (automatic on desktop login)

## Verification

1. Launch app: `python3 /home/richard/git/rm-acs-launcher/acs_launcher/main.py`
2. Add a system via System Manager dialog
3. Select system/user/function, click Launch
4. Verify password dialog appears (first time), enter password
5. Verify ACS logon runs and plugin window opens
6. Close and reopen - verify last selections are restored
7. Open Manage Passwords - verify stored credentials listed
8. Verify password retrieval from keyring works on subsequent launches (no prompt)

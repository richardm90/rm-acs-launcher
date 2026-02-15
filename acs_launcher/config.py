import json
import os
import copy

CONFIG_DIR = os.path.expanduser("~/.config/rm-acs-launcher")
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")
ICONS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data", "icons",
)

DEFAULT_FUNCTIONS = [
    {
        "id": "5250",
        "label": "5250 Terminal Emulator",
        "launch_cmd": "{acs_exe} {hod_file}",
        "requires_logon": True,
        "system_fields": ["hod_file"],
        "is_favourite": True,
        "icon_path": "5250.png",
    },
    {
        "id": "rss",
        "label": "Run SQL Scripts",
        "launch_cmd": "{java} -jar {acs_jar} /plugin=rss /system={system}",
        "requires_logon": True,
        "system_fields": [],
        "is_favourite": True,
        "icon_path": "rss.png",
    },
    {
        "id": "db2",
        "label": "Database Management",
        "launch_cmd": "{java} -jar {acs_jar} /plugin=db2 /system={system}",
        "requires_logon": True,
        "system_fields": [],
        "is_favourite": True,
        "icon_path": "db2.png",
    },
    {
        "id": "ifs",
        "label": "IFS Browser",
        "launch_cmd": "{java} -jar {acs_jar} /plugin=ifs /system={system}",
        "requires_logon": True,
        "system_fields": [],
        "is_favourite": True,
        "icon_path": "ifs.png",
    },
    {
        "id": "splf",
        "label": "Printer Output (Spool Files)",
        "launch_cmd": "{java} -jar {acs_jar} /plugin=splf /system={system}",
        "requires_logon": True,
        "system_fields": [],
        "is_favourite": True,
        "icon_path": "splf.png",
    },
    {
        "id": "rmtcmd",
        "label": "Remote Command",
        "launch_cmd": "{java} -jar {acs_jar} /plugin=rmtcmd /system={system}",
        "requires_logon": True,
        "system_fields": [],
        "is_favourite": False,
        "icon_path": "acs-logo.png",
    },
    {
        "id": "ssh",
        "label": "SSH Terminal",
        "launch_cmd": "{java} -jar {acs_jar} /plugin=ssh /system={system}",
        "requires_logon": False,
        "system_fields": [],
        "is_favourite": False,
        "icon_path": "acs-logo.png",
    },
    {
        "id": "cfg",
        "label": "System Configuration",
        "launch_cmd": "{java} -jar {acs_jar} /plugin=cfg /system={system}",
        "requires_logon": False,
        "system_fields": [],
        "is_favourite": False,
        "icon_path": "acs-logo.png",
    },
    {
        "id": "keyman",
        "label": "Certificate Management",
        "launch_cmd": "{java} -jar {acs_jar} /plugin=keyman /system={system}",
        "requires_logon": False,
        "system_fields": [],
        "is_favourite": False,
        "icon_path": "acs-logo.png",
    },
    {
        "id": "l1c",
        "label": "Navigator for i",
        "launch_cmd": "{java} -jar {acs_jar} /plugin=l1c /system={system}",
        "requires_logon": True,
        "system_fields": [],
        "is_favourite": False,
        "icon_path": "acs-logo.png",
    },
    {
        "id": "sysdbg",
        "label": "System Debugger",
        "launch_cmd": "{java} -jar {acs_jar} /plugin=sysdbg /system={system}",
        "requires_logon": True,
        "system_fields": [],
        "is_favourite": True,
        "icon_path": "sysdbg.png",
    },
]

DEFAULT_CONFIG = {
    "acs_exe_path": "/opt/ibm/iAccessClientSolutions/Start_Programs/Linux_x86-64/acslaunch_linux-64",
    "acs_jar_path": "/opt/ibm/iAccessClientSolutions/acsbundle.jar",
    "java_path": "/usr/bin/java",
    "java_opts": "-Xmx1024m",
    "logon_cmd": "{acs_exe} /plugin=logon /system={system} /userid={user} /password={password} /auth",
    "systems": [],
    "functions": DEFAULT_FUNCTIONS,
    "last_system": "",
    "last_user": "",
    "last_function": "",
}


def load_config():
    """Load config from disk, returning defaults for missing keys."""
    config = copy.deepcopy(DEFAULT_CONFIG)
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                saved = json.load(f)
            for key in config:
                if key in saved:
                    config[key] = saved[key]
        except (json.JSONDecodeError, OSError):
            pass
    return config


def save_config(config):
    """Save config to disk, creating the directory if needed."""
    os.makedirs(CONFIG_DIR, exist_ok=True)
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=2)


def get_system(config, system_name):
    """Find a system dict by name, or None."""
    for s in config["systems"]:
        if s["name"] == system_name:
            return s
    return None


def get_function(config, function_id):
    """Find a function dict by id, or None."""
    for fn in config["functions"]:
        if fn["id"] == function_id:
            return fn
    return None


def get_default_icon(function_id):
    """Return the default icon_path for a built-in function, or empty string."""
    for fn in DEFAULT_FUNCTIONS:
        if fn["id"] == function_id:
            return fn.get("icon_path", "")
    return ""


def resolve_icon_path(icon_path, function_id=None):
    """Resolve an icon path. Bare filenames are looked up in the bundled icons dir.
    If icon_path is empty and function_id is given, falls back to the built-in default."""
    if not icon_path and function_id:
        icon_path = get_default_icon(function_id)
    if not icon_path:
        return ""
    if os.path.sep not in icon_path and "/" not in icon_path:
        return os.path.join(ICONS_DIR, icon_path)
    return icon_path


def system_has_required_fields(system, function):
    """Check if a system has all custom fields required by a function."""
    fields = system.get("fields", {})
    for field_name in function.get("system_fields", []):
        if not fields.get(field_name):
            return False
    return True

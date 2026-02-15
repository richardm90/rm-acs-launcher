import json
import os
import copy

CONFIG_DIR = os.path.expanduser("~/.config/rm-acs-launcher")
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")

DEFAULT_FUNCTIONS = [
    {
        "id": "5250",
        "label": "5250 Terminal Emulator",
        "launch_cmd": "/opt/ibm/iAccessClientSolutions/Start_Programs/Linux_x86-64/acslaunch_linux-64 {hod_file}",
        "logon_cmd": "{java} -jar {acs_jar} /plugin=logon /system={system} /userid={user} /password={password} /auth",
        "system_fields": ["hod_file"],
    },
    {
        "id": "rss",
        "label": "Run SQL Scripts",
        "launch_cmd": "{java} -jar {acs_jar} /plugin=rss /system={system}",
        "logon_cmd": "{java} -jar {acs_jar} /plugin=logon /system={system} /userid={user} /password={password} /auth",
        "system_fields": [],
    },
    {
        "id": "db2",
        "label": "Database Management",
        "launch_cmd": "{java} -jar {acs_jar} /plugin=db2 /system={system}",
        "logon_cmd": "{java} -jar {acs_jar} /plugin=logon /system={system} /userid={user} /password={password} /auth",
        "system_fields": [],
    },
    {
        "id": "ifs",
        "label": "IFS Browser",
        "launch_cmd": "{java} -jar {acs_jar} /plugin=ifs /system={system}",
        "logon_cmd": "{java} -jar {acs_jar} /plugin=logon /system={system} /userid={user} /password={password} /auth",
        "system_fields": [],
    },
    {
        "id": "splf",
        "label": "Printer Output (Spool Files)",
        "launch_cmd": "{java} -jar {acs_jar} /plugin=splf /system={system}",
        "logon_cmd": "{java} -jar {acs_jar} /plugin=logon /system={system} /userid={user} /password={password} /auth",
        "system_fields": [],
    },
    {
        "id": "rmtcmd",
        "label": "Remote Command",
        "launch_cmd": "{java} -jar {acs_jar} /plugin=rmtcmd /system={system}",
        "logon_cmd": "{java} -jar {acs_jar} /plugin=logon /system={system} /userid={user} /password={password} /auth",
        "system_fields": [],
    },
    {
        "id": "ssh",
        "label": "SSH Terminal",
        "launch_cmd": "{java} -jar {acs_jar} /plugin=ssh /system={system}",
        "logon_cmd": None,
        "system_fields": [],
    },
    {
        "id": "cfg",
        "label": "System Configuration",
        "launch_cmd": "{java} -jar {acs_jar} /plugin=cfg /system={system}",
        "logon_cmd": None,
        "system_fields": [],
    },
    {
        "id": "keyman",
        "label": "Certificate Management",
        "launch_cmd": "{java} -jar {acs_jar} /plugin=keyman /system={system}",
        "logon_cmd": None,
        "system_fields": [],
    },
    {
        "id": "l1c",
        "label": "Navigator for i",
        "launch_cmd": "{java} -jar {acs_jar} /plugin=l1c /system={system}",
        "logon_cmd": "{java} -jar {acs_jar} /plugin=logon /system={system} /userid={user} /password={password} /auth",
        "system_fields": [],
    },
]

DEFAULT_CONFIG = {
    "acs_jar_path": "/opt/ibm/iAccessClientSolutions/acsbundle.jar",
    "java_path": "/usr/bin/java",
    "java_opts": "-Xmx1024m",
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


def system_has_required_fields(system, function):
    """Check if a system has all custom fields required by a function."""
    fields = system.get("fields", {})
    for field_name in function.get("system_fields", []):
        if not fields.get(field_name):
            return False
    return True

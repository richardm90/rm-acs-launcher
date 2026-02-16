import gi

gi.require_version("Secret", "1")
from gi.repository import Secret

SCHEMA = Secret.Schema.new(
    "com.github.richardm90.rm-acs-launcher",
    Secret.SchemaFlags.NONE,
    {
        "service": Secret.SchemaAttributeType.STRING,
        "system": Secret.SchemaAttributeType.STRING,
        "user": Secret.SchemaAttributeType.STRING,
    },
)

SERVICE_NAME = "rm-acs-launcher"


def _attrs(system, user):
    return {"service": SERVICE_NAME, "system": system, "user": user}


def lookup(system, user):
    """Look up a password from GNOME Keyring. Returns the password string or None."""
    return Secret.password_lookup_sync(SCHEMA, _attrs(system, user), None)


def store(system, user, password):
    """Store a password in GNOME Keyring."""
    label = f"RM ACS {system}/{user}"
    Secret.password_store_sync(
        SCHEMA,
        _attrs(system, user),
        Secret.COLLECTION_DEFAULT,
        label,
        password,
        None,
    )


def clear(system, user):
    """Remove a password from GNOME Keyring. Returns True if removed."""
    return Secret.password_clear_sync(SCHEMA, _attrs(system, user), None)


def has_password(system, user):
    """Check if a password exists in the keyring."""
    return lookup(system, user) is not None

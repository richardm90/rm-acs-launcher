#!/bin/bash
set -e

DESKTOP_FILE="$HOME/.local/share/applications/rm-acs-launcher.desktop"

echo "Uninstalling RM ACS Launcher..."

if [ -f "$DESKTOP_FILE" ]; then
    rm "$DESKTOP_FILE"
    echo "Desktop entry removed."
else
    echo "No desktop entry found."
fi

echo ""
echo "Note: Configuration at ~/.config/rm-acs-launcher/ and keyring passwords"
echo "have been left intact. Remove them manually if desired."

#!/bin/bash
set -e

APP_NAME="rm-acs-launcher"
INSTALL_DIR="$HOME/.local/share/$APP_NAME"
BIN_FILE="$HOME/.local/bin/$APP_NAME"
DESKTOP_FILE="$HOME/.local/share/applications/$APP_NAME.desktop"

echo "Uninstalling RM ACS Launcher..."

if [ -d "$INSTALL_DIR" ]; then
    rm -rf "$INSTALL_DIR"
    echo "App files removed: $INSTALL_DIR"
else
    echo "No app files found."
fi

if [ -f "$BIN_FILE" ]; then
    rm "$BIN_FILE"
    echo "Launcher removed: $BIN_FILE"
else
    echo "No launcher script found."
fi

if [ -f "$DESKTOP_FILE" ]; then
    rm "$DESKTOP_FILE"
    echo "Desktop entry removed: $DESKTOP_FILE"
else
    echo "No desktop entry found."
fi

echo ""
echo "Note: Configuration at ~/.config/rm-acs-launcher/ and keyring passwords"
echo "have been left intact. Remove them manually if desired."

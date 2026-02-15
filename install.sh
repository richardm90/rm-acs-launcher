#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
DESKTOP_FILE="$HOME/.local/share/applications/rm-acs-launcher.desktop"

echo "Installing RM ACS Launcher..."

# Create desktop entry with correct paths
sed -e "s|Exec=.*|Exec=python3 ${SCRIPT_DIR}/acs_launcher/main.py|" \
    -e "s|Icon=.*|Icon=${SCRIPT_DIR}/data/rm-acs-launcher.png|" \
    "${SCRIPT_DIR}/data/rm-acs-launcher.desktop" > "$DESKTOP_FILE"

echo "Desktop entry installed to: $DESKTOP_FILE"
echo ""
echo "You can now launch RM ACS Launcher from your application menu,"
echo "or run directly with:"
echo "  python3 ${SCRIPT_DIR}/acs_launcher/main.py"

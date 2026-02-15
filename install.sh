#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
APP_NAME="rm-acs-launcher"
INSTALL_DIR="$HOME/.local/share/$APP_NAME"
BIN_DIR="$HOME/.local/bin"
DESKTOP_FILE="$HOME/.local/share/applications/$APP_NAME.desktop"

echo "Installing RM ACS Launcher..."

# Create installation directories
mkdir -p "$INSTALL_DIR"
mkdir -p "$BIN_DIR"
mkdir -p "$(dirname "$DESKTOP_FILE")"

# Copy application files
cp -r "${SCRIPT_DIR}/acs_launcher" "$INSTALL_DIR/"
cp -r "${SCRIPT_DIR}/data" "$INSTALL_DIR/"

# Create launcher script
cat > "$BIN_DIR/$APP_NAME" << EOF
#!/bin/bash
exec python3 "$INSTALL_DIR/acs_launcher/main.py" "\$@"
EOF
chmod +x "$BIN_DIR/$APP_NAME"

# Create desktop entry with correct paths
sed -e "s|Exec=.*|Exec=$BIN_DIR/$APP_NAME|" \
    -e "s|Icon=.*|Icon=$INSTALL_DIR/data/rm-acs-launcher.png|" \
    "${SCRIPT_DIR}/data/rm-acs-launcher.desktop" > "$DESKTOP_FILE"

echo "Installation complete:"
echo "  App files:     $INSTALL_DIR/"
echo "  Launcher:      $BIN_DIR/$APP_NAME"
echo "  Desktop entry:  $DESKTOP_FILE"
echo ""
echo "You can now launch RM ACS Launcher from your application menu,"
echo "or from the terminal with: $APP_NAME"
echo ""
echo "The source repository is no longer needed and can be removed."

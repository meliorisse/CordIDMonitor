#!/bin/bash
set -e

REPO="meliorisse/CordIDMonitor"
APP_NAME="Cord ID Monitor"
EXEC_NAME="cord-id-monitor"
ICON_NAME="cord-id-monitor"

# Directories
BIN_DIR="$HOME/.local/bin"
DESKTOP_DIR="$HOME/.local/share/applications"
ICON_DIR="$HOME/.local/share/icons/hicolor/512x512/apps"

mkdir -p "$BIN_DIR"
mkdir -p "$DESKTOP_DIR"
mkdir -p "$ICON_DIR"

echo "Installing $APP_NAME..."

# 1. Fetch Latest Release URL
echo "Fetching latest release..."
LATEST_TAG=$(curl -s "https://api.github.com/repos/$REPO/releases/latest" | grep '"tag_name":' | sed -E 's/.*"([^"]+)".*/\1/')

if [ -z "$LATEST_TAG" ]; then
    echo "Error: Could not find latest release."
    exit 1
fi

DOWNLOAD_URL="https://github.com/$REPO/releases/download/$LATEST_TAG/Cord_ID_Monitor-x86_64.AppImage"
TARGET_FILE="$BIN_DIR/$EXEC_NAME.AppImage"

# 2. Download AppImage
echo "Downloading $LATEST_TAG..."
curl -L -o "$TARGET_FILE" "$DOWNLOAD_URL"
chmod +x "$TARGET_FILE"

# 3. Download Icon (from main branch)
echo "Downloading icon..."
ICON_URL="https://raw.githubusercontent.com/$REPO/main/assets/cord-id-monitor.png"
curl -L -o "$ICON_DIR/$ICON_NAME.png" "$ICON_URL"

# 4. Create Desktop File
echo "Creating desktop entry..."
cat > "$DESKTOP_DIR/$EXEC_NAME.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=$APP_NAME
Comment=Monitor USB device connections and speeds
Exec=$TARGET_FILE
Icon=$ICON_NAME
Categories=Utility;System;Monitor;
Terminal=false
EOF

# 5. Update Cache
if command -v update-desktop-database &> /dev/null; then
    update-desktop-database "$DESKTOP_DIR"
fi

echo "------------------------------------------------"
echo "$APP_NAME installed successfully!"
echo "Run it from your application menu or command line: $TARGET_FILE"

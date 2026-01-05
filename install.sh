#!/bin/bash

# v2deck Installation Script for Steam Deck
# Run this in Desktop Mode

set -e

PLUGIN_NAME="v2deck"
PLUGIN_DIR="$HOME/homebrew/plugins/$PLUGIN_NAME"
XRAY_VERSION="1.8.24"
TUN2SOCKS_VERSION="2.5.2"

echo "========================================"
echo "   v2deck Installer for Steam Deck   "
echo "========================================"

if [ ! -d "$HOME/homebrew" ]; then
    echo "Error: Decky Loader not found!"
    echo "Please install Decky Loader first: https://decky.xyz"
    exit 1
fi

echo ""
echo "[1/5] Removing old installation (if exists)..."
rm -rf "$PLUGIN_DIR"

echo "[2/5] Creating plugin directory..."
mkdir -p "$PLUGIN_DIR"
mkdir -p "$PLUGIN_DIR/bin"
mkdir -p "$PLUGIN_DIR/dist"

echo "[3/5] Copying plugin files..."
cp -r ./* "$PLUGIN_DIR/" 2>/dev/null || true
rm -f "$PLUGIN_DIR/install.sh"
rm -f "$PLUGIN_DIR/build.sh"

echo "[4/5] Downloading xray-core..."
XRAY_URL="https://github.com/XTLS/Xray-core/releases/download/v${XRAY_VERSION}/Xray-linux-64.zip"
TEMP_DIR=$(mktemp -d)

curl -L -o "$TEMP_DIR/xray.zip" "$XRAY_URL"
unzip -o "$TEMP_DIR/xray.zip" -d "$TEMP_DIR/xray"
cp "$TEMP_DIR/xray/xray" "$PLUGIN_DIR/bin/xray"
chmod +x "$PLUGIN_DIR/bin/xray"

if [ -f "$TEMP_DIR/xray/geoip.dat" ]; then
    cp "$TEMP_DIR/xray/geoip.dat" "$PLUGIN_DIR/bin/"
fi
if [ -f "$TEMP_DIR/xray/geosite.dat" ]; then
    cp "$TEMP_DIR/xray/geosite.dat" "$PLUGIN_DIR/bin/"
fi

echo "[5/5] Downloading tun2socks..."
TUN2SOCKS_URL="https://github.com/xjasonlyu/tun2socks/releases/download/v${TUN2SOCKS_VERSION}/tun2socks-linux-amd64.zip"

curl -L -o "$TEMP_DIR/tun2socks.zip" "$TUN2SOCKS_URL"
unzip -o "$TEMP_DIR/tun2socks.zip" -d "$TEMP_DIR/tun2socks"
cp "$TEMP_DIR/tun2socks/tun2socks-linux-amd64" "$PLUGIN_DIR/bin/tun2socks"
chmod +x "$PLUGIN_DIR/bin/tun2socks"

rm -rf "$TEMP_DIR"

echo ""
echo "========================================"
echo "   Installation Complete!              "
echo "========================================"
echo ""
echo "Restart Steam or run 'sudo systemctl restart plugin_loader' to load the plugin."
echo ""
echo "If you have issues, make sure your filesystem is unlocked:"
echo "  sudo steamos-readonly disable"
echo ""

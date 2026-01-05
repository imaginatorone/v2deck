#!/bin/bash

# v2deck Build Script
# Builds the plugin for distribution

set -e

PLUGIN_NAME="v2deck"

echo "========================================"
echo "   Building v2deck Plugin           "
echo "========================================"

if ! command -v pnpm &> /dev/null; then
    echo "Installing pnpm..."
    npm install -g pnpm
fi

echo ""
echo "[1/4] Installing dependencies..."
pnpm install

echo ""
echo "[2/4] Building frontend..."
pnpm run build

echo ""
echo "[3/4] Creating distribution package..."

rm -rf "./release"
mkdir -p "./release/$PLUGIN_NAME"

cp -r ./dist "./release/$PLUGIN_NAME/"
cp ./main.py "./release/$PLUGIN_NAME/"
cp ./plugin.json "./release/$PLUGIN_NAME/"
cp ./package.json "./release/$PLUGIN_NAME/"

mkdir -p "./release/$PLUGIN_NAME/bin"
echo "# Binaries will be downloaded during installation" > "./release/$PLUGIN_NAME/bin/.gitkeep"

if [ -d "./defaults" ]; then
    cp -r ./defaults "./release/$PLUGIN_NAME/"
fi

echo ""
echo "[4/4] Creating ZIP archive..."
cd "./release"
zip -r "../$PLUGIN_NAME.zip" "./$PLUGIN_NAME"
cd ..

echo ""
echo "========================================"
echo "   Build Complete!                     "
echo "========================================"
echo ""
echo "Output files:"
echo "  - release/$PLUGIN_NAME/ (plugin directory)"
echo "  - $PLUGIN_NAME.zip (distribution archive)"
echo ""
echo "To install on Steam Deck:"
echo "  1. Copy $PLUGIN_NAME.zip to Steam Deck"
echo "  2. Extract to ~/homebrew/plugins/"
echo "  3. Run: ./install.sh to download binaries"
echo "  4. Restart Steam"
echo ""

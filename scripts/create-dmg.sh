#!/usr/bin/env bash
set -euo pipefail

# Build a macOS app bundle from the Swift package target and wrap it in a DMG.
# Requirements: Xcode command line tools, iconutil, hdiutil.

ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
APP_NAME="n00HQ"
PRODUCT_BIN="n00hq"
VERSION="${VERSION:-0.1.0}"
BUILD_CONFIG="${BUILD_CONFIG:-release}"

N00_DIR="$ROOT_DIR/n00HQ"
OUT_DIR="$ROOT_DIR/dist"
APP_DIR="$OUT_DIR/${APP_NAME}.app"
MACOS_DIR="$APP_DIR/Contents/MacOS"
RESOURCES_DIR="$APP_DIR/Contents/Resources"
ARTIFACTS_DIR="$ROOT_DIR/.dev/automation/artifacts"

echo "[create-dmg] Building Swift product ($BUILD_CONFIG)…"
pushd "$N00_DIR" >/dev/null
swift build -c "$BUILD_CONFIG" --product "$PRODUCT_BIN"
popd >/dev/null

PRODUCT_PATH="$N00_DIR/.build/$BUILD_CONFIG/$PRODUCT_BIN"
BUNDLE_PATH="$N00_DIR/.build/$BUILD_CONFIG/n00HQ_n00HQApp.bundle"
ICONSET="$N00_DIR/Sources/n00HQApp/AppIcon.xcassets/AppIcon.appiconset"

rm -rf "$APP_DIR"
mkdir -p "$MACOS_DIR" "$RESOURCES_DIR" "$OUT_DIR"

echo "[create-dmg] Copying binary and resources…"
cp "$PRODUCT_PATH" "$MACOS_DIR/$PRODUCT_BIN"
if [[ -d $BUNDLE_PATH ]]; then
	cp -R "$BUNDLE_PATH" "$RESOURCES_DIR/"
fi

echo "[create-dmg] Building icns from appiconset…"
ICON_TMP="$OUT_DIR/AppIcon.icns"
ICONSET_TMP="$OUT_DIR/AppIcon.iconset"
rm -rf "$ICONSET_TMP"
mkdir -p "$ICONSET_TMP"
cp "$ICONSET"/icon_*.png "$ICONSET_TMP/"
iconutil -c icns "$ICONSET_TMP" -o "$ICON_TMP"
cp "$ICON_TMP" "$RESOURCES_DIR/AppIcon.icns"

INFO_PLIST="$APP_DIR/Contents/Info.plist"
cat >"$INFO_PLIST" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>CFBundleName</key><string>${APP_NAME}</string>
  <key>CFBundleDisplayName</key><string>${APP_NAME}</string>
  <key>CFBundleIdentifier</key><string>com.n00tropic.n00hq</string>
  <key>CFBundleShortVersionString</key><string>${VERSION}</string>
  <key>CFBundleVersion</key><string>${VERSION}</string>
  <key>CFBundleExecutable</key><string>${PRODUCT_BIN}</string>
  <key>CFBundleIconFile</key><string>AppIcon</string>
  <key>LSMinimumSystemVersion</key><string>13.0</string>
  <key>NSHighResolutionCapable</key><true/>
  <key>LSApplicationCategoryType</key><string>public.app-category.productivity</string>
</dict>
</plist>
EOF

DMG_PATH="$OUT_DIR/${APP_NAME}-${VERSION}.dmg"
rm -f "$DMG_PATH"
echo "[create-dmg] Creating DMG at $DMG_PATH"
hdiutil create -volname "$APP_NAME" -srcfolder "$APP_DIR" -ov -format UDZO "$DMG_PATH" >/dev/null
echo "[create-dmg] Done."

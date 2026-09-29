#!/bin/zsh
set -euo pipefail
cd "${0:A:h:h}"
configuration="${1:-release}"
swift build -c "$configuration"
binary_dir="$(swift build -c "$configuration" --show-bin-path)"
app_path="$PWD/dist/HunterDex.app"
if pgrep -x HunterDex >/dev/null; then
  echo "请先退出猎人手册，再运行打包脚本，以免替换正在读取的数据库。" >&2
  exit 1
fi
mkdir -p "$app_path/Contents/MacOS" "$app_path/Contents/Resources"
cp "$binary_dir/HunterDex" "$app_path/Contents/MacOS/HunterDex"
ditto "$binary_dir/HunterDex_HunterDex.bundle" "$app_path/Contents/Resources/HunterDex_HunterDex.bundle"
cat > "$app_path/Contents/Info.plist" <<'PLIST'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
<key>CFBundleExecutable</key><string>HunterDex</string>
<key>CFBundleIdentifier</key><string>local.hunternotes.HunterDex</string>
<key>CFBundleName</key><string>HunterDex</string>
<key>CFBundleDisplayName</key><string>猎人手册</string>
<key>CFBundlePackageType</key><string>APPL</string>
<key>CFBundleShortVersionString</key><string>0.3.0</string>
<key>CFBundleVersion</key><string>3</string>
<key>LSMinimumSystemVersion</key><string>14.0</string>
<key>NSHighResolutionCapable</key><true/>
<key>NSHumanReadableCopyright</key><string>Independent community companion. See bundled data attribution.</string>
</dict></plist>
PLIST
if [[ -f "$PWD/Assets/AppIcon.icns" ]]; then
  cp "$PWD/Assets/AppIcon.icns" "$app_path/Contents/Resources/AppIcon.icns"
  /usr/libexec/PlistBuddy -c 'Add :CFBundleIconFile string AppIcon' "$app_path/Contents/Info.plist"
fi
cp "$PWD/LICENSE" "$app_path/Contents/Resources/HunterDex-LICENSE.txt"
cp "$PWD/THIRD_PARTY_NOTICES.md" "$app_path/Contents/Resources/THIRD_PARTY_NOTICES.md"
codesign --force --deep --sign - "$app_path"
codesign --verify --deep --strict "$app_path"
echo "Built: $app_path"

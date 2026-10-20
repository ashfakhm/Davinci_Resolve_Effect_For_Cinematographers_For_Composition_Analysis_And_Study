#!/bin/sh
# Removes Cinematic_Composition_Toolkit.drfx from DaVinci Resolve.
# Run from repository root: sh tools/uninstall_mac.sh
set -e

DEST="$HOME/Library/Application Support/Blackmagic Design/DaVinci Resolve/Fusion/Templates"
TARGET="$DEST/Cinematic_Composition_Toolkit.drfx"
OLD_FRAME_CRAFT="$DEST/FrameCraft_ALL.drfx"

if [ -f "$TARGET" ]; then
    rm -f "$TARGET"
    echo "Removed $TARGET"
fi

if [ -f "$OLD_FRAME_CRAFT" ]; then
    rm -f "$OLD_FRAME_CRAFT"
    echo "Removed $OLD_FRAME_CRAFT"
fi

# Clean any residual unpacked FrameCraft folders in Edit/Effects if any exist
if [ -d "$DEST/Edit/Effects" ]; then
    find "$DEST/Edit/Effects" -maxdepth 1 -type d -name "FrameCraft*" -exec rm -rf {} + 2>/dev/null || true
    find "$DEST/Edit/Effects" -maxdepth 1 -type d -name "Cinematic Guides" -exec rm -rf {} + 2>/dev/null || true
fi

echo "Uninstalled Cinematic Composition Toolkit. Quit (Cmd+Q) and reopen DaVinci Resolve."

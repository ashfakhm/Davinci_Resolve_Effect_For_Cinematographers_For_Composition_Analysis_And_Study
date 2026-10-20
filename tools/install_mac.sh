#!/bin/sh
# Installs Cinematic_Composition_Toolkit.drfx into DaVinci Resolve.
# Run from repository root: sh tools/install_mac.sh
set -e

SRC="${1:-dist/Cinematic_Composition_Toolkit.drfx}"
DEST="$HOME/Library/Application Support/Blackmagic Design/DaVinci Resolve/Fusion/Templates"

if [ ! -f "$SRC" ]; then
    echo "Bundle not found at $SRC. Building it now..."
    python3 tools/build_cinematic_toolkit.py
fi

mkdir -p "$DEST"
cp "$SRC" "$DEST/"

echo "--------------------------------------------------------"
echo " Successfully installed: $(basename "$SRC")"
echo " Destination: $DEST"
echo "--------------------------------------------------------"
echo "Next step: If DaVinci Resolve is open, Quit (Cmd+Q) and reopen it."
echo "In DaVinci Resolve:"
echo "1. Go to Edit Page -> Effects Library -> Effects -> Cinematic Guides."
echo "2. Drag 'Cinematic Composition Toolkit' onto any clip or Adjustment Clip."
echo "3. Use the Inspector to switch guides and frame presets!"

#!/usr/bin/env bash
# Cross-build a Windows exe from Linux using PyInstaller in a Wine-based Docker container.
# Requires Docker installed and enough disk space.
# Usage: ./build_windows.sh
set -euo pipefail

echo "Building Windows executable using Docker..."
echo "This may take several minutes on first run..."
echo ""

# Use the batonogov image 
IMAGE="batonogov/pyinstaller-windows:latest"

# Create dist directory if it doesn't exist
mkdir -p dist

echo "Running PyInstaller in Docker..."
# Run PyInstaller using the image's entrypoint
docker run \
  -v "$(pwd):/src" \
  $IMAGE

if [ -d "dist/getsupernovae" ]; then
    echo ""
    echo "✓ Build successful!"
    ls -lh dist/getsupernovae/
    echo ""
    echo "The Windows executable is ready: dist/getsupernovae/getsupernovae.exe"
elif [ -f "dist/getsupernovae.exe" ]; then
    echo ""
    echo "✓ Build successful!"
    ls -lh dist/getsupernovae.exe
    echo ""
    echo "The Windows executable is ready: dist/getsupernovae.exe"
else
    echo ""
    echo "✗ Build failed - executable not found in dist/"
    echo "Check the output above for errors"
    exit 1
fi
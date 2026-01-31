#!/usr/bin/env bash
set -euo pipefail

# Extract translatable strings into a POT template and provide helpers
# Usage: ./scripts/extract_messages.sh

ROOT_DIR=$(cd "$(dirname "$0")/.." && pwd)
cd "$ROOT_DIR"

echo "Extracting messages to locales/getsupernovae.pot..."
# find python files and extract strings marked with _() and ngettext()
find . -name "*.py" | xargs xgettext --keyword=_ --keyword=ngettext:1,2 --language=Python --output=locales/getsupernovae.pot || true

echo "If you want to initialize a new language, run:"
echo "  msginit --no-translator --locale=es --input=locales/getsupernovae.pot --output-file=locales/es/LC_MESSAGES/getsupernovae.po"
echo "Then edit the .po and compile with msgfmt or use 'msgfmt -o locales/<lang>/LC_MESSAGES/getsupernovae.mo locales/<lang>/LC_MESSAGES/getsupernovae.po'"

echo "Done."

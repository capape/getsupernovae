Locale extraction and compilation
=================================

This project uses gettext for translations. Files are located under `locales/`.

Quick workflow

- Extract messages (produces `locales/getsupernovae.pot`):

```bash
./scripts/extract_messages.sh
```

- Initialize a new language (example Spanish):

```bash
msginit --no-translator --locale=es --input=locales/getsupernovae.pot --output-file=locales/es/LC_MESSAGES/getsupernovae.po
```

- Edit `locales/<lang>/LC_MESSAGES/getsupernovae.po` with translations.

- Compile `.po` to `.mo` for runtime use:

```bash
msgfmt locales/es/LC_MESSAGES/getsupernovae.po -o locales/es/LC_MESSAGES/getsupernovae.mo
```

Runtime

The `i18n.py` module loads compiled `.mo` files from `locales/<lang>/LC_MESSAGES/getsupernovae.mo` when you call `set_language('<lang>')`.
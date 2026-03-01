"""
Simple i18n wrapper using gettext.

API mirrors the old top-level `i18n.py`: `_`, `ngettext`, `set_language`, `get_language`.
"""

import gettext
import os
from typing import Optional

# point LOCALEDIR to the repository-level `locales/` directory
LOCALEDIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "locales"))
DOMAIN = "getsupernovae"

# current translation object (defaults to NullTranslations => identity)
_current_trans = gettext.NullTranslations()
_CURRENT_LANGUAGE: Optional[str] = None


def _(message: str) -> str:
    """Translate a message using the current language."""
    return _current_trans.gettext(message)


def ngettext(singular: str, plural: str, n: int) -> str:
    """Translate a message with plural forms."""
    return _current_trans.ngettext(singular, plural, n)


def set_language(lang: Optional[str]) -> None:
    """Set the application language."""
    global _current_trans, _CURRENT_LANGUAGE
    if not lang:
        _current_trans = gettext.NullTranslations()
        _CURRENT_LANGUAGE = None
    else:
        try:
            _current_trans = gettext.translation(DOMAIN, LOCALEDIR, languages=[lang], fallback=True)
            _CURRENT_LANGUAGE = lang
        except (OSError, IOError, ValueError):
            _current_trans = gettext.NullTranslations()
            _CURRENT_LANGUAGE = None


def get_language() -> Optional[str]:
    """Get the current language code."""
    return _CURRENT_LANGUAGE


# Do NOT auto-initialize from LANG - let the app explicitly set language
set_language(None)

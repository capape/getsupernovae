"""
Simple i18n wrapper using gettext.

Usage:
    from i18n import _, set_language, get_language, ngettext

    set_language('es')   # switch to Spanish if locales/es/LC_MESSAGES/getsupernovae.mo exists
    print(_("Hello, World"))
"""
from typing import Optional
import gettext
import os

LOCALEDIR = os.path.join(os.path.dirname(__file__), "locales")
DOMAIN = "getsupernovae"

# current translation object (defaults to NullTranslations => identity)
_current_trans = gettext.NullTranslations()
_current_language: Optional[str] = None


def _(message: str) -> str:
    """
    Translate message using the current translation.
    This function always uses the current translation object,
    ensuring that language changes take effect immediately.
    """
    return _current_trans.gettext(message)


def ngettext(singular: str, plural: str, n: int) -> str:
    """
    Translate message with plural forms using the current translation.
    """
    return _current_trans.ngettext(singular, plural, n)


def set_language(lang: Optional[str]) -> None:
    """
    Load and activate translations for `lang` (e.g. 'en', 'es', 'ca').
    Passing None or an empty string resets to identity (no translation).
    """
    global _current_trans, _current_language
    if not lang:
        _current_trans = gettext.NullTranslations()
        _current_language = None
    else:
        try:
            _current_trans = gettext.translation(DOMAIN, LOCALEDIR, languages=[lang], fallback=True)
            _current_language = lang
        except Exception:
            _current_trans = gettext.NullTranslations()
            _current_language = None


def get_language() -> Optional[str]:
    """Return the currently active language code or None if untranslated."""
    return _current_language


# Do NOT auto-initialize from LANG - let the app explicitly set language
# This prevents Spanish from being loaded before the app can set English
set_language(None)

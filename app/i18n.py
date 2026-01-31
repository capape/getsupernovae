"""
Simple i18n wrapper using gettext.

API mirrors the old top-level `i18n.py`: `_`, `ngettext`, `set_language`, `get_language`.
"""
from typing import Optional
import gettext
import os

# point LOCALEDIR to the repository-level `locales/` directory
LOCALEDIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "locales"))
DOMAIN = "getsupernovae"

# current translation object (defaults to NullTranslations => identity)
_current_trans = gettext.NullTranslations()
_current_language: Optional[str] = None


def _(message: str) -> str:
    return _current_trans.gettext(message)


def ngettext(singular: str, plural: str, n: int) -> str:
    return _current_trans.ngettext(singular, plural, n)


def set_language(lang: Optional[str]) -> None:
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
    return _current_language


# Do NOT auto-initialize from LANG - let the app explicitly set language
set_language(None)

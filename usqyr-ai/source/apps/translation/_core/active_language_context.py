from contextvars import ContextVar

from .conf import get_supported_language_codes, DEFAULT_LANGUAGE_STARTUP

_lang_ctx: ContextVar[str | None] = ContextVar("lang_code", default=None)
_valid_codes = set(get_supported_language_codes())


def set_language(lang_code: str) -> None:
    if lang_code not in _valid_codes:
        raise ValueError(
            f"Invalid language code '{lang_code}'. "
            f"Must be one of: {', '.join(sorted(_valid_codes))}"
        )
    _lang_ctx.set(lang_code)


def get_language() -> str:
    lang = _lang_ctx.get()
    return lang if lang is not None else DEFAULT_LANGUAGE_STARTUP
